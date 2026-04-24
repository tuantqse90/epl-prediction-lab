"""GET /api/stats/equity-curve — flat-stake P&L per season.

Each season's return from staking 1u at best-available odds on every
matchup where model edge ≥ threshold. Shows whether the edge holds
season over season or is just recent-variance noise.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel


router = APIRouter(prefix="/api/stats", tags=["stats"])


class SeasonResult(BaseModel):
    season: str
    bets: int
    wins: int
    pnl: float
    roi_percent: float
    cumulative_pnl: float


class EquityCurveResponse(BaseModel):
    threshold: float
    seasons: list[SeasonResult]


@router.get("/equity-curve", response_model=EquityCurveResponse)
async def equity_curve(
    request: Request,
    threshold: float = Query(0.05, ge=0.0, le=0.30),
    league: str | None = Query(None),
) -> EquityCurveResponse:
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
                FROM match_odds o
                GROUP BY o.match_id
            ),
            graded AS (
                SELECT m.season,
                       l.p_home_win, l.p_draw, l.p_away_win,
                       b.bh, b.bd, b.ba,
                       m.home_goals, m.away_goals
                FROM matches m
                JOIN latest l ON l.match_id = m.id
                LEFT JOIN best b ON b.match_id = m.id
                WHERE m.status = 'final'
                  AND m.home_goals IS NOT NULL
                  AND ($2::text IS NULL OR m.league_code = $2)
            ),
            picks AS (
                SELECT season, home_goals, away_goals,
                  CASE
                    WHEN p_home_win >= p_draw AND p_home_win >= p_away_win
                         AND bh IS NOT NULL AND p_home_win * bh - 1 >= $1
                      THEN 'H'
                    WHEN p_draw >= p_home_win AND p_draw >= p_away_win
                         AND bd IS NOT NULL AND p_draw * bd - 1 >= $1
                      THEN 'D'
                    WHEN p_away_win >= p_home_win AND p_away_win >= p_draw
                         AND ba IS NOT NULL AND p_away_win * ba - 1 >= $1
                      THEN 'A'
                  END AS side,
                  bh, bd, ba
                FROM graded
            )
            SELECT season,
                   COUNT(*) FILTER (WHERE side IS NOT NULL)::int AS bets,
                   COUNT(*) FILTER (
                     WHERE (side = 'H' AND home_goals > away_goals)
                        OR (side = 'D' AND home_goals = away_goals)
                        OR (side = 'A' AND home_goals < away_goals)
                   )::int AS wins,
                   COALESCE(SUM(
                     CASE side
                       WHEN 'H' THEN CASE WHEN home_goals > away_goals THEN bh - 1 ELSE -1 END
                       WHEN 'D' THEN CASE WHEN home_goals = away_goals THEN bd - 1 ELSE -1 END
                       WHEN 'A' THEN CASE WHEN home_goals < away_goals THEN ba - 1 ELSE -1 END
                     END
                   ), 0)::float AS pnl
            FROM picks
            GROUP BY season
            ORDER BY season ASC
            """,
            threshold, league,
        )
    seasons: list[SeasonResult] = []
    cumulative = 0.0
    for r in rows:
        bets = int(r["bets"] or 0)
        pnl = float(r["pnl"] or 0.0)
        cumulative += pnl
        seasons.append(SeasonResult(
            season=r["season"],
            bets=bets,
            wins=int(r["wins"] or 0),
            pnl=pnl,
            roi_percent=(pnl / bets * 100) if bets > 0 else 0.0,
            cumulative_pnl=cumulative,
        ))
    return EquityCurveResponse(threshold=threshold, seasons=seasons)
