"""Pull live pre-match H2H odds from The Odds API and upsert.

Averages decimal prices across UK+EU bookmakers for each fixture, then reuses
the same `upsert_odds` path as the historical football-data ingester. Stored
under source='the-odds-api:avg' so both historical and live rows coexist on
the same match when available (the LATEST one wins in the API response).

Env:
    THE_ODDS_API_KEY   — required

Usage:
    python scripts/ingest_live_odds.py [--regions uk,eu] [--season 2025-26]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import urllib.parse
import urllib.request
import json
from pathlib import Path

import asyncpg
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.ingest.odds import OddsRow, upsert_odds
from app.leagues import LEAGUES, get_league


# The Odds API returns full EPL team names; Understat uses the shorter form.
LIVE_NAME_MAP: dict[str, str] = {
    "Brighton and Hove Albion": "Brighton",
    "Leeds United": "Leeds",
    "Tottenham Hotspur": "Tottenham",
    "West Ham United": "West Ham",
    # others (Arsenal, Chelsea, Man City/United, etc.) line up directly
}


def _canon(name: str) -> str:
    return LIVE_NAME_MAP.get(name, name)


def _fetch(api_key: str, sport_key: str, regions: str) -> list[dict]:
    params = {
        "apiKey": api_key,
        "regions": regions,
        "markets": "h2h",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "epl-lab/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        remaining = resp.headers.get("x-requests-remaining")
        used = resp.headers.get("x-requests-used")
        if remaining:
            print(f"[quota] used={used} remaining={remaining}")
        return json.loads(resp.read())


def _aggregate(event: dict) -> dict | None:
    home, away = event["home_team"], event["away_team"]
    h_prices, d_prices, a_prices = [], [], []
    for bk in event.get("bookmakers", []):
        for mkt in bk.get("markets", []):
            if mkt.get("key") != "h2h":
                continue
            for out in mkt.get("outcomes", []):
                price = out.get("price")
                name = out.get("name")
                if not price or price <= 1.0:
                    continue
                if name == home:
                    h_prices.append(price)
                elif name == away:
                    a_prices.append(price)
                elif name == "Draw":
                    d_prices.append(price)
    if not (h_prices and d_prices and a_prices):
        return None
    return {
        "home": sum(h_prices) / len(h_prices),
        "draw": sum(d_prices) / len(d_prices),
        "away": sum(a_prices) / len(a_prices),
        "n_books": len(h_prices),
    }


def events_to_rows(events: list[dict], season: str) -> list[OddsRow]:
    rows: list[OddsRow] = []
    for e in events:
        agg = _aggregate(e)
        if agg is None:
            continue
        try:
            ts = pd.to_datetime(e["commence_time"])
        except Exception:
            continue
        rows.append(
            OddsRow(
                season=season,
                date=ts,
                home_name=_canon(e["home_team"]),
                away_name=_canon(e["away_team"]),
                odds_home=float(agg["home"]),
                odds_draw=float(agg["draw"]),
                odds_away=float(agg["away"]),
                source="the-odds-api:avg",
            )
        )
    return rows


async def run(season: str, regions: str, leagues: list) -> None:
    api_key = os.environ.get("THE_ODDS_API_KEY")
    if not api_key:
        print("[live-odds] missing THE_ODDS_API_KEY")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        total_events = 0
        total_upserted = 0
        for lg in leagues:
            try:
                events = _fetch(api_key, lg.the_odds_api_key, regions)
            except Exception as e:
                print(f"[live-odds] {lg.short}: {type(e).__name__}: {e}")
                continue
            rows = events_to_rows(events, season=season)
            n = await upsert_odds(pool, rows)
            print(f"[live-odds] {lg.short}: {len(events)} events · {len(rows)} parsed · {n} upserted")
            total_events += len(events)
            total_upserted += n
        print(f"[live-odds] total: {total_events} events / {total_upserted} upserted")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    from app.leagues import LEAGUES, get_league

    p = argparse.ArgumentParser()
    p.add_argument("--season", default="2025-26")
    p.add_argument("--regions", default="uk,eu")
    p.add_argument("--league", default=None,
                   help="optional single-league filter; default = all top-5")
    args = p.parse_args()
    leagues = [get_league(args.league)] if args.league else LEAGUES
    asyncio.run(run(args.season, args.regions, leagues))


if __name__ == "__main__":
    main()
