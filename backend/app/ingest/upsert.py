"""asyncpg upsert layer — thin glue around INSERT … ON CONFLICT.

Not unit-tested. Verified by running `scripts/ingest_season.py` against a real
Postgres instance (brought up via the repo's docker-compose).
"""

from __future__ import annotations

from typing import Iterable

import asyncpg

from app.ingest.schedule import MatchRow, TeamRow

_UPSERT_TEAM = """
INSERT INTO teams (slug, name, short_name)
VALUES ($1, $2, $3)
ON CONFLICT (slug) DO UPDATE
    SET name = EXCLUDED.name,
        short_name = EXCLUDED.short_name,
        updated_at = NOW()
RETURNING id, slug
"""

_UPSERT_MATCH = """
INSERT INTO matches (
    external_id, season, kickoff_time,
    home_team_id, away_team_id,
    home_goals, away_goals, home_xg, away_xg, status
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
ON CONFLICT (external_id) DO UPDATE SET
    kickoff_time = EXCLUDED.kickoff_time,
    home_goals   = EXCLUDED.home_goals,
    away_goals   = EXCLUDED.away_goals,
    home_xg      = EXCLUDED.home_xg,
    away_xg      = EXCLUDED.away_xg,
    status       = EXCLUDED.status
"""


async def upsert_all(
    pool: asyncpg.Pool,
    teams: Iterable[TeamRow],
    matches: Iterable[MatchRow],
) -> tuple[int, int]:
    """Upsert teams then matches inside a single transaction. Returns (n_teams, n_matches)."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            slug_to_id: dict[str, int] = {}
            team_count = 0
            for t in teams:
                row = await conn.fetchrow(_UPSERT_TEAM, t.slug, t.name, t.short_name)
                slug_to_id[row["slug"]] = row["id"]
                team_count += 1

            match_count = 0
            for m in matches:
                await conn.execute(
                    _UPSERT_MATCH,
                    m.external_id,
                    m.season,
                    m.kickoff_time.to_pydatetime(),
                    slug_to_id[m.home_slug],
                    slug_to_id[m.away_slug],
                    m.home_goals,
                    m.away_goals,
                    m.home_xg,
                    m.away_xg,
                    m.status,
                )
                match_count += 1
            return team_count, match_count
