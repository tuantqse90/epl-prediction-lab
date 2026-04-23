"""Finalise matches stuck in 'scheduled' whose kickoff is long past.

Problem:
    ingest_live_scores only sees currently-live fixtures from API-Football's
    live feed. If a match was never live-polled (quota exhausted that day,
    outage, wrong kickoff at ingest time), it sits at 'scheduled' forever
    even after it actually ended. The ops watchdog flags it; this script
    resolves it.

Strategy:
    For every 'scheduled' match with kickoff >2h ago and an af_id, pull
    `/fixtures?id=<af_id>` (1 quota/match) and upsert final state.

Env:
    API_FOOTBALL_KEY

Usage:
    python scripts/finalise_missed_matches.py [--max 20]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import urllib.request
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings


def _get(url: str, key: str) -> dict:
    req = urllib.request.Request(url, headers={"x-apisports-key": key})
    with urllib.request.urlopen(req, timeout=20) as resp:
        remaining = resp.headers.get("x-ratelimit-requests-remaining")
        if remaining:
            print(f"[finalise] quota remaining: {remaining}")
        return json.loads(resp.read())


def _fetch_fixture(key: str, fixture_id: int) -> dict | None:
    url = f"https://v3.football.api-sports.io/fixtures?id={fixture_id}"
    try:
        body = _get(url, key)
    except Exception as e:
        print(f"[finalise] fetch failed for {fixture_id}: {type(e).__name__}: {e}")
        return None
    response = body.get("response") or []
    return response[0] if response else None


def _map_status(short: str | None) -> str | None:
    """Translate API-Football status to our schema."""
    if not short:
        return None
    FT = {"FT", "AET", "PEN"}
    LIVE = {"1H", "HT", "2H", "ET", "P", "BT", "INT"}
    CANC = {"CANC", "ABD", "AWD", "WO"}
    POSTP = {"TBD", "PST", "SUSP"}
    if short in FT:
        return "final"
    if short in LIVE:
        return "live"
    if short in CANC:
        return "cancelled"
    if short in POSTP:
        return "scheduled"
    return None


async def run(max_matches: int) -> None:
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("[finalise] missing API_FOOTBALL_KEY")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, api_football_fixture_id
                FROM matches
                WHERE status = 'scheduled'
                  AND kickoff_time < NOW() - INTERVAL '2 hours'
                  AND api_football_fixture_id IS NOT NULL
                ORDER BY kickoff_time ASC
                LIMIT $1
                """,
                max_matches,
            )
        print(f"[finalise] {len(rows)} scheduled-past-kickoff matches to resolve")

        resolved = 0
        for r in rows:
            fixture = _fetch_fixture(api_key, int(r["api_football_fixture_id"]))
            if not fixture:
                continue
            fix = fixture.get("fixture") or {}
            status_short = (fix.get("status") or {}).get("short")
            elapsed = (fix.get("status") or {}).get("elapsed")
            goals = fixture.get("goals") or {}
            hg = goals.get("home")
            ag = goals.get("away")
            mapped = _map_status(status_short)
            if mapped is None or hg is None or ag is None:
                continue
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE matches
                    SET status = $1,
                        home_goals = $2,
                        away_goals = $3,
                        minute = $4,
                        live_updated_at = NOW()
                    WHERE id = $5
                    """,
                    mapped, int(hg), int(ag), elapsed, int(r["id"]),
                )
                resolved += 1
                print(f"[finalise] match {r['id']} → {mapped} {hg}-{ag}")
        print(f"[finalise] resolved {resolved}/{len(rows)}")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--max", type=int, default=20)
    args = p.parse_args()
    asyncio.run(run(args.max))


if __name__ == "__main__":
    main()
