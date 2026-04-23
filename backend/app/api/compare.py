"""GET /api/compare/head-to-head — predict a synthetic fixture between any
two teams. Returns each ensemble leg separately + the blended result, so the
frontend can render a side-by-side "how each model sees this matchup" view.

No DB write, no commitment hash — this is exploratory, not a forecast of
record.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app import queries
from app.core.config import get_settings
from app.models.elo import compute_ratings, elo_to_3way
from app.models.features import compute_team_strengths, match_lambdas
from app.predict.service import ELO_WEIGHT, NEUTRAL, XGB_WEIGHT
from app.models.poisson import predict_match
from app.models.xgb_model import (
    build_feature_row as xgb_build_feature_row,
    load_model as xgb_load_model,
    predict_probs as xgb_predict_probs,
)
router = APIRouter(prefix="/api/compare", tags=["compare"])


class Triple(BaseModel):
    p_home_win: float
    p_draw: float
    p_away_win: float


class H2HPrediction(BaseModel):
    home_name: str
    home_slug: str
    away_name: str
    away_slug: str
    league_code: str | None

    poisson: Triple
    elo: Triple | None
    xgb: Triple | None
    ensemble: Triple

    expected_home_goals: float
    expected_away_goals: float
    top_scoreline: tuple[int, int]

    data_as_of: datetime


class H2HMeeting(BaseModel):
    match_id: int
    kickoff_time: datetime
    season: str
    league_code: str | None
    home_slug: str
    home_short: str
    away_slug: str
    away_short: str
    home_goals: int
    away_goals: int
    outcome: str                          # H | D | A
    predicted_outcome: str | None         # H | D | A
    hit: bool | None


class H2HHistory(BaseModel):
    home_slug: str
    away_slug: str
    meetings: list[H2HMeeting]
    total_meetings: int
    home_wins: int
    draws: int
    away_wins: int
    model_scored: int                     # meetings where we had a prediction
    model_correct: int
    model_accuracy: float | None


@router.get("/history", response_model=H2HHistory)
async def head_to_head_history(
    request: Request,
    home: str = Query(..., description="home team slug"),
    away: str = Query(..., description="away team slug"),
    limit: int = Query(10, ge=1, le=50),
) -> H2HHistory:
    """Last N meetings between two teams (either order), with model pick +
    hit/miss where a prediction was logged at the time.
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH latest AS (
                SELECT DISTINCT ON (p.match_id)
                  p.match_id, p.p_home_win, p.p_draw, p.p_away_win
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            )
            SELECT m.id, m.kickoff_time, m.season, m.league_code,
                   ht.slug AS home_slug, ht.short_name AS home_short,
                   at.slug AS away_slug, at.short_name AS away_short,
                   m.home_goals, m.away_goals,
                   l.p_home_win, l.p_draw, l.p_away_win
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            LEFT JOIN latest l ON l.match_id = m.id
            WHERE m.status = 'final' AND m.home_goals IS NOT NULL
              AND (
                (ht.slug = $1 AND at.slug = $2)
                OR (ht.slug = $2 AND at.slug = $1)
              )
            ORDER BY m.kickoff_time DESC
            LIMIT $3
            """,
            home, away, limit,
        )

    meetings: list[H2HMeeting] = []
    hw = dw = aw = 0  # from the queried home-team's perspective
    scored = correct = 0
    for r in rows:
        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        actual = "H" if hg > ag else "A" if hg < ag else "D"
        predicted: str | None = None
        if r["p_home_win"] is not None:
            probs = {"H": r["p_home_win"], "D": r["p_draw"], "A": r["p_away_win"]}
            predicted = max(probs, key=probs.get)
            scored += 1
            if predicted == actual:
                correct += 1
        # Normalize H/A so the count is always from the *requested* `home`
        # team's perspective (not DB's home side).
        if r["home_slug"] == home:
            if actual == "H":
                hw += 1
            elif actual == "A":
                aw += 1
            else:
                dw += 1
        else:
            if actual == "H":
                aw += 1
            elif actual == "A":
                hw += 1
            else:
                dw += 1
        hit = (predicted == actual) if predicted is not None else None
        meetings.append(H2HMeeting(
            match_id=r["id"],
            kickoff_time=r["kickoff_time"],
            season=r["season"],
            league_code=r["league_code"],
            home_slug=r["home_slug"], home_short=r["home_short"],
            away_slug=r["away_slug"], away_short=r["away_short"],
            home_goals=hg, away_goals=ag,
            outcome=actual,
            predicted_outcome=predicted,
            hit=hit,
        ))

    accuracy = (correct / scored) if scored > 0 else None
    return H2HHistory(
        home_slug=home, away_slug=away,
        meetings=meetings,
        total_meetings=len(meetings),
        home_wins=hw, draws=dw, away_wins=aw,
        model_scored=scored, model_correct=correct,
        model_accuracy=accuracy,
    )


async def _team_by_slug(pool, slug: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT t.id, t.slug, t.name, t.short_name,
                   (SELECT league_code FROM matches m
                    WHERE m.home_team_id = t.id OR m.away_team_id = t.id
                    ORDER BY m.kickoff_time DESC LIMIT 1) AS league_code
            FROM teams t
            WHERE t.slug = $1
            """,
            slug,
        )
    return dict(row) if row else None


@router.get("/head-to-head", response_model=H2HPrediction)
async def head_to_head(
    request: Request,
    home: str = Query(..., description="home team slug"),
    away: str = Query(..., description="away team slug"),
) -> H2HPrediction:
    """Compute Poisson / Elo / XGBoost / blended probs for any fixture pair.

    No commitment — these are exploratory numbers for the compare page.
    """
    pool = request.app.state.pool
    settings = get_settings()

    home_team = await _team_by_slug(pool, home)
    away_team = await _team_by_slug(pool, away)
    if home_team is None or away_team is None:
        raise HTTPException(404, "team not found")

    league_code = home_team["league_code"] or away_team["league_code"]
    df = await queries.fetch_finished_matches_df(pool, league_code=league_code)
    if df.empty:
        raise HTTPException(404, f"no finished matches with xG for league {league_code!r}")

    as_of = datetime.now(timezone.utc)

    strengths = compute_team_strengths(
        df,
        as_of=pd.Timestamp(as_of),
        last_n=settings.default_last_n,
        opponent_adjust=True,
    )
    home_s = strengths.get(home_team["name"], NEUTRAL)
    away_s = strengths.get(away_team["name"], NEUTRAL)

    league_avg = float(pd.concat([df["home_goals"], df["away_goals"]]).mean())
    lam_h, lam_a = match_lambdas(home_s, away_s, league_avg_goals=league_avg)

    # Poisson (no Elo blend)
    poisson_only = predict_match(
        lam_h, lam_a,
        rho=settings.default_rho,
        temperature=settings.default_temperature,
    )

    # Elo alone
    ratings = compute_ratings(df)
    elo_home = ratings.get(home_team["name"])
    elo_away = ratings.get(away_team["name"])
    elo_triple: Triple | None = None
    elo_triple_raw: tuple[float, float, float] | None = None
    if elo_home is not None and elo_away is not None:
        t = elo_to_3way(elo_home, elo_away)
        elo_triple_raw = (t.p_home_win, t.p_draw, t.p_away_win)
        elo_triple = Triple(p_home_win=t.p_home_win, p_draw=t.p_draw, p_away_win=t.p_away_win)

    # XGBoost alone
    xgb_model = xgb_load_model()
    xgb_triple: Triple | None = None
    xgb_triple_raw: tuple[float, float, float] | None = None
    if xgb_model is not None:
        feats = xgb_build_feature_row(
            df, home_team["name"], away_team["name"],
            pd.Timestamp(as_of), league_avg,
        )
        if feats is not None:
            x = xgb_predict_probs(xgb_model, feats)
            xgb_triple_raw = x
            xgb_triple = Triple(p_home_win=x[0], p_draw=x[1], p_away_win=x[2])

    # Blended (same two-step convex combo as predict_and_persist)
    blended = predict_match(
        lam_h, lam_a,
        rho=settings.default_rho,
        temperature=settings.default_temperature,
        elo_probs=elo_triple_raw,
        elo_weight=ELO_WEIGHT if elo_triple_raw is not None else 0.0,
    )
    if xgb_triple_raw is not None:
        w = XGB_WEIGHT
        blended_probs = (
            (1 - w) * blended.p_home_win + w * xgb_triple_raw[0],
            (1 - w) * blended.p_draw + w * xgb_triple_raw[1],
            (1 - w) * blended.p_away_win + w * xgb_triple_raw[2],
        )
        s = sum(blended_probs) or 1.0
        ensemble_triple = Triple(
            p_home_win=blended_probs[0] / s,
            p_draw=blended_probs[1] / s,
            p_away_win=blended_probs[2] / s,
        )
    else:
        ensemble_triple = Triple(
            p_home_win=blended.p_home_win,
            p_draw=blended.p_draw,
            p_away_win=blended.p_away_win,
        )

    if poisson_only.top_scorelines:
        top_h, top_a = int(poisson_only.top_scorelines[0][0]), int(poisson_only.top_scorelines[0][1])
    else:
        top_h, top_a = 1, 1
    return H2HPrediction(
        home_name=home_team["name"], home_slug=home_team["slug"],
        away_name=away_team["name"], away_slug=away_team["slug"],
        league_code=league_code,
        poisson=Triple(
            p_home_win=poisson_only.p_home_win,
            p_draw=poisson_only.p_draw,
            p_away_win=poisson_only.p_away_win,
        ),
        elo=elo_triple,
        xgb=xgb_triple,
        ensemble=ensemble_triple,
        expected_home_goals=poisson_only.expected_home_goals,
        expected_away_goals=poisson_only.expected_away_goals,
        top_scoreline=(top_h, top_a),
        data_as_of=as_of,
    )
