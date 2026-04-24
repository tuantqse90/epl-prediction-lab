"""GET /api/stats/clv-by-market — CLV breakdown by market type.

Existing `closing_odds` table only stores 1X2 closing lines. This
endpoint returns that view now; when we ingest OU/AH/BTTS closing lines
later, each additional `market` row surfaces automatically without a
frontend change.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel


router = APIRouter(prefix="/api/stats", tags=["stats"])


class MarketCLV(BaseModel):
    market: str
    total_samples: int
    mean_clv_pct: float | None
    notes: str | None = None


class CLVByMarketResponse(BaseModel):
    markets: list[MarketCLV]


@router.get("/clv-by-market", response_model=CLVByMarketResponse)
async def clv_by_market(request: Request) -> CLVByMarketResponse:
    pool = request.app.state.pool
    out: list[MarketCLV] = []

    # 1X2 CLV — pick-and-closing evaluation.
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            WITH latest AS (
                SELECT DISTINCT ON (match_id) match_id, p_home_win, p_draw, p_away_win
                FROM predictions ORDER BY match_id, created_at DESC
            )
            SELECT COUNT(*) AS n,
                   AVG(clv_pct) AS mean_clv
            FROM (
                SELECT
                  CASE
                    WHEN l.p_home_win >= l.p_draw AND l.p_home_win >= l.p_away_win
                      THEN (l.p_home_win * co.odds_home - 1) * 100.0
                    WHEN l.p_away_win >= l.p_home_win AND l.p_away_win >= l.p_draw
                      THEN (l.p_away_win * co.odds_away - 1) * 100.0
                    ELSE (l.p_draw * co.odds_draw - 1) * 100.0
                  END AS clv_pct
                FROM closing_odds co
                JOIN latest l ON l.match_id = co.match_id
            ) x
            WHERE clv_pct IS NOT NULL
            """,
        )
    n_1x2 = int(row["n"] or 0)
    mean_1x2 = float(row["mean_clv"]) if row["mean_clv"] is not None else None

    out.append(MarketCLV(
        market="1X2",
        total_samples=n_1x2,
        mean_clv_pct=mean_1x2,
        notes=(
            "Closing line snapshot taken T-5min; CLV > 0 means model picked the "
            "outcome the market later agreed with."
            if n_1x2 > 0 else
            "closing_odds table is filling in from the T-5min cron; data accumulates over time."
        ),
    ))

    # Placeholder rows for markets we don't yet snapshot at close. Surfacing
    # the zero state so users know where the gap is.
    for market in ("OU", "AH", "BTTS"):
        out.append(MarketCLV(
            market=market,
            total_samples=0,
            mean_clv_pct=None,
            notes="no closing snapshots stored yet for this market",
        ))

    return CLVByMarketResponse(markets=out)
