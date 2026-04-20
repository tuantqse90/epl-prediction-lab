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


def _fetch(api_key: str, sport_key: str, regions: str, markets: str = "h2h") -> list[dict]:
    params = {
        "apiKey": api_key,
        "regions": regions,
        "markets": markets,
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


def _book_rows(event: dict) -> list[tuple[str, float, float, float]]:
    """One (book_key, home, draw, away) tuple per bookmaker in the event."""
    home, away = event["home_team"], event["away_team"]
    out: list[tuple[str, float, float, float]] = []
    for bk in event.get("bookmakers", []):
        key = bk.get("key") or bk.get("title") or ""
        if not key:
            continue
        h = d = a = None
        for mkt in bk.get("markets", []):
            if mkt.get("key") != "h2h":
                continue
            for o in mkt.get("outcomes", []):
                price = o.get("price")
                name = o.get("name")
                if not price or price <= 1.0:
                    continue
                if name == home:
                    h = price
                elif name == away:
                    a = price
                elif name == "Draw":
                    d = price
        if h and d and a:
            out.append((key, float(h), float(d), float(a)))
    return out


from dataclasses import dataclass


@dataclass(frozen=True)
class MarketOddsRow:
    """One outcome of one market on one match from one source. Matches the
    match_odds_markets table row shape."""
    season: str
    date: pd.Timestamp
    home_name: str
    away_name: str
    source: str                # 'the-odds-api:avg' or 'odds-api:<book_key>'
    market_code: str           # 'OU' | 'BTTS'
    line: float | None         # 2.5 for OU, None for BTTS
    outcome_code: str          # 'OVER'/'UNDER', 'YES'/'NO'
    odds: float


def _parse_totals_rows(event: dict) -> list[tuple[str, float, str, float]]:
    """Extract per-book totals (O/U) rows from an event. One row per
    (book_key, line, outcome). Aggregates across all lines a book quotes."""
    out: list[tuple[str, float, str, float]] = []
    for bk in event.get("bookmakers", []):
        book_key = bk.get("key") or bk.get("title") or ""
        if not book_key:
            continue
        for mkt in bk.get("markets", []):
            if mkt.get("key") != "totals":
                continue
            for o in mkt.get("outcomes", []):
                price = o.get("price")
                name = (o.get("name") or "").upper()
                point = o.get("point")
                if not price or price <= 1.0 or point is None:
                    continue
                if name not in ("OVER", "UNDER"):
                    continue
                out.append((book_key, float(point), name, float(price)))
    return out


def _parse_spreads_rows(event: dict) -> list[tuple[str, float, str, float]]:
    """Extract per-book spreads (Asian handicap) rows normalised to the
    home-side perspective.

    the-odds-api returns spreads as one outcome per TEAM with a `point`
    field. Home at point=-0.5 and away at point=+0.5 is the same handicap
    quoted from two sides; we store both so lookups on either side hit."""
    home = event.get("home_team", "")
    away = event.get("away_team", "")
    out: list[tuple[str, float, str, float]] = []
    for bk in event.get("bookmakers", []):
        book_key = bk.get("key") or bk.get("title") or ""
        if not book_key:
            continue
        for mkt in bk.get("markets", []):
            if mkt.get("key") != "spreads":
                continue
            for o in mkt.get("outcomes", []):
                price = o.get("price")
                point = o.get("point")
                name = o.get("name") or ""
                if not price or price <= 1.0 or point is None:
                    continue
                if name == home:
                    out.append((book_key, float(point), "HOME", float(price)))
                elif name == away:
                    # Convert to home-perspective line: home +N = away -N
                    out.append((book_key, -float(point), "AWAY", float(price)))
    return out


def _aggregate_totals(event: dict) -> dict[float, dict[str, float]]:
    """Per-line average over/under prices across all books."""
    buckets: dict[float, dict[str, list[float]]] = {}
    for _, line, side, price in _parse_totals_rows(event):
        buckets.setdefault(line, {"OVER": [], "UNDER": []}).setdefault(side, []).append(price)
    return {
        line: {side: sum(ps) / len(ps) for side, ps in sides.items() if ps}
        for line, sides in buckets.items()
    }


def _aggregate_spreads(event: dict) -> dict[tuple[float, str], float]:
    """Per (line, side) average price across books."""
    buckets: dict[tuple[float, str], list[float]] = {}
    for _, line, side, price in _parse_spreads_rows(event):
        buckets.setdefault((line, side), []).append(price)
    return {k: sum(ps) / len(ps) for k, ps in buckets.items() if ps}


def events_to_market_rows(events: list[dict], season: str) -> list[MarketOddsRow]:
    """Flatten events into per-outcome match_odds_markets rows (O/U + BTTS).

    Mirrors the dual per-book + aggregate pattern used for 1X2: we write a
    pooled `source='the-odds-api:avg'` row AND one `source='odds-api:<book>'`
    row per bookmaker per outcome, so the edge endpoint can pick the best
    price across books while still having an avg reference for devigging."""
    rows: list[MarketOddsRow] = []
    for e in events:
        try:
            ts = pd.to_datetime(e["commence_time"])
        except Exception:
            continue
        home_c = _canon(e["home_team"])
        away_c = _canon(e["away_team"])

        # --- Totals (Over/Under) ---
        for book_key, line, side, price in _parse_totals_rows(e):
            rows.append(MarketOddsRow(
                season=season, date=ts,
                home_name=home_c, away_name=away_c,
                source=f"odds-api:{book_key}",
                market_code="OU", line=line, outcome_code=side, odds=price,
            ))
        for line, sides in _aggregate_totals(e).items():
            for side, price in sides.items():
                rows.append(MarketOddsRow(
                    season=season, date=ts,
                    home_name=home_c, away_name=away_c,
                    source="the-odds-api:avg",
                    market_code="OU", line=line, outcome_code=side, odds=price,
                ))

        # --- Spreads (Asian handicap, normalised to home-perspective line) ---
        for book_key, line, side, price in _parse_spreads_rows(e):
            rows.append(MarketOddsRow(
                season=season, date=ts,
                home_name=home_c, away_name=away_c,
                source=f"odds-api:{book_key}",
                market_code="AH", line=line, outcome_code=side, odds=price,
            ))
        for (line, side), price in _aggregate_spreads(e).items():
            rows.append(MarketOddsRow(
                season=season, date=ts,
                home_name=home_c, away_name=away_c,
                source="the-odds-api:avg",
                market_code="AH", line=line, outcome_code=side, odds=price,
            ))
    return rows


async def upsert_market_odds(pool, rows):
    """UPSERT into match_odds_markets keyed by
    (match_id, source, market_code, line, outcome_code)."""
    rows = list(rows)
    n = 0
    async with pool.acquire() as conn:
        async with conn.transaction():
            for r in rows:
                match_id = await conn.fetchval(
                    """
                    SELECT m.id FROM matches m
                    JOIN teams ht ON ht.id = m.home_team_id
                    JOIN teams at ON at.id = m.away_team_id
                    WHERE ht.name = $1 AND at.name = $2
                      AND DATE(m.kickoff_time) = $3
                    """,
                    r.home_name, r.away_name, r.date.date(),
                )
                if match_id is None:
                    continue
                await conn.execute(
                    """
                    INSERT INTO match_odds_markets (
                        match_id, source, market_code, line, outcome_code, odds
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (match_id, source, market_code, line, outcome_code)
                    DO UPDATE SET odds = EXCLUDED.odds, captured_at = NOW()
                    """,
                    match_id, r.source, r.market_code, r.line, r.outcome_code, r.odds,
                )
                n += 1
    return n


def events_to_rows(events: list[dict], season: str) -> list[OddsRow]:
    """Emit both the per-bookmaker rows (source='odds-api:<book_key>') and
    the pooled-average row (source='the-odds-api:avg', legacy) so the old
    aggregate-only code path keeps working while the comparison panel can
    query each book individually."""
    rows: list[OddsRow] = []
    for e in events:
        try:
            ts = pd.to_datetime(e["commence_time"])
        except Exception:
            continue
        home_c = _canon(e["home_team"])
        away_c = _canon(e["away_team"])

        # Per-bookmaker rows.
        for book_key, h, d, a in _book_rows(e):
            rows.append(OddsRow(
                season=season, date=ts,
                home_name=home_c, away_name=away_c,
                odds_home=h, odds_draw=d, odds_away=a,
                source=f"odds-api:{book_key}",
            ))

        # Legacy pooled-average row.
        agg = _aggregate(e)
        if agg is not None:
            rows.append(OddsRow(
                season=season, date=ts,
                home_name=home_c, away_name=away_c,
                odds_home=float(agg["home"]),
                odds_draw=float(agg["draw"]),
                odds_away=float(agg["away"]),
                source="the-odds-api:avg",
            ))
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
        total_market_rows = 0
        for lg in leagues:
            # Single combined fetch — the-odds-api charges 1 credit per request
            # regardless of how many markets are bundled, so grabbing 1X2 +
            # totals + BTTS in one call is free compared to three.
            try:
                # BTTS is gated above free tier on the-odds-api; spreads
                # (Asian handicap) is supported and gives us real AH edge.
                events = _fetch(api_key, lg.the_odds_api_key, regions, markets="h2h,totals,spreads")
            except Exception as e:
                print(f"[live-odds] {lg.short}: {type(e).__name__}: {e}")
                continue

            rows = events_to_rows(events, season=season)
            n = await upsert_odds(pool, rows)
            mkt_rows = events_to_market_rows(events, season=season)
            m = await upsert_market_odds(pool, mkt_rows)
            print(f"[live-odds] {lg.short}: {len(events)} events · 1X2 {n} upserted · markets {m} upserted")
            total_events += len(events)
            total_upserted += n
            total_market_rows += m
        print(f"[live-odds] total: {total_events} events / 1X2 {total_upserted} / markets {total_market_rows}")
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
