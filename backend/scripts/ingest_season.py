"""Scrape one EPL season from Understat and upsert into Postgres.

Usage:
    DATABASE_URL=postgresql://... python scripts/ingest_season.py --season 2024-25
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import asyncpg
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.ingest.schedule import schedule_to_rows
from app.ingest.upsert import upsert_all
from app.leagues import DEFAULT_LEAGUE, get_league


def _load_schedule(league_code: str, season: str) -> pd.DataFrame:
    import soccerdata as sd

    us = sd.Understat(leagues=[league_code], seasons=[season])
    df = us.read_schedule().reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    return df


async def run(league_code: str, season: str) -> None:
    settings = get_settings()
    df = _load_schedule(league_code, season)
    teams, matches = schedule_to_rows(df, season=season)
    for m in matches:
        object.__setattr__(m, "league_code", league_code)

    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=4)
    try:
        n_teams, n_matches = await upsert_all(pool, teams, matches, league_code=league_code)
    finally:
        await pool.close()

    print(f"> ingested {league_code} / {season} :: {n_teams} teams, {n_matches} matches")


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--season", default="2025-26")
    p.add_argument("--league", default=DEFAULT_LEAGUE,
                   help="soccerdata league code or slug (e.g. ESP-La Liga or laliga)")
    args = p.parse_args()
    league_code = get_league(args.league).code
    asyncio.run(run(league_code, args.season))


if __name__ == "__main__":
    main()
