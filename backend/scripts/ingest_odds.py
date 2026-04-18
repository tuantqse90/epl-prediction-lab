"""Download football-data.co.uk odds CSV for a league+season and upsert.

Usage:
    python scripts/ingest_odds.py --season 2025-26 --league laliga
    python scripts/ingest_odds.py --seasons 2022-23,2023-24,2024-25,2025-26 --league epl
"""

from __future__ import annotations

import argparse
import asyncio
import io
import logging
import sys
import urllib.request
from pathlib import Path

import asyncpg
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.ingest.odds import odds_csv_to_rows, upsert_odds
from app.leagues import DEFAULT_LEAGUE, get_league


def _fd_url(fd_code: str, season: str) -> str:
    start, end = season.split("-")
    return f"https://www.football-data.co.uk/mmz4281/{start[-2:]}{end[-2:]}/{fd_code}.csv"


def _fetch(fd_code: str, season: str) -> pd.DataFrame:
    url = _fd_url(fd_code, season)
    print(f"> fetching {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "epl-lab/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    return pd.read_csv(io.BytesIO(raw), encoding_errors="replace")


async def run(league_code: str, seasons: list[str]) -> None:
    settings = get_settings()
    league = get_league(league_code)
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        for season in seasons:
            df = _fetch(league.football_data_code, season)
            rows = odds_csv_to_rows(df, season=season)
            n = await upsert_odds(pool, rows)
            print(f"> {league.short} {season}: {len(rows)} rows parsed, {n} matched + upserted")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--season", default=None)
    p.add_argument("--seasons", default=None, help="comma-separated")
    p.add_argument("--league", default=DEFAULT_LEAGUE)
    args = p.parse_args()

    if args.seasons:
        seasons = [s.strip() for s in args.seasons.split(",") if s.strip()]
    elif args.season:
        seasons = [args.season]
    else:
        seasons = ["2025-26"]

    lc = get_league(args.league).code
    asyncio.run(run(lc, seasons))


if __name__ == "__main__":
    main()
