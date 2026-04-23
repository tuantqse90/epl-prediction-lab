"""GET /api/teams/:slug — season stats + form + top scorers + fixtures."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/teams", tags=["teams"])


class TeamBrief(BaseModel):
    slug: str
    name: str
    short_name: str
    league_code: str | None = None


@router.get("", response_model=list[TeamBrief])
async def list_teams(
    request: Request,
    season: str = Query("2025-26"),
    league: str | None = Query(None),
) -> list[TeamBrief]:
    """Flat list of teams with scheduled/final matches this season. Backs the
    `/compare` team picker + any UI that needs a canonical team roster.

    `league` is the full league_code (e.g. 'ENG-Premier League') — matching
    the `matches.league_code` column, not the FE slug. When absent, returns
    every league in the DB."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT t.slug, t.name, t.short_name, m.league_code
            FROM teams t
            JOIN matches m ON (m.home_team_id = t.id OR m.away_team_id = t.id)
            WHERE m.season = $1
              AND ($2::text IS NULL OR m.league_code = $2)
            ORDER BY t.name
            """,
            season, league,
        )
    return [
        TeamBrief(
            slug=r["slug"], name=r["name"],
            short_name=r["short_name"], league_code=r["league_code"],
        )
        for r in rows
    ]


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
    league_code: str | None = None
    league_rank: int | None = None      # 1-based position in league table
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
        SELECT player_name, position, goals, xg, assists, xa, photo_url,
               api_football_player_id
        FROM player_season_stats
        WHERE team_id = $1 AND season = $2
        ORDER BY goals DESC NULLS LAST, xg DESC NULLS LAST
        LIMIT $3
        """,
        team_id, season, n,
    )
    out: list[TopScorer] = []
    for r in rows:
        af_id = r["api_football_player_id"]
        photo_url = f"/api/players/photo/{int(af_id)}" if af_id else r["photo_url"]
        out.append(
            TopScorer(
                player_name=r["player_name"],
                position=r["position"],
                goals=r["goals"] or 0,
                xg=round(float(r["xg"] or 0), 2),
                assists=r["assists"] or 0,
                xa=round(float(r["xa"] or 0), 2),
                photo_url=photo_url,
            )
        )
    return out


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


class TeamNarrative(BaseModel):
    team_slug: str
    season: str
    lang: str
    story: str
    generated_at: datetime


@router.get("/{slug}/narrative", response_model=TeamNarrative | None)
async def get_team_narrative(
    slug: str,
    request: Request,
    season: str = Query("2025-26"),
    lang: str = Query("en"),
) -> TeamNarrative | None:
    """Long-form auto-generated story for the team page. Null if not yet
    generated — team page should then hide the section gracefully."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT team_slug, season, lang, story, generated_at
            FROM team_narratives
            WHERE team_slug = $1 AND season = $2 AND lang = $3
            """,
            slug, season, lang,
        )
    if not row:
        return None
    return TeamNarrative(**dict(row))


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

        # Resolve primary league for this team (most-played in season),
        # then compute rank among its league-mates by points (with GD,
        # goals-for as tiebreakers) — matches how the /table page sorts.
        league_row = await conn.fetchrow(
            """
            SELECT league_code, COUNT(*) AS n
            FROM matches
            WHERE season = $2
              AND (home_team_id = $1 OR away_team_id = $1)
              AND league_code IS NOT NULL
            GROUP BY league_code
            ORDER BY n DESC NULLS LAST
            LIMIT 1
            """,
            team["id"], season,
        )
        league_code = league_row["league_code"] if league_row else None

        league_rank: int | None = None
        if league_code:
            rank_row = await conn.fetchrow(
                """
                WITH finals AS (
                    SELECT m.home_team_id AS team_id,
                           CASE WHEN m.home_goals > m.away_goals THEN 3
                                WHEN m.home_goals = m.away_goals THEN 1 ELSE 0 END AS pts,
                           m.home_goals AS gf, m.away_goals AS ga
                    FROM matches m
                    WHERE m.season = $1 AND m.league_code = $2 AND m.status = 'final'
                      AND m.home_goals IS NOT NULL
                    UNION ALL
                    SELECT m.away_team_id AS team_id,
                           CASE WHEN m.away_goals > m.home_goals THEN 3
                                WHEN m.away_goals = m.home_goals THEN 1 ELSE 0 END AS pts,
                           m.away_goals AS gf, m.home_goals AS ga
                    FROM matches m
                    WHERE m.season = $1 AND m.league_code = $2 AND m.status = 'final'
                      AND m.home_goals IS NOT NULL
                ),
                agg AS (
                    SELECT team_id,
                           SUM(pts) AS points,
                           SUM(gf) - SUM(ga) AS gd,
                           SUM(gf) AS gf
                    FROM finals GROUP BY team_id
                ),
                ranked AS (
                    SELECT team_id,
                           RANK() OVER (
                             ORDER BY points DESC NULLS LAST,
                                      gd DESC NULLS LAST,
                                      gf DESC NULLS LAST
                           ) AS rnk
                    FROM agg
                )
                SELECT rnk FROM ranked WHERE team_id = $3
                """,
                season, league_code, team["id"],
            )
            if rank_row:
                league_rank = int(rank_row["rnk"])

    return TeamProfile(
        slug=team["slug"],
        name=team["name"],
        short_name=team["short_name"],
        season=season,
        league_code=league_code,
        league_rank=league_rank,
        stats=stats,
        form=form,
        top_scorers=scorers,
        recent=recent,
        upcoming=upcoming,
    )
