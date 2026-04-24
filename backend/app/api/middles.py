"""GET /api/stats/middles — O/U middle opportunities for upcoming fixtures."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.models.middles import find_ou_middles


router = APIRouter(prefix="/api/stats", tags=["stats"])


class MiddleRow(BaseModel):
    match_id: int
    league_code: str | None
    kickoff_time: datetime
    home_short: str
    away_short: str
    middle_low: float
    middle_high: float
    source_over: str
    source_under: str
    odds_over: float
    odds_under: float
    middle_pnl: float
    miss_pnl_low: float
    miss_pnl_high: float


class MiddlesResponse(BaseModel):
    checked: int
    opportunities: list[MiddleRow]


@router.get("/middles", response_model=MiddlesResponse)
async def middles(
    request: Request,
    league: str | None = Query(None),
    horizon_days: int = Query(14, ge=1, le=60),
    min_middle_pnl: float = Query(0.5, ge=0.0, le=5.0),
) -> MiddlesResponse:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.id, m.league_code, m.kickoff_time,
                   ht.short_name AS home_short, at.short_name AS away_short,
                   mom.source, mom.line, mom.outcome_code, mom.odds
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            LEFT JOIN match_odds_markets mom
              ON mom.match_id = m.id AND mom.market_code = 'OU'
            WHERE m.status = 'scheduled'
              AND m.kickoff_time BETWEEN NOW() AND NOW() + ($1 || ' days')::INTERVAL
              AND ($2::text IS NULL OR m.league_code = $2)
            ORDER BY m.id ASC
            """,
            str(horizon_days), league,
        )

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
            "ou": [],
        })
        if r["source"] and r["line"] is not None and r["outcome_code"]:
            per_match[mid]["ou"].append(SimpleNamespace(
                source=r["source"],
                line=float(r["line"]),
                outcome_code=r["outcome_code"],
                odds=float(r["odds"]),
            ))

    out: list[MiddleRow] = []
    for mid, data in per_match.items():
        candidates = find_ou_middles(data["ou"])
        for c in candidates:
            if c["middle_pnl"] < min_middle_pnl:
                continue
            out.append(MiddleRow(match_id=mid, **data["meta"], **c))
    out.sort(key=lambda r: -r.middle_pnl)
    return MiddlesResponse(checked=len(per_match), opportunities=out[:100])
