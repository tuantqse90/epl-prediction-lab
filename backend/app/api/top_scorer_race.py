"""GET /api/stats/top-scorer-race — Golden Boot / Pichichi projection.

Joins player_season_stats with each team's remaining matches this
season, projects final goal total via xG/match rate.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.models.top_scorer_race import rank_scorer_race


router = APIRouter(prefix="/api/stats", tags=["stats"])


class ScorerProjection(BaseModel):
    rank: int
    player_name: str
    team_slug: str
    team_short: str
    league_code: str
    goals: int
    xg: float
    games: int
    team_remaining: int
    xg_per_match: float
    projected: float
    gap_to_leader: float
    photo_url: str | None = None


class ScorerRaceResponse(BaseModel):
    league_code: str
    season: str
    players: list[ScorerProjection]


@router.get("/top-scorer-race", response_model=ScorerRaceResponse)
async def top_scorer_race(
    request: Request,
    league: str = Query(..., description="league code"),
    season: str = Query("2025-26"),
    limit: int = Query(20, ge=5, le=50),
) -> ScorerRaceResponse:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH remaining AS (
                SELECT home_team_id AS team_id, COUNT(*)::int AS n
                FROM matches
                WHERE league_code = $1 AND season = $2 AND status = 'scheduled'
                GROUP BY home_team_id
                UNION ALL
                SELECT away_team_id, COUNT(*)::int
                FROM matches
                WHERE league_code = $1 AND season = $2 AND status = 'scheduled'
                GROUP BY away_team_id
            ),
            per_team AS (
                SELECT team_id, COALESCE(SUM(n), 0)::int AS remaining
                FROM remaining GROUP BY team_id
            )
            SELECT ps.player_name, ps.goals, ps.xg, ps.games,
                   ps.photo_url,
                   t.slug AS team_slug, t.short_name AS team_short,
                   COALESCE(rt.remaining, 0) AS team_remaining
            FROM player_season_stats ps
            JOIN teams t ON t.id = ps.team_id
            LEFT JOIN per_team rt ON rt.team_id = ps.team_id
            JOIN matches m ON (m.home_team_id = t.id OR m.away_team_id = t.id)
            WHERE ps.season = $2
              AND m.league_code = $1
              AND ps.goals >= 5
            GROUP BY ps.player_name, ps.goals, ps.xg, ps.games, ps.photo_url,
                     t.slug, t.short_name, rt.remaining
            ORDER BY ps.goals DESC, ps.xg DESC
            LIMIT 80
            """,
            league, season,
        )
    enriched = rank_scorer_race([
        {
            "player": r["player_name"],
            "goals": int(r["goals"] or 0),
            "xg": float(r["xg"] or 0),
            "games": int(r["games"] or 0),
            "team_remaining": int(r["team_remaining"] or 0),
            "team_slug": r["team_slug"],
            "team_short": r["team_short"],
            "photo_url": r["photo_url"],
        }
        for r in rows
    ])
    players: list[ScorerProjection] = []
    for i, e in enumerate(enriched[:limit], start=1):
        players.append(ScorerProjection(
            rank=i,
            player_name=e["player"],
            team_slug=e["team_slug"],
            team_short=e["team_short"],
            league_code=league,
            goals=int(e["goals"]),
            xg=float(e["xg"]),
            games=int(e["games"]),
            team_remaining=int(e["team_remaining"]),
            xg_per_match=float(e["xg_per_match"]),
            projected=float(e["projected"]),
            gap_to_leader=float(e["gap_to_leader"]),
            photo_url=e.get("photo_url"),
        ))
    return ScorerRaceResponse(league_code=league, season=season, players=players)
