"""Site-wide search — teams, players, and upcoming matches.

Cheap ILIKE queries (no full-text index) backed by a 60-second in-memory
cache per (query, league) tuple. Shape designed for a Ctrl-K palette:
every result has (type, label, href) so the FE renders a flat list.
"""

from __future__ import annotations

import re
import time

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel


def _player_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchHit(BaseModel):
    type: str        # 'team' | 'player' | 'match'
    label: str
    sublabel: str | None = None
    href: str


_CACHE: dict[tuple[str, str], tuple[float, list[SearchHit]]] = {}
_CACHE_TTL = 60


@router.get("", response_model=list[SearchHit])
async def search(
    request: Request,
    q: str = Query(..., min_length=2, max_length=64),
    limit: int = Query(8, ge=1, le=20),
) -> list[SearchHit]:
    q_trim = q.strip()
    key = (q_trim.lower(), str(limit))
    now = time.time()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < _CACHE_TTL:
        return hit[1]

    pool = request.app.state.pool
    pattern = f"%{q_trim}%"

    async with pool.acquire() as conn:
        teams = await conn.fetch(
            """
            SELECT slug, name, short_name
            FROM teams
            WHERE name ILIKE $1 OR short_name ILIKE $1
            ORDER BY
                (CASE WHEN name ILIKE $2 THEN 0 ELSE 1 END),  -- prefix match first
                name
            LIMIT $3
            """,
            pattern, f"{q_trim}%", limit,
        )
        players = await conn.fetch(
            """
            SELECT DISTINCT ON (p.player_name)
                p.player_name, t.slug AS team_slug, t.short_name AS team_short
            FROM player_season_stats p
            JOIN teams t ON t.id = p.team_id
            WHERE p.player_name ILIKE $1
              AND p.season = '2025-26'
            ORDER BY p.player_name
            LIMIT $2
            """,
            pattern, limit,
        )
        matches = await conn.fetch(
            """
            SELECT m.id, m.kickoff_time, ht.short_name AS home_short, at.short_name AS away_short
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.status = 'scheduled'
              AND (ht.name ILIKE $1 OR at.name ILIKE $1)
              AND m.kickoff_time >= NOW()
              AND m.kickoff_time < NOW() + INTERVAL '21 days'
            ORDER BY m.kickoff_time ASC
            LIMIT $2
            """,
            pattern, limit,
        )

    results: list[SearchHit] = []
    for r in teams:
        results.append(SearchHit(
            type="team",
            label=r["name"],
            sublabel=r["short_name"],
            href=f"/teams/{r['slug']}",
        ))
    for r in players:
        results.append(SearchHit(
            type="player",
            label=r["player_name"],
            sublabel=r["team_short"],
            href=f"/players/{_player_slug(r['player_name'])}",
        ))
    for r in matches:
        results.append(SearchHit(
            type="match",
            label=f"{r['home_short']} vs {r['away_short']}",
            sublabel=r["kickoff_time"].date().isoformat(),
            href=f"/match/{r['id']}",
        ))

    _CACHE[key] = (now, results)
    return results
