"""Pull per-bookmaker pre-match odds from API-Football for every match
in the next 72 hours, store one row per (match, book) in match_odds.

Replaces the-odds-api for the odds-comparison feature — we're on the
API-Football Ultra plan (75k/day), whose `/odds?fixture=X` endpoint
already returns per-book H2H prices without pushing our tiny The Odds
API monthly cap.

Usage:
    python scripts/ingest_bookmaker_odds.py [--hours 72]
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings


# Map API-Football bookmaker keys to short, friendly slugs for match_odds.source.
# Falls through to lowercased name when unmapped.
_BOOK_SLUG = {
    1: "10bet",
    2: "marathonbet",
    3: "williamhill",
    4: "pinnacle",
    5: "1xbet",
    6: "bwin",
    7: "betsson",
    8: "bet365",
    9: "betfair",
    10: "sbobet",
    11: "unibet",
    12: "betcris",
    13: "caesars",
    14: "betway",
    16: "bet9ja",
    17: "ladbrokes",
    18: "888sport",
    19: "paddypower",
    20: "betvictor",
    21: "coral",
    22: "betfred",
    23: "coolbet",
    24: "mostbet",
    25: "betclic",
}


def _fetch_odds(key: str, fixture_id: int) -> list[dict]:
    url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}"
    req = urllib.request.Request(url, headers={"x-apisports-key": key})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.loads(r.read())
            rem = r.headers.get("x-ratelimit-requests-remaining")
            if rem:
                try:
                    if int(rem) < 500:
                        print(f"[odds-af] quota low: {rem} remaining")
                except ValueError:
                    pass
    except Exception as e:
        print(f"[odds-af] {fixture_id}: {type(e).__name__}: {e}")
        return []
    return body.get("response", []) or []


def _extract_h2h(response: list[dict]) -> list[tuple[str, float, float, float]]:
    """Return (book_slug, home_odds, draw_odds, away_odds) per bookmaker."""
    out: list[tuple[str, float, float, float]] = []
    if not response:
        return out
    # API-Football wraps everything under response[0] (one fixture).
    entry = response[0]
    for bk in entry.get("bookmakers", []) or []:
        bk_id = bk.get("id")
        slug = _BOOK_SLUG.get(bk_id) if bk_id else None
        if not slug:
            slug = (bk.get("name") or "").lower().replace(" ", "-")
        if not slug:
            continue
        h = d = a = None
        for bet in bk.get("bets", []) or []:
            if (bet.get("name") or "").lower() != "match winner":
                continue
            for v in bet.get("values", []) or []:
                label = (v.get("value") or "").strip().lower()
                try:
                    odd = float(v.get("odd", 0))
                except (TypeError, ValueError):
                    odd = 0.0
                if odd <= 1.0:
                    continue
                if label == "home":
                    h = odd
                elif label == "away":
                    a = odd
                elif label == "draw":
                    d = odd
        if h and d and a:
            out.append((slug, h, d, a))
    return out


async def run(hours: int) -> None:
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        print("[odds-af] no API_FOOTBALL_KEY; skipping")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            fixtures = await conn.fetch(
                """
                SELECT id, api_football_fixture_id
                FROM matches
                WHERE status = 'scheduled'
                  AND api_football_fixture_id IS NOT NULL
                  AND kickoff_time BETWEEN NOW() AND NOW() + ($1 || ' hours')::INTERVAL
                ORDER BY kickoff_time ASC
                """,
                str(hours),
            )
        if not fixtures:
            print(f"[odds-af] no fixtures with api_football_fixture_id in next {hours}h")
            return

        print(f"[odds-af] pulling odds for {len(fixtures)} fixtures")
        total_rows = 0
        touched_matches = 0
        for f in fixtures:
            resp = _fetch_odds(key, int(f["api_football_fixture_id"]))
            books = _extract_h2h(resp)
            if not books:
                continue
            touched_matches += 1
            for slug, h, d, a in books:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO match_odds (match_id, source, odds_home, odds_draw, odds_away, captured_at)
                        VALUES ($1, $2, $3, $4, $5, NOW())
                        ON CONFLICT (match_id, source) DO UPDATE
                        SET odds_home = EXCLUDED.odds_home,
                            odds_draw = EXCLUDED.odds_draw,
                            odds_away = EXCLUDED.odds_away,
                            captured_at = EXCLUDED.captured_at
                        """,
                        f["id"], f"odds-api:{slug}", float(h), float(d), float(a),
                    )
                total_rows += 1
            # 0.15s throttle: 6.6 calls/sec is well under Ultra's 450/min cap
            # while leaving room for sibling ingest scripts.
            time.sleep(0.15)
        print(f"[odds-af] upserted {total_rows} book rows across {touched_matches}/{len(fixtures)} fixtures")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--hours", type=int, default=72)
    args = p.parse_args()
    asyncio.run(run(args.hours))


if __name__ == "__main__":
    main()
