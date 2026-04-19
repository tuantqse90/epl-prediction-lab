"""GET /api/table — league season table with xG-based columns side-by-side."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.leagues import get_league

router = APIRouter(prefix="/api/table", tags=["table"])


class TableRow(BaseModel):
    rank: int
    slug: str
    name: str
    short_name: str
    played: int
    wins: int
    draws: int
    losses: int
    points: int
    goals_for: int
    goals_against: int
    goal_diff: int
    xg_for: float
    xg_against: float
    xg_diff: float


_TABLE_QUERY = """
WITH per_match AS (
    SELECT
        t.id, t.slug, t.name, t.short_name,
        CASE
            WHEN m.home_team_id = t.id AND m.home_goals >  m.away_goals THEN 3
            WHEN m.away_team_id = t.id AND m.away_goals >  m.home_goals THEN 3
            WHEN m.home_goals = m.away_goals                            THEN 1
            ELSE 0
        END AS pts,
        (CASE
            WHEN m.home_team_id = t.id AND m.home_goals >  m.away_goals THEN 1
            WHEN m.away_team_id = t.id AND m.away_goals >  m.home_goals THEN 1
            ELSE 0
        END) AS is_win,
        (CASE WHEN m.home_goals =  m.away_goals THEN 1 ELSE 0 END) AS is_draw,
        (CASE
            WHEN m.home_team_id = t.id AND m.home_goals <  m.away_goals THEN 1
            WHEN m.away_team_id = t.id AND m.away_goals <  m.home_goals THEN 1
            ELSE 0
        END) AS is_loss,
        (CASE WHEN m.home_team_id = t.id THEN m.home_goals ELSE m.away_goals END) AS gf,
        (CASE WHEN m.home_team_id = t.id THEN m.away_goals ELSE m.home_goals END) AS ga,
        COALESCE(CASE WHEN m.home_team_id = t.id THEN m.home_xg ELSE m.away_xg END, 0) AS xgf,
        COALESCE(CASE WHEN m.home_team_id = t.id THEN m.away_xg ELSE m.home_xg END, 0) AS xga
    FROM teams t
    JOIN matches m
      ON (m.home_team_id = t.id OR m.away_team_id = t.id)
    WHERE m.status = 'final'
      AND m.season = $1
      AND m.home_goals IS NOT NULL
      AND m.away_goals IS NOT NULL
      AND ($2::text IS NULL OR m.league_code = $2)
)
SELECT
    slug, name, short_name,
    COUNT(*)        AS played,
    SUM(is_win)     AS wins,
    SUM(is_draw)    AS draws,
    SUM(is_loss)    AS losses,
    SUM(pts)        AS points,
    SUM(gf)::int    AS goals_for,
    SUM(ga)::int    AS goals_against,
    SUM(xgf)        AS xg_for,
    SUM(xga)        AS xg_against
FROM per_match
GROUP BY slug, name, short_name
ORDER BY points DESC, (SUM(gf) - SUM(ga)) DESC, SUM(gf) DESC
"""


@router.get("", response_model=list[TableRow])
async def get_table(
    request: Request,
    season: str = Query("2025-26", description="season, e.g. 2025-26"),
    league: str | None = Query(None, description="league slug or code (epl, laliga, …)"),
) -> list[TableRow]:
    pool = request.app.state.pool
    league_code: str | None = None
    if league:
        try:
            league_code = get_league(league).code
        except KeyError:
            league_code = None
    async with pool.acquire() as conn:
        rows = await conn.fetch(_TABLE_QUERY, season, league_code)
    out: list[TableRow] = []
    for i, r in enumerate(rows, start=1):
        gf, ga = int(r["goals_for"]), int(r["goals_against"])
        xgf, xga = float(r["xg_for"]), float(r["xg_against"])
        out.append(
            TableRow(
                rank=i,
                slug=r["slug"],
                name=r["name"],
                short_name=r["short_name"],
                played=r["played"],
                wins=r["wins"],
                draws=r["draws"],
                losses=r["losses"],
                points=r["points"],
                goals_for=gf,
                goals_against=ga,
                goal_diff=gf - ga,
                xg_for=round(xgf, 2),
                xg_against=round(xga, 2),
                xg_diff=round(xgf - xga, 2),
            )
        )
    return out
