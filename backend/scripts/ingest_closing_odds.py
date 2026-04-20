"""Snapshot the-odds-api prices at T-5min before kickoff → closing_odds.

This is the reference row used by /api/stats/clv to measure whether the model
was picking winners the market slowly agreed with. Run every 5 minutes; will
only write the FIRST snapshot per (match_id, source) thanks to the table's
UNIQUE constraint.

Env:
    THE_ODDS_API_KEY — required

Usage:
    python scripts/ingest_closing_odds.py [--within-min 30]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.leagues import LEAGUES


def _fetch(api_key: str, sport_key: str, regions: str) -> list[dict]:
    params = {
        "apiKey": api_key,
        "regions": regions,
        "markets": "h2h",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "football-predict/clv"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        remaining = resp.headers.get("x-requests-remaining")
        used = resp.headers.get("x-requests-used")
        if remaining:
            print(f"[closing-odds][quota] used={used} remaining={remaining}")
        return json.loads(resp.read())


def _aggregate(event: dict) -> tuple[float, float, float] | None:
    home, away = event["home_team"], event["away_team"]
    h, d, a = [], [], []
    for bk in event.get("bookmakers", []):
        for mkt in bk.get("markets", []):
            if mkt.get("key") != "h2h":
                continue
            for out in mkt.get("outcomes", []):
                price = out.get("price")
                if not price or price <= 1.0:
                    continue
                if out.get("name") == home:
                    h.append(price)
                elif out.get("name") == away:
                    a.append(price)
                elif out.get("name") == "Draw":
                    d.append(price)
    if not (h and d and a):
        return None
    return sum(h) / len(h), sum(d) / len(d), sum(a) / len(a)


async def _find_match(conn, home_name: str, away_name: str, commence_iso: str) -> int | None:
    """Resolve a The-Odds-API fixture to matches.id by name + date."""
    from app.ingest.odds import _canon
    row = await conn.fetchrow(
        """
        SELECT m.id, m.kickoff_time
        FROM matches m
        JOIN teams ht ON ht.id = m.home_team_id
        JOIN teams at ON at.id = m.away_team_id
        WHERE ht.name = $1 AND at.name = $2
          AND DATE(m.kickoff_time) = DATE($3::timestamptz)
        LIMIT 1
        """,
        _canon(home_name), _canon(away_name), commence_iso,
    )
    return row["id"] if row else None


async def run(regions: str, within_min: int) -> int:
    api_key = os.environ.get("THE_ODDS_API_KEY")
    if not api_key:
        print("[closing-odds] missing THE_ODDS_API_KEY")
        return 0

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    written = 0
    try:
        async with pool.acquire() as conn:
            # Short-circuit: if no fixture is kicking off within the window,
            # skip every API call. Saves ~60 the-odds-api calls/hour during
            # empty windows — crucial on the 500/month free tier.
            imminent = await conn.fetchval(
                "SELECT COUNT(*) FROM matches "
                "WHERE kickoff_time BETWEEN NOW() AND NOW() + ($1 || ' minutes')::INTERVAL "
                "AND status != 'final'",
                str(within_min),
            )
            if not imminent:
                print(f"[closing-odds] no fixtures within {within_min}min — skipping API calls")
                return 0

            for lg in LEAGUES:
                if not lg.the_odds_api_key:
                    continue
                try:
                    events = _fetch(api_key, lg.the_odds_api_key, regions)
                except Exception as e:
                    print(f"[closing-odds] {lg.short}: {type(e).__name__}: {e}")
                    continue

                lg_written = 0
                for e in events:
                    # Only snapshot fixtures that are IMMINENT — this is the
                    # "closing" line, not a running line.
                    commence = e.get("commence_time")
                    if not commence:
                        continue
                    row = await conn.fetchrow(
                        "SELECT EXTRACT(EPOCH FROM ($1::timestamptz - NOW())) / 60 AS mins",
                        commence,
                    )
                    mins = float(row["mins"]) if row else 9999.0
                    if mins < 0 or mins > within_min:
                        continue

                    agg = _aggregate(e)
                    if agg is None:
                        continue
                    oh, od, oa = agg

                    match_id = await _find_match(conn, e["home_team"], e["away_team"], commence)
                    if match_id is None:
                        continue

                    n = await conn.execute(
                        """
                        INSERT INTO closing_odds (
                            match_id, source, odds_home, odds_draw, odds_away,
                            minutes_before_kickoff
                        )
                        VALUES ($1, 'the-odds-api:avg', $2, $3, $4, $5)
                        ON CONFLICT (match_id, source) DO NOTHING
                        """,
                        match_id, float(oh), float(od), float(oa), int(round(mins)),
                    )
                    # asyncpg execute() returns "INSERT 0 1" or "INSERT 0 0"
                    if n.endswith("1"):
                        lg_written += 1
                print(f"[closing-odds] {lg.short}: {len(events)} events · {lg_written} closing snapshots written")
                written += lg_written
        print(f"[closing-odds] total: {written} closing snapshots")
    finally:
        await pool.close()
    return written


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--regions", default="uk,eu")
    p.add_argument("--within-min", type=int, default=30,
                   help="only snapshot fixtures kicking off in this window (minutes)")
    args = p.parse_args()
    asyncio.run(run(args.regions, args.within_min))


if __name__ == "__main__":
    main()
