"""GET /api/teams/:slug — season stats + form + top scorers + fixtures."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/teams", tags=["teams"])


class TeamStats(BaseModel):
    played: int
    wins: int
    draws: int
    losses: int
    points: int
    goals_for: int
    goals_against: int
    xg_for: float
    xg_against: float


class TopScorer(BaseModel):
    player_name: str
    position: str | None
    goals: int
    xg: float
    assists: int
    xa: float
    photo_url: str | None = None


class FixtureBrief(BaseModel):
    id: int
    kickoff_time: datetime
    status: str
    home_slug: str
    home_short: str
    away_slug: str
    away_short: str
    home_goals: int | None = None
    away_goals: int | None = None
    is_home: bool


class TeamProfile(BaseModel):
    slug: str
    name: str
    short_name: str
    season: str
    stats: TeamStats
    form: list[str]                  # last 10, newest first: W/D/L
    top_scorers: list[TopScorer]
    recent: list[FixtureBrief]
    upcoming: list[FixtureBrief]


class TrajectoryPoint(BaseModel):
    kickoff_time: datetime
    xg_for: float
    xg_against: float
    goals_for: int
    goals_against: int
    is_home: bool
    opponent_short: str


class TrajectoryOut(BaseModel):
    slug: str
    season: str
    points: list[TrajectoryPoint]


async def _stats(conn, team_id: int, season: str) -> TeamStats:
    row = await conn.fetchrow(
        """
        SELECT
            COUNT(*) AS played,
            SUM(CASE
                WHEN (m.home_team_id=$1 AND m.home_goals > m.away_goals)
                  OR (m.away_team_id=$1 AND m.away_goals > m.home_goals) THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN m.home_goals = m.away_goals THEN 1 ELSE 0 END) AS draws,
            SUM(CASE
                WHEN (m.home_team_id=$1 AND m.home_goals < m.away_goals)
                  OR (m.away_team_id=$1 AND m.away_goals < m.home_goals) THEN 1 ELSE 0 END) AS losses,
            SUM(CASE WHEN m.home_team_id=$1 THEN m.home_goals ELSE m.away_goals END)::int AS gf,
            SUM(CASE WHEN m.home_team_id=$1 THEN m.away_goals ELSE m.home_goals END)::int AS ga,
            COALESCE(SUM(CASE WHEN m.home_team_id=$1 THEN m.home_xg ELSE m.away_xg END), 0) AS xgf,
            COALESCE(SUM(CASE WHEN m.home_team_id=$1 THEN m.away_xg ELSE m.home_xg END), 0) AS xga
        FROM matches m
        WHERE m.status = 'final' AND m.season = $2
          AND (m.home_team_id = $1 OR m.away_team_id = $1)
          AND m.home_goals IS NOT NULL
        """,
        team_id, season,
    )
    wins = row["wins"] or 0
    draws = row["draws"] or 0
    return TeamStats(
        played=row["played"] or 0,
        wins=wins,
        draws=draws,
        losses=row["losses"] or 0,
        points=wins * 3 + draws,
        goals_for=row["gf"] or 0,
        goals_against=row["ga"] or 0,
        xg_for=round(float(row["xgf"] or 0), 2),
        xg_against=round(float(row["xga"] or 0), 2),
    )


async def _form(conn, team_id: int, season: str) -> list[str]:
    rows = await conn.fetch(
        """
        SELECT m.home_team_id, m.home_goals, m.away_goals
        FROM matches m
        WHERE m.status='final' AND m.season=$2
          AND (m.home_team_id=$1 OR m.away_team_id=$1)
          AND m.home_goals IS NOT NULL
        ORDER BY m.kickoff_time DESC
        LIMIT 10
        """,
        team_id, season,
    )
    form: list[str] = []
    for r in rows:
        hg, ag = r["home_goals"], r["away_goals"]
        is_home = r["home_team_id"] == team_id
        gf, ga = (hg, ag) if is_home else (ag, hg)
        form.append("W" if gf > ga else ("D" if gf == ga else "L"))
    return form


async def _top_scorers(conn, team_id: int, season: str, n: int = 5) -> list[TopScorer]:
    rows = await conn.fetch(
        """
        SELECT player_name, position, goals, xg, assists, xa, photo_url
        FROM player_season_stats
        WHERE team_id = $1 AND season = $2
        ORDER BY goals DESC NULLS LAST, xg DESC NULLS LAST
        LIMIT $3
        """,
        team_id, season, n,
    )
    return [
        TopScorer(
            player_name=r["player_name"],
            position=r["position"],
            goals=r["goals"] or 0,
            xg=round(float(r["xg"] or 0), 2),
            assists=r["assists"] or 0,
            xa=round(float(r["xa"] or 0), 2),
            photo_url=r["photo_url"],
        )
        for r in rows
    ]


async def _fixtures(conn, team_id: int, season: str) -> tuple[list[FixtureBrief], list[FixtureBrief]]:
    rows = await conn.fetch(
        """
        SELECT m.id, m.kickoff_time, m.status, m.home_team_id, m.away_team_id,
               m.home_goals, m.away_goals,
               ht.slug AS home_slug, ht.short_name AS home_short,
               at.slug AS away_slug, at.short_name AS away_short
        FROM matches m
        JOIN teams ht ON ht.id = m.home_team_id
        JOIN teams at ON at.id = m.away_team_id
        WHERE m.season = $2 AND (m.home_team_id=$1 OR m.away_team_id=$1)
        ORDER BY m.kickoff_time ASC
        """,
        team_id, season,
    )
    recent: list[FixtureBrief] = []
    upcoming: list[FixtureBrief] = []
    for r in rows:
        f = FixtureBrief(
            id=r["id"],
            kickoff_time=r["kickoff_time"],
            status=r["status"],
            home_slug=r["home_slug"],
            home_short=r["home_short"],
            away_slug=r["away_slug"],
            away_short=r["away_short"],
            home_goals=r["home_goals"],
            away_goals=r["away_goals"],
            is_home=(r["home_team_id"] == team_id),
        )
        if f.status == "final":
            recent.append(f)
        else:
            upcoming.append(f)
    return recent[-5:][::-1], upcoming[:5]


@router.get("/{slug}/trajectory", response_model=TrajectoryOut)
async def get_trajectory(
    slug: str,
    request: Request,
    season: str = Query("2025-26"),
) -> TrajectoryOut:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        team = await conn.fetchrow("SELECT id FROM teams WHERE slug = $1", slug)
        if team is None:
            raise HTTPException(404, f"team {slug} not found")
        rows = await conn.fetch(
            """
            SELECT m.kickoff_time,
                   (m.home_team_id = $1) AS is_home,
                   CASE WHEN m.home_team_id = $1 THEN m.home_xg ELSE m.away_xg END AS xg_for,
                   CASE WHEN m.home_team_id = $1 THEN m.away_xg ELSE m.home_xg END AS xg_against,
                   CASE WHEN m.home_team_id = $1 THEN m.home_goals ELSE m.away_goals END AS goals_for,
                   CASE WHEN m.home_team_id = $1 THEN m.away_goals ELSE m.home_goals END AS goals_against,
                   CASE WHEN m.home_team_id = $1 THEN at.short_name ELSE ht.short_name END AS opp
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.season = $2 AND m.status = 'final'
              AND (m.home_team_id = $1 OR m.away_team_id = $1)
              AND m.home_xg IS NOT NULL AND m.away_xg IS NOT NULL
            ORDER BY m.kickoff_time ASC
            """,
            team["id"], season,
        )
    return TrajectoryOut(
        slug=slug,
        season=season,
        points=[
            TrajectoryPoint(
                kickoff_time=r["kickoff_time"],
                xg_for=float(r["xg_for"] or 0),
                xg_against=float(r["xg_against"] or 0),
                goals_for=int(r["goals_for"] or 0),
                goals_against=int(r["goals_against"] or 0),
                is_home=bool(r["is_home"]),
                opponent_short=r["opp"],
            )
            for r in rows
        ],
    )


@router.get("/{slug}", response_model=TeamProfile)
async def get_team(slug: str, request: Request, season: str = Query("2025-26")) -> TeamProfile:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        team = await conn.fetchrow(
            "SELECT id, slug, name, short_name FROM teams WHERE slug = $1", slug
        )
        if team is None:
            raise HTTPException(404, f"team {slug} not found")
        stats = await _stats(conn, team["id"], season)
        form = await _form(conn, team["id"], season)
        scorers = await _top_scorers(conn, team["id"], season)
        recent, upcoming = await _fixtures(conn, team["id"], season)
    return TeamProfile(
        slug=team["slug"],
        name=team["name"],
        short_name=team["short_name"],
        season=season,
        stats=stats,
        form=form,
        top_scorers=scorers,
        recent=recent,
        upcoming=upcoming,
    )
