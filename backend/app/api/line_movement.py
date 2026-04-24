"""GET /api/matches/:id/line-movement — historical odds per source.

Returns one time-series per bookmaker source showing how home/draw/away
odds moved from ingest-time toward kickoff.

Also exposes sharp-vs-square divergence: compare Pinnacle (or AF:pinnacle
equivalent) against the consensus of retail books. A divergence > 5% on
any outcome surfaces as a flag.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel


router = APIRouter(prefix="/api/matches", tags=["matches"])


class OddsSnapshot(BaseModel):
    captured_at: datetime
    source: str
    odds_home: float
    odds_draw: float
    odds_away: float


class SharpDivergenceFlag(BaseModel):
    outcome: str            # HOME | DRAW | AWAY
    sharp_prob: float       # devigged Pinnacle implied prob
    square_prob: float      # devigged mean of retail books
    divergence_pp: float    # sharp - square, in percentage points (signed)


class LineMovementResponse(BaseModel):
    match_id: int
    total_snapshots: int
    series: list[OddsSnapshot]
    sharp_divergence: list[SharpDivergenceFlag]


@router.get("/{match_id}/line-movement", response_model=LineMovementResponse)
async def line_movement(
    match_id: int,
    request: Request,
    limit: int = Query(500, ge=10, le=2000),
) -> LineMovementResponse:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT captured_at, source, odds_home, odds_draw, odds_away
            FROM match_odds_history
            WHERE match_id = $1
            ORDER BY captured_at ASC
            LIMIT $2
            """,
            match_id, limit,
        )
    snapshots = [OddsSnapshot(**dict(r)) for r in rows]

    # Sharp vs square divergence — based on the *latest* snapshot per source.
    latest_by_source: dict[str, OddsSnapshot] = {}
    for s in snapshots:
        latest_by_source[s.source] = s  # last write wins since rows ascending
    divergence = _compute_sharp_divergence(latest_by_source)

    return LineMovementResponse(
        match_id=match_id,
        total_snapshots=len(snapshots),
        series=snapshots,
        sharp_divergence=divergence,
    )


def _devig(home: float, draw: float, away: float) -> tuple[float, float, float]:
    """Proportional devig — each outcome's implied prob divided by the sum."""
    ih, id_, ia = 1 / home, 1 / draw, 1 / away
    total = ih + id_ + ia
    return (ih / total, id_ / total, ia / total)


def _compute_sharp_divergence(
    latest: dict[str, OddsSnapshot], threshold_pp: float = 5.0,
) -> list[SharpDivergenceFlag]:
    """Compare Pinnacle (sharp) vs mean of retail books (square). Flag any
    outcome where they diverge by ≥ threshold_pp percentage points."""
    pin_key = None
    retail_keys: list[str] = []
    for key in latest.keys():
        if "pinnacle" in key.lower():
            pin_key = key
        elif key.startswith("odds-api:") or key.startswith("af:"):
            retail_keys.append(key)

    if pin_key is None or not retail_keys:
        return []

    pin = latest[pin_key]
    sharp = _devig(pin.odds_home, pin.odds_draw, pin.odds_away)

    # Unweighted mean of retail devigged probs.
    sq_h = sq_d = sq_a = 0.0
    n = 0
    for k in retail_keys:
        if k == pin_key:
            continue
        r = latest[k]
        h, d, a = _devig(r.odds_home, r.odds_draw, r.odds_away)
        sq_h += h; sq_d += d; sq_a += a; n += 1
    if n == 0:
        return []
    sq = (sq_h / n, sq_d / n, sq_a / n)

    flags: list[SharpDivergenceFlag] = []
    for idx, outcome in enumerate(("HOME", "DRAW", "AWAY")):
        gap_pp = (sharp[idx] - sq[idx]) * 100
        if abs(gap_pp) >= threshold_pp:
            flags.append(SharpDivergenceFlag(
                outcome=outcome,
                sharp_prob=sharp[idx],
                square_prob=sq[idx],
                divergence_pp=gap_pp,
            ))
    return flags
