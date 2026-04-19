"""Pull per-league injury list from API-Football and cache to DB.

API-Football exposes `/injuries?league=<id>&season=<YYYY>` which returns every
currently-reported absentee across the league in one shot — perfect for our
quota budget (5 leagues × 1 call ≈ 5 quota/run). Cron daily; the endpoint
ignores rapid refreshes anyway.

Env:
    API_FOOTBALL_KEY

Usage:
    python scripts/ingest_injuries.py [--season 2025] [--league laliga]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import urllib.request
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.leagues import LEAGUES, get_league


# API-Football uses full club names; map them back to the Understat-slug form
# we store in `teams.slug` via the same kebab-case rule as `slugify`.
def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# Reuse the same long-name mapping from ingest_live_scores so the slugs end
# up canonical. Keep in sync with that file — the failure mode is a no-op
# row (team_slug doesn't match any `teams.slug`, so FE joins skip it).
from scripts.ingest_live_scores import NAME_MAP  # noqa: E402


def _canon(name: str) -> str:
    return NAME_MAP.get(name, name)


def _fetch(api_key: str, league_id: int, season_year: int) -> list[dict]:
    url = f"https://v3.football.api-sports.io/injuries?league={league_id}&season={season_year}"
    req = urllib.request.Request(url, headers={"x-apisports-key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            remaining = resp.headers.get("x-ratelimit-requests-remaining")
            if remaining:
                print(f"[injuries] quota remaining: {remaining}")
            body = json.loads(resp.read())
    except Exception as e:
        print(f"[injuries] fetch failed for league={league_id}: {type(e).__name__}: {e}")
        return []
    return body.get("response", []) or []


async def _upsert(pool: asyncpg.Pool, rows: list[dict], league_code: str, season: str) -> int:
    if not rows:
        return 0
    n = 0
    async with pool.acquire() as conn:
        async with conn.transaction():
            for r in rows:
                player = r.get("player") or {}
                team = r.get("team") or {}
                player_name = (player.get("name") or "").strip()
                team_name = _canon((team.get("name") or "").strip())
                reason = (player.get("reason") or "").strip() or None
                status_label = (player.get("type") or "").strip() or None
                if not player_name or not team_name:
                    continue
                team_slug = _slugify(team_name)
                await conn.execute(
                    """
                    INSERT INTO player_injuries (
                        team_slug, player_name, reason, status_label,
                        league_code, season, last_seen_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    ON CONFLICT (team_slug, player_name, season, reason) DO UPDATE SET
                        status_label = EXCLUDED.status_label,
                        league_code  = EXCLUDED.league_code,
                        last_seen_at = NOW()
                    """,
                    team_slug, player_name, reason, status_label, league_code, season,
                )
                n += 1
    return n


def _season_year(season: str) -> int:
    """`2025-26` → 2025 (API-Football uses the starting year)."""
    return int(season.split("-")[0])


async def run(season: str, league_filter: str | None) -> None:
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("[injuries] missing API_FOOTBALL_KEY")
        return

    leagues = [get_league(league_filter)] if league_filter else LEAGUES
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        season_year = _season_year(season)
        total = 0
        for lg in leagues:
            rows = _fetch(api_key, lg.api_football_id, season_year)
            n = await _upsert(pool, rows, lg.code, season)
            print(f"[injuries] {lg.short}: {len(rows)} fetched · {n} upserted")
            total += n

        # Prune stale rows (not seen in 14 days) — players who recovered or
        # moved on. Keeps `get current injuries` queries honest without a
        # separate sweep job.
        pruned = await pool.execute(
            "DELETE FROM player_injuries WHERE last_seen_at < NOW() - INTERVAL '14 days'",
        )
        print(f"[injuries] total: {total} upserted · prune: {pruned}")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--season", default="2025-26")
    p.add_argument("--league", default=None, help="optional single-league filter")
    args = p.parse_args()
    asyncio.run(run(args.season, args.league))


if __name__ == "__main__":
    main()
