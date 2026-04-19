"""GET /api/matches — upcoming fixtures with latest prediction joined."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app import queries
from app.schemas import MatchOut

router = APIRouter(prefix="/api/matches", tags=["matches"])


class H2HMatch(BaseModel):
    match_id: int
    kickoff_date: str
    season: str
    league_code: str | None
    home_slug: str
    home_short: str
    home_goals: int
    away_slug: str
    away_short: str
    away_goals: int


class Injury(BaseModel):
    team_slug: str
    player_name: str
    reason: str | None
    status_label: str | None
    last_seen_at: str


class MatchInjuries(BaseModel):
    home: list[Injury]
    away: list[Injury]


@router.get("", response_model=list[MatchOut])
async def list_matches(
    request: Request,
    upcoming_only: bool = Query(True, description="Only matches with kickoff in the future"),
    limit: int = Query(20, ge=1, le=200),
    league: str | None = Query(None, description="league slug or code (e.g. epl, laliga)"),
) -> list[MatchOut]:
    from app.leagues import get_league
    league_code = get_league(league).code if league else None
    rows = await queries.list_matches(
        request.app.state.pool,
        upcoming_only=upcoming_only,
        limit=limit,
        league_code=league_code,
    )
    return [MatchOut.model_validate(queries.record_to_match_dict(r)) for r in rows]


@router.get("/{match_id}", response_model=MatchOut)
async def get_match(match_id: int, request: Request) -> MatchOut:
    pool = request.app.state.pool
    row = await queries.get_match(pool, match_id)
    if row is None:
        raise HTTPException(404, f"match {match_id} not found")
    data = queries.record_to_match_dict(row)
    data["events"] = await queries.get_match_events(pool, match_id)
    return MatchOut.model_validate(data)


@router.get("/{match_id}/h2h", response_model=list[H2HMatch])
async def match_h2h(
    match_id: int,
    request: Request,
    limit: int = Query(5, ge=1, le=20),
) -> list[H2HMatch]:
    """Last N completed meetings between the two teams (any league, any season)."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        pair = await conn.fetchrow(
            """
            SELECT ht.name AS home_name, at.name AS away_name, m.kickoff_time
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.id = $1
            """,
            match_id,
        )
        if pair is None:
            raise HTTPException(404, f"match {match_id} not found")

        rows = await conn.fetch(
            """
            SELECT m.id AS match_id, m.kickoff_time, m.season, m.league_code,
                   m.home_goals, m.away_goals,
                   ht.slug AS home_slug, ht.short_name AS home_short,
                   at.slug AS away_slug, at.short_name AS away_short
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.status = 'final'
              AND m.kickoff_time < $3
              AND m.home_goals IS NOT NULL
              AND (
                (ht.name = $1 AND at.name = $2)
                OR (ht.name = $2 AND at.name = $1)
              )
            ORDER BY m.kickoff_time DESC
            LIMIT $4
            """,
            pair["home_name"], pair["away_name"], pair["kickoff_time"], limit,
        )
    return [
        H2HMatch(
            match_id=r["match_id"],
            kickoff_date=r["kickoff_time"].date().isoformat(),
            season=r["season"],
            league_code=r["league_code"],
            home_slug=r["home_slug"],
            home_short=r["home_short"],
            home_goals=int(r["home_goals"]),
            away_slug=r["away_slug"],
            away_short=r["away_short"],
            away_goals=int(r["away_goals"]),
        )
        for r in rows
    ]


@router.get("/{match_id}/injuries", response_model=MatchInjuries)
async def match_injuries(match_id: int, request: Request) -> MatchInjuries:
    """Currently-reported absentees on each side (cached from API-Football)."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        pair = await conn.fetchrow(
            """
            SELECT ht.slug AS home_slug, at.slug AS away_slug, m.season
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.id = $1
            """,
            match_id,
        )
        if pair is None:
            raise HTTPException(404, f"match {match_id} not found")

        # API-Football /injuries returns every "Missing Fixture" event for
        # the season — most are historical. Status_label ∈ {'Missing Fixture',
        # 'Questionable'}. Only the latter is forward-looking; the former is a
        # past-absence record. We dedupe historical noise by selecting only
        # the most-recent row per player.
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (team_slug, player_name)
                   team_slug, player_name, reason, status_label, last_seen_at
            FROM player_injuries
            WHERE team_slug = ANY($1::text[])
              AND season = $2
              AND last_seen_at >= NOW() - INTERVAL '3 days'
              AND status_label <> 'Missing Fixture'
            ORDER BY team_slug, player_name, last_seen_at DESC
            """,
            [pair["home_slug"], pair["away_slug"]],
            pair["season"],
        )

    home_list: list[Injury] = []
    away_list: list[Injury] = []
    for r in rows:
        item = Injury(
            team_slug=r["team_slug"],
            player_name=r["player_name"],
            reason=r["reason"],
            status_label=r["status_label"],
            last_seen_at=r["last_seen_at"].isoformat(),
        )
        if r["team_slug"] == pair["home_slug"]:
            home_list.append(item)
        else:
            away_list.append(item)
    return MatchInjuries(home=home_list, away=away_list)
