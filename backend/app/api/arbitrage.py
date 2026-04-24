"""GET /api/stats/arbs — scan upcoming fixtures for positive arbs."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.models.arbitrage import best_arb


router = APIRouter(prefix="/api/stats", tags=["stats"])


class ArbRow(BaseModel):
    match_id: int
    league_code: str | None
    kickoff_time: datetime
    home_short: str
    away_short: str
    profit_percent: float
    home_source: str
    draw_source: str
    away_source: str
    home_odds: float
    draw_odds: float
    away_odds: float
    stake_home: float
    stake_draw: float
    stake_away: float


class ArbResponse(BaseModel):
    checked: int
    opportunities: list[ArbRow]


@router.get("/arbs", response_model=ArbResponse)
async def arbs(
    request: Request,
    league: str | None = Query(None),
    horizon_days: int = Query(14, ge=1, le=60),
    min_profit_pct: float = Query(0.2, ge=0.0, le=20.0),
) -> ArbResponse:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.id, m.league_code, m.kickoff_time,
                   ht.short_name AS home_short, at.short_name AS away_short,
                   o.source, o.odds_home, o.odds_draw, o.odds_away
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            LEFT JOIN match_odds o ON o.match_id = m.id
            WHERE m.status = 'scheduled'
              AND m.kickoff_time BETWEEN NOW() AND NOW() + ($1 || ' days')::INTERVAL
              AND ($2::text IS NULL OR m.league_code = $2)
            ORDER BY m.id ASC, o.source ASC
            """,
            str(horizon_days), league,
        )

    # Group by match
    per_match: dict[int, dict] = {}
    for r in rows:
        mid = r["id"]
        per_match.setdefault(mid, {
            "meta": {
                "league_code": r["league_code"],
                "kickoff_time": r["kickoff_time"],
                "home_short": r["home_short"],
                "away_short": r["away_short"],
            },
            "odds": [],
        })
        if r["source"]:
            per_match[mid]["odds"].append({
                "source": r["source"],
                "odds_home": r["odds_home"],
                "odds_draw": r["odds_draw"],
                "odds_away": r["odds_away"],
            })

    from types import SimpleNamespace
    out: list[ArbRow] = []
    for mid, data in per_match.items():
        odd_rows = [SimpleNamespace(**o) for o in data["odds"]]
        arb = best_arb(odd_rows)
        if arb is None or arb.profit_percent < min_profit_pct:
            continue
        out.append(ArbRow(
            match_id=mid,
            league_code=data["meta"]["league_code"],
            kickoff_time=data["meta"]["kickoff_time"],
            home_short=data["meta"]["home_short"],
            away_short=data["meta"]["away_short"],
            profit_percent=arb.profit_percent,
            home_source=arb.home_source, draw_source=arb.draw_source, away_source=arb.away_source,
            home_odds=arb.home_odds, draw_odds=arb.draw_odds, away_odds=arb.away_odds,
            stake_home=arb.stake_home, stake_draw=arb.stake_draw, stake_away=arb.stake_away,
        ))

    out.sort(key=lambda x: -x.profit_percent)
    return ArbResponse(checked=len(per_match), opportunities=out)
