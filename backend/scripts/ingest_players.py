"""Scrape Understat player-season stats for a given EPL season and upsert."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.ingest.players import player_stats_to_rows, upsert_player_stats
from app.leagues import DEFAULT_LEAGUE, get_league


def _load(league_code: str, season: str):
    import soccerdata as sd

    us = sd.Understat(leagues=[league_code], seasons=[season])
    return us.read_player_season_stats()


async def run(league_code: str, season: str) -> None:
    settings = get_settings()
    df = _load(league_code, season)
    rows = player_stats_to_rows(df, season=season)
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=4)
    try:
        n = await upsert_player_stats(pool, season, rows)
    finally:
        await pool.close()
    print(f"> ingested {n} player-season rows for {league_code} / {season}")


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--season", default="2025-26")
    p.add_argument("--league", default=DEFAULT_LEAGUE)
    args = p.parse_args()
    lc = get_league(args.league).code
    asyncio.run(run(lc, args.season))


if __name__ == "__main__":
    main()
