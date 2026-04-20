"""Backfill matches.referee from API-Football /fixtures for historical seasons.

The live-scores and lineups ingest scripts only populate referee on fixtures
that roll through their cron window. Anything older than those jobs' first
run has `referee IS NULL`. This script walks every (league, season) in our
matches table and fills in the referee where API-Football has it.

Costs: one /fixtures page per (league, season). Pagination is auto-followed.
Expected total: ~30 API calls for 5 leagues × 6 seasons. Trivial against
API-Football Ultra's 75k/day quota.

Usage:
    python scripts/backfill_referees.py [--season 2024-25]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import urllib.request
from pathlib import Path

import asyncpg
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.leagues import LEAGUES


def _fetch(key: str, path: str) -> dict:
    url = f"https://v3.football.api-sports.io{path}"
    req = urllib.request.Request(url, headers={"x-apisports-key": key})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def _iter_fixtures(key: str, league_id: int, season_year: int):
    # API-Football /fixtures returns the entire season in a single response
    # (no pagination in practice — `paging.total` is always 1). Passing
    # `&page=1` explicitly triggers a 0-result response, so we deliberately
    # omit it on the first call.
    body = _fetch(key, f"/fixtures?league={league_id}&season={season_year}")
    for ev in body.get("response", []) or []:
        yield ev


async def run(seasons: list[str]) -> None:
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        print("[backfill-ref] missing API_FOOTBALL_KEY")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        total_seen = 0
        total_updated = 0
        async with pool.acquire() as conn:
            for lg in LEAGUES:
                for season in seasons:
                    season_year = int(season.split("-")[0])
                    try:
                        fixtures = list(_iter_fixtures(key, lg.api_football_id, season_year))
                    except Exception as e:
                        print(f"[backfill-ref] {lg.short} {season}: {type(e).__name__}: {e}")
                        continue

                    updated = 0
                    for fx_ev in fixtures:
                        fx = fx_ev.get("fixture") or {}
                        kickoff = fx.get("date")
                        referee = (fx.get("referee") or "").strip() or None
                        if not kickoff or not referee:
                            continue
                        # Match on league_code + kickoff timestamp (same join
                        # approach ingest_apifootball_odds uses — deterministic
                        # within a league).
                        try:
                            ts = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
                        except ValueError:
                            continue
                        res = await conn.execute(
                            """
                            UPDATE matches
                            SET referee = $1
                            WHERE league_code = $2
                              AND kickoff_time = $3
                              AND (referee IS NULL OR referee = '')
                            """,
                            referee, lg.code, ts,
                        )
                        # asyncpg returns "UPDATE N" — parse to count
                        if res.endswith("1"):
                            updated += 1
                    total_seen += len(fixtures)
                    total_updated += updated
                    print(f"[backfill-ref] {lg.short} {season}: {len(fixtures)} fixtures, {updated} referees filled")
        print(f"[backfill-ref] total: {total_seen} fixtures seen, {total_updated} referees filled")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--season", default=None,
                   help="single season (e.g. 2024-25); default = every season in DB")
    args = p.parse_args()
    # Figure out which seasons to backfill.
    # Our team database has 2019-20 → 2025-26 per PROGRESS.md notes.
    default_seasons = [f"{y}-{str(y+1)[-2:]}" for y in range(2019, 2026)]
    seasons = [args.season] if args.season else default_seasons
    asyncio.run(run(seasons))


if __name__ == "__main__":
    main()
