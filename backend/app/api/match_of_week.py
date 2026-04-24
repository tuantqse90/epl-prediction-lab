"""GET /api/stats/match-of-week — auto-picked biggest-edge fixture.

Picks the match with the highest edge where the model pick is above a
reasonable confidence floor (≥ 45%). Runs live — no caching table —
cheap enough at 1 SQL call.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel


router = APIRouter(prefix="/api/stats", tags=["stats"])


class MatchOfWeek(BaseModel):
    match_id: int
    league_code: str | None
    kickoff_time: datetime
    home_short: str
    away_short: str
    home_slug: str
    away_slug: str
    pick: str
    confidence: float
    best_odds: float
    edge_pp: float


@router.get("/match-of-week", response_model=MatchOfWeek | None)
async def match_of_week(request: Request) -> MatchOfWeek | None:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH latest AS (
                SELECT DISTINCT ON (p.match_id)
                  p.match_id, p.p_home_win, p.p_draw, p.p_away_win
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            ),
            best AS (
                SELECT o.match_id,
                       MAX(o.odds_home) AS bh,
                       MAX(o.odds_draw) AS bd,
                       MAX(o.odds_away) AS ba
                FROM match_odds o GROUP BY o.match_id
            )
            SELECT m.id, m.league_code, m.kickoff_time,
                   ht.short_name AS home_short, at.short_name AS away_short,
                   ht.slug AS home_slug, at.slug AS away_slug,
                   l.p_home_win, l.p_draw, l.p_away_win,
                   b.bh, b.bd, b.ba
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            JOIN latest l ON l.match_id = m.id
            LEFT JOIN best b ON b.match_id = m.id
            WHERE m.status = 'scheduled'
              AND m.kickoff_time BETWEEN NOW() AND NOW() + INTERVAL '7 days'
            """,
        )
    best: MatchOfWeek | None = None
    best_edge = -1.0
    for r in rows:
        probs = {"H": r["p_home_win"], "D": r["p_draw"], "A": r["p_away_win"]}
        pick = max(probs, key=probs.get)
        conf = float(probs[pick])
        if conf < 0.45:
            continue
        odds = {"H": r["bh"], "D": r["bd"], "A": r["ba"]}[pick]
        if odds is None:
            continue
        edge_pp = (conf * float(odds) - 1.0) * 100
        if edge_pp <= best_edge or edge_pp > 30.0:
            continue
        best_edge = edge_pp
        best = MatchOfWeek(
            match_id=r["id"],
            league_code=r["league_code"],
            kickoff_time=r["kickoff_time"],
            home_short=r["home_short"], away_short=r["away_short"],
            home_slug=r["home_slug"], away_slug=r["away_slug"],
            pick=pick, confidence=conf,
            best_odds=float(odds), edge_pp=edge_pp,
        )
    return best
