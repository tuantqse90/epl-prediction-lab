"""Orchestration: DB rows → team strengths → Poisson prediction → persist.

Called on-demand by the API and in bulk by `scripts/predict_upcoming.py`.
"""

from __future__ import annotations

import asyncpg
import pandas as pd

from app import queries
from app.models.elo import compute_ratings, elo_to_3way
from app.models.features import TeamStrength, compute_team_strengths, match_lambdas
from app.models.poisson import MatchPrediction, predict_match
from app.models.xgb_model import (
    build_feature_row as xgb_build_feature_row,
    load_model as xgb_load_model,
    predict_probs as xgb_predict_probs,
)
from app.onchain.commitment import commitment_hash

NEUTRAL = TeamStrength(attack=1.0, defense=1.0)

# Ensemble weights — final 1X2 = (ELO + XGB) signals blend into Poisson.
# Weights are applied via two sequential convex combinations in
# predict_match: first Poisson+Elo, then the result blended with XGB.
ELO_WEIGHT = 0.20
# Optimal weights per walk-forward tune on 1,816 out-of-sample matches
# (2024-25 + 2025-26 across top-5 leagues). Original config elo=0.25/xgb=0.15
# → log-loss 0.9834, acc 52.4%. Current elo=0.20/xgb=0.60 → log-loss 0.9278,
# acc 56.2% (-5.6% log-loss, +3.8pp accuracy). See scripts/tune_ensemble.py.
XGB_WEIGHT = 0.60
_XGB_MODEL_CACHE = {"model": None, "loaded": False}


def _xgb_model():
    """Lazy-load once per process. Returns None if model file absent."""
    if not _XGB_MODEL_CACHE["loaded"]:
        _XGB_MODEL_CACHE["model"] = xgb_load_model()
        _XGB_MODEL_CACHE["loaded"] = True
    return _XGB_MODEL_CACHE["model"]

# How hard an injury-adjusted xG shortfall bites the team's λ. 0.6 means
# losing 20% of team-xG to current absentees knocks λ down by 12%. Chosen
# conservatively — xG share imperfectly measures a player's true scoring
# contribution (assists, chance creation, defensive presence).
INJURY_ALPHA = 0.6

# Weather multiplier thresholds (symmetric, applied to both teams' λ).
WIND_THRESHOLD_KMH = 30.0
WIND_MULTIPLIER = 0.92          # ~-8% λ in strong wind
RAIN_THRESHOLD_MM = 2.0
RAIN_MULTIPLIER = 0.95          # ~-5% λ in heavy rain

# Referee tendency cap: ±10% on total-goal environment. Sparse refs (< 30
# matches in rolling window) get multiplier 1.0 (no-op).
REFEREE_CAP = 0.10
REFEREE_MIN_MATCHES = 30


async def _referee_multiplier(
    conn: asyncpg.Connection, match_id: int, league_code: str | None, kickoff
) -> float:
    """Look up the assigned referee for this match, compute their delta
    against the league-wide goals average over the prior two full seasons,
    return the multiplicative λ adjustment. Returns 1.0 if no referee
    assigned or sparse sample."""
    if not league_code:
        return 1.0
    row = await conn.fetchrow(
        "SELECT referee FROM matches WHERE id = $1", match_id,
    )
    if row is None or not row["referee"]:
        return 1.0
    ref_name = row["referee"]

    # Rolling 2-season window looking BACKWARDS from this kickoff. Excludes
    # the current match (WHERE id <> $1) so future-leak stays zero.
    sample = await conn.fetch(
        """
        SELECT referee, home_goals, away_goals
        FROM matches
        WHERE league_code = $2
          AND status = 'final'
          AND home_goals IS NOT NULL
          AND referee IS NOT NULL
          AND kickoff_time < $3
          AND kickoff_time >= $3 - INTERVAL '730 days'
          AND id <> $1
        """,
        match_id, league_code, kickoff,
    )
    if not sample:
        return 1.0

    from app.models.referee import referee_tendencies, referee_multiplier
    tendencies = referee_tendencies(sample, min_matches=REFEREE_MIN_MATCHES)
    info = tendencies.get(ref_name)
    if info is None:
        return 1.0
    # League avg from the same rolling sample so backtest/live stay consistent.
    totals = [int(r["home_goals"]) + int(r["away_goals"]) for r in sample]
    league_avg = sum(totals) / len(totals) if totals else 2.8
    return referee_multiplier(info["goals_delta"], league_avg=league_avg, cap=REFEREE_CAP)


async def _weather_multiplier(conn: asyncpg.Connection, match_id: int) -> float:
    row = await conn.fetchrow(
        "SELECT wind_kmh, precip_mm FROM match_weather WHERE match_id = $1",
        match_id,
    )
    if row is None:
        return 1.0
    m = 1.0
    wind = row["wind_kmh"]
    precip = row["precip_mm"]
    if wind is not None and wind >= WIND_THRESHOLD_KMH:
        m *= WIND_MULTIPLIER
    if precip is not None and precip >= RAIN_THRESHOLD_MM:
        m *= RAIN_MULTIPLIER
    return m


async def _injury_impact(
    conn: asyncpg.Connection, team_id: int, season: str, match_id: int | None = None
) -> float:
    """Share of the team's season xG currently unavailable.

    Prefers lineup data (when available ~60min pre-KO) because it captures
    rested/suspended/tactically-dropped players that the injuries feed
    misses. Falls back to the injuries table otherwise. Capped at 0.5 so a
    single key absence never nukes λ.
    """
    # Lineup-based path: if we have a starting XI + bench row set for this
    # fixture, absent = every season-stats player not in that 23-ish squad.
    if match_id is not None:
        row = await conn.fetchrow(
            """
            WITH squad AS (
                SELECT DISTINCT player_name
                FROM match_lineups
                WHERE match_id = $3 AND team_slug = (
                    SELECT slug FROM teams WHERE id = $1
                )
            ),
            team_xg AS (
                SELECT COALESCE(SUM(xg), 0) AS total_xg
                FROM player_season_stats
                WHERE team_id = $1 AND season = $2
            ),
            absent AS (
                SELECT COALESCE(SUM(p.xg), 0) AS absent_xg
                FROM player_season_stats p
                WHERE p.team_id = $1
                  AND p.season = $2
                  AND (SELECT COUNT(*) FROM squad) > 0
                  AND p.player_name NOT IN (SELECT player_name FROM squad)
            )
            SELECT total_xg, absent_xg, (SELECT COUNT(*) FROM squad) AS squad_size
            FROM team_xg, absent
            """,
            team_id, season, match_id,
        )
        if row and int(row["squad_size"] or 0) >= 10 and row["total_xg"]:
            share = float(row["absent_xg"]) / float(row["total_xg"])
            return max(0.0, min(0.5, share))
        # squad too small or lineup missing → fall through to injuries feed.

    row = await conn.fetchrow(
        """
        WITH team_xg AS (
            SELECT COALESCE(SUM(xg), 0) AS total_xg
            FROM player_season_stats
            WHERE team_id = $1 AND season = $2
        ),
        injured AS (
            SELECT COALESCE(SUM(p.xg), 0) AS injured_xg
            FROM player_injuries pi
            JOIN teams t      ON t.id = $1 AND pi.team_slug = t.slug
            JOIN player_season_stats p
                 ON p.team_id = t.id
                AND p.season = $2
                AND p.player_name = pi.player_name
            WHERE pi.season = $2
              AND pi.last_seen_at >= NOW() - INTERVAL '3 days'
              AND pi.status_label <> 'Missing Fixture'
        )
        SELECT team_xg.total_xg, injured.injured_xg
        FROM team_xg, injured
        """,
        team_id, season,
    )
    if row is None or not row["total_xg"]:
        return 0.0
    share = float(row["injured_xg"]) / float(row["total_xg"])
    return max(0.0, min(0.5, share))


async def predict_and_persist(
    pool: asyncpg.Pool,
    match_id: int,
    *,
    rho: float,
    model_version: str,
    last_n: int = 12,
    temperature: float = 1.0,
) -> tuple[int, MatchPrediction]:
    """Predict a single match and write a `predictions` row. Returns (prediction_id, result)."""
    match = await queries.get_match(pool, match_id)
    if match is None:
        raise ValueError(f"match {match_id} not found")

    league_code = match["league_code"] if match["league_code"] else None
    df = await queries.fetch_finished_matches_df(pool, league_code=league_code)
    if df.empty:
        raise RuntimeError(
            f"no finished matches with xG for league {league_code!r} — run ingest first"
        )

    # opponent_adjust=True rescales each match's xG by opponent quality.
    strengths = compute_team_strengths(
        df, as_of=match["kickoff_time"], last_n=last_n, opponent_adjust=True,
    )
    home = strengths.get(match["home_name"], NEUTRAL)
    away = strengths.get(match["away_name"], NEUTRAL)

    league_avg = float(pd.concat([df["home_goals"], df["away_goals"]]).mean())
    lam_h, lam_a = match_lambdas(home, away, league_avg_goals=league_avg)

    # Injury + weather adjustments: upcoming fixtures only. Backtest keeps
    # historical λ untouched so accuracy comparisons stay fair.
    if match["status"] == "scheduled" and "backtest" not in model_version:
        async with pool.acquire() as conn:
            home_hit = await _injury_impact(conn, match["home_team_id"], match["season"], match_id)
            away_hit = await _injury_impact(conn, match["away_team_id"], match["season"], match_id)
            weather_m = await _weather_multiplier(conn, match_id)
            ref_m = await _referee_multiplier(conn, match_id, league_code, match["kickoff_time"])
        lam_h *= max(0.5, 1.0 - INJURY_ALPHA * home_hit) * weather_m * ref_m
        lam_a *= max(0.5, 1.0 - INJURY_ALPHA * away_hit) * weather_m * ref_m

    # Elo side of the ensemble: walk the same filtered finished-match df up
    # to this kickoff, derive current ratings, convert to 3-way probs.
    prior_finals = df[df["date"] < match["kickoff_time"]]
    ratings = compute_ratings(prior_finals)
    elo_home = ratings.get(match["home_name"])
    elo_away = ratings.get(match["away_name"])
    elo_triple: tuple[float, float, float] | None = None
    if elo_home is not None and elo_away is not None:
        triple = elo_to_3way(elo_home, elo_away)
        elo_triple = (triple.p_home_win, triple.p_draw, triple.p_away_win)

    # First pass: Poisson + Elo blend.
    result = predict_match(
        lam_h, lam_a, rho=rho, temperature=temperature,
        elo_probs=elo_triple,
        elo_weight=ELO_WEIGHT if elo_triple is not None else 0.0,
    )

    # Second pass: layer XGBoost on top. Only blend if the trained booster
    # file exists — a fresh deploy without training data silently falls
    # back to the Poisson+Elo ensemble.
    xgb_model = _xgb_model()
    xgb_triple = None
    if xgb_model is not None:
        feats = xgb_build_feature_row(
            prior_finals, match["home_name"], match["away_name"],
            match["kickoff_time"], league_avg,
        )
        if feats is not None:
            xgb_triple = xgb_predict_probs(xgb_model, feats)
    if xgb_triple is not None:
        w = XGB_WEIGHT
        blended = (
            (1 - w) * result.p_home_win + w * xgb_triple[0],
            (1 - w) * result.p_draw + w * xgb_triple[1],
            (1 - w) * result.p_away_win + w * xgb_triple[2],
        )
        z = sum(blended) or 1.0
        result = MatchPrediction(
            p_home_win=blended[0] / z,
            p_draw=blended[1] / z,
            p_away_win=blended[2] / z,
            expected_home_goals=result.expected_home_goals,
            expected_away_goals=result.expected_away_goals,
            top_scorelines=result.top_scorelines,
        )

    tagged_version = (
        f"{model_version}:rho={rho}:T={temperature}:elo={ELO_WEIGHT}"
        f"{':xgb=' + str(XGB_WEIGHT) if xgb_triple is not None else ''}"
    )
    digest = commitment_hash(
        prediction=result,
        match_id=match_id,
        kickoff_unix=int(match["kickoff_time"].timestamp()),
        model_version=tagged_version,
        rho=rho,
    )
    pred_id = await queries.insert_prediction(
        pool, match_id, result, tagged_version, commitment_hash=digest
    )

    # Fire-and-forget: warm the bootstrap CI cache in the background so the
    # first visitor to /match/:id never waits for the 1.8-s cold path.
    # predict_and_persist is typically called from a cron or predict_upcoming
    # loop, so by the time a real user hits the page the CI is already
    # cached. Failures here are harmless — the endpoint still computes on
    # demand if the cache miss.
    if match["status"] == "scheduled":
        try:
            import asyncio
            from app.api.matches import _compute_ci
            asyncio.create_task(_compute_ci(pool, match_id))
        except Exception:
            pass

    return pred_id, result


async def predict_all_upcoming(
    pool: asyncpg.Pool,
    *,
    rho: float,
    model_version: str,
    horizon_days: int = 14,
    last_n: int = 12,
    temperature: float = 1.0,
    league_code: str | None = None,
) -> list[int]:
    async with pool.acquire() as conn:
        if league_code:
            rows = await conn.fetch(
                """
                SELECT id FROM matches
                WHERE status = 'scheduled'
                  AND league_code = $2
                  AND kickoff_time BETWEEN NOW() AND NOW() + ($1 || ' days')::INTERVAL
                ORDER BY kickoff_time ASC
                """,
                str(horizon_days), league_code,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id FROM matches
                WHERE status = 'scheduled'
                  AND kickoff_time BETWEEN NOW() AND NOW() + ($1 || ' days')::INTERVAL
                ORDER BY kickoff_time ASC
                """,
                str(horizon_days),
            )
    created: list[int] = []
    for r in rows:
        pid, _ = await predict_and_persist(
            pool, r["id"],
            rho=rho, model_version=model_version,
            last_n=last_n, temperature=temperature,
        )
        created.append(pid)
    return created
