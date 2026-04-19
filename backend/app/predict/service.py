"""Orchestration: DB rows → team strengths → Poisson prediction → persist.

Called on-demand by the API and in bulk by `scripts/predict_upcoming.py`.
"""

from __future__ import annotations

import asyncpg
import pandas as pd

from app import queries
from app.models.features import TeamStrength, compute_team_strengths, match_lambdas
from app.models.poisson import MatchPrediction, predict_match
from app.onchain.commitment import commitment_hash

NEUTRAL = TeamStrength(attack=1.0, defense=1.0)

# How hard an injury-adjusted xG shortfall bites the team's λ. 0.6 means
# losing 20% of team-xG to current absentees knocks λ down by 12%. Chosen
# conservatively — xG share imperfectly measures a player's true scoring
# contribution (assists, chance creation, defensive presence).
INJURY_ALPHA = 0.6


async def _injury_impact(
    conn: asyncpg.Connection, team_id: int, season: str
) -> float:
    """Share of the team's season xG currently unavailable.

    Matches currently-listed non-'Missing Fixture' injuries against
    player_season_stats (slug + exact player name). Returns a value in
    [0, 0.5] — capped to prevent a single key injury from nuking λ.
    """
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

    strengths = compute_team_strengths(df, as_of=match["kickoff_time"], last_n=last_n)
    home = strengths.get(match["home_name"], NEUTRAL)
    away = strengths.get(match["away_name"], NEUTRAL)

    league_avg = float(pd.concat([df["home_goals"], df["away_goals"]]).mean())
    lam_h, lam_a = match_lambdas(home, away, league_avg_goals=league_avg)

    # Injury adjustment: applied to upcoming fixtures only. Backtest + already
    # played matches keep their historical prediction untouched. Skipped when
    # the backtest marker is present in the model_version tag.
    if match["status"] == "scheduled" and "backtest" not in model_version:
        async with pool.acquire() as conn:
            home_hit = await _injury_impact(conn, match["home_team_id"], match["season"])
            away_hit = await _injury_impact(conn, match["away_team_id"], match["season"])
        lam_h *= max(0.5, 1.0 - INJURY_ALPHA * home_hit)
        lam_a *= max(0.5, 1.0 - INJURY_ALPHA * away_hit)

    result = predict_match(lam_h, lam_a, rho=rho, temperature=temperature)
    tagged_version = f"{model_version}:rho={rho}:T={temperature}"
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
