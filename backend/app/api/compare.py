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
