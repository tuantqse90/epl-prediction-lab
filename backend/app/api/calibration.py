"""GET /api/stats/calibration — reliability diagram data.

Pulls (predicted argmax prob, hit_bool) over a window, bins by decile,
returns per-bin hit rate + Brier + log-loss.

The argmax-prob-vs-hit-rate framing means "when the model said 60%,
60% of those matches should have hit the predicted outcome." Deviations
from the diagonal = miscalibration.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.models.calibration import summarize


router = APIRouter(prefix="/api/stats", tags=["stats"])


class Bin(BaseModel):
    bin_low: float
    bin_high: float
    n: int
    mean_predicted: float
    actual_hit_rate: float
    gap: float


class CalibrationResponse(BaseModel):
    total: int
    brier: float
    log_loss: float
    reliability: float
    bins: list[Bin]


@router.get("/reliability", response_model=CalibrationResponse)
async def calibration(
    request: Request,
    league: str | None = Query(None, description="optional league_code filter"),
    season: str | None = Query(None, description="optional season filter"),
    n_bins: int = Query(10, ge=5, le=20),
) -> CalibrationResponse:
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
            SELECT m.home_goals, m.away_goals, m.league_code, m.season,
                   l.p_home_win, l.p_draw, l.p_away_win
            FROM matches m
            JOIN latest l ON l.match_id = m.id
            WHERE m.status = 'final' AND m.home_goals IS NOT NULL
              AND ($1::text IS NULL OR m.league_code = $1)
              AND ($2::text IS NULL OR m.season = $2)
            """,
            league, season,
        )
    preds: list[tuple[float, bool]] = []
    for r in rows:
        probs = {"H": r["p_home_win"], "D": r["p_draw"], "A": r["p_away_win"]}
        pick = max(probs, key=probs.get)
        conf = float(probs[pick])
        actual = "H" if r["home_goals"] > r["away_goals"] else "A" if r["home_goals"] < r["away_goals"] else "D"
        preds.append((conf, pick == actual))
    s = summarize(preds, n_bins=n_bins)
    return CalibrationResponse(
        total=s["total"],
        brier=s["brier"],
        log_loss=s["log_loss"],
        reliability=s["reliability"],
        bins=[Bin(**b) for b in s["bins"]],
    )
