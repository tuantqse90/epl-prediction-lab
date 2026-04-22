"""Backfill api_football_fixture_id + authoritative kickoff_time.

Problem this exists to solve:
    A scheduled match with a wrong kickoff_time or missing
    api_football_fixture_id is invisible to ingest_live_scores — the live
    poll uses a NOW()±window filter keyed off kickoff_time, and stale dates
    push the row outside the window so it never gets updated. Observed on
    Burnley vs Man City (id=339) where DB held 2026-04-26 while the real
    kickoff was 2026-04-22 19:00 UTC.

What this does:
    For every scheduled match in the next N days across all 5 tracked
    leagues, fetch the canonical fixture list from API-Football and
    UPDATE both api_football_fixture_id AND kickoff_time so the live
    pipeline can find it.

Env:
    API_FOOTBALL_KEY

Usage:
    python scripts/backfill_fixture_ids.py [--days 30]
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
from app.leagues import BY_CODE

from scripts.ingest_live_scores import NAME_MAP


def _canon(name: str) -> str:
    return NAME_MAP.get(name, name)


def _get(url: str, key: str) -> dict:
    req = urllib.request.Request(url, headers={"x-apisports-key": key})
    with urllib.request.urlopen(req, timeout=20) as resp:
        remaining = resp.headers.get("x-ratelimit-requests-remaining")
        if remaining:
            print(f"[backfill-fixtures] quota remaining: {remaining}")
        return json.loads(resp.read())


def _fetch_fixtures_for_league_season(key: str, league_id: int, season_year: int) -> list[dict]:
    url = (
        f"https://v3.football.api-sports.io/fixtures"
        f"?league={league_id}&season={season_year}"
    )
    try:
        body = _get(url, key)
    except Exception as e:
        print(f"[backfill-fixtures] lookup failed ({league_id}/{season_year}): {type(e).__name__}: {e}")
        return []
    return body.get("response", []) or []


async def _backfill(pool: asyncpg.Pool, key: str, days: int) -> tuple[int, int]:
    """Returns (fixture_ids_set, kickoffs_corrected)."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.id, m.kickoff_time, m.league_code, m.season,
                   m.api_football_fixture_id,
                   ht.name AS home_name, at.name AS away_name
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.status = 'scheduled'
              AND m.kickoff_time BETWEEN NOW() - INTERVAL '2 days'
                                     AND NOW() + ($1 || ' days')::INTERVAL
            ORDER BY m.kickoff_time ASC
            """,
            str(days),
        )
    if not rows:
        return (0, 0)

    # One /fixtures call per (league_code, season) covers every match in that
    # bucket — ~5 API calls total.
    buckets: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        buckets.setdefault((r["league_code"], r["season"]), []).append(dict(r))

    ids_set = 0
    kickoffs_corrected = 0

    for (league_code, season), bucket in buckets.items():
        lg = BY_CODE.get(league_code)
        if not lg:
            continue
        season_year = int(season.split("-")[0])
        fixtures = _fetch_fixtures_for_league_season(key, lg.api_football_id, season_year)
        if not fixtures:
            continue

        by_pair: dict[tuple[str, str], tuple[int, str, str | None]] = {}
        for f in fixtures:
            teams = f.get("teams") or {}
            h = _canon((teams.get("home") or {}).get("name", "").strip())
            a = _canon((teams.get("away") or {}).get("name", "").strip())
            fix = f.get("fixture") or {}
            fid = fix.get("id")
            iso = (fix.get("date") or "").strip()
            ref = (fix.get("referee") or "").strip() or None
            if h and a and fid and iso:
                by_pair[(h, a)] = (int(fid), iso, ref)

        async with pool.acquire() as conn:
            for r in bucket:
                info = by_pair.get((r["home_name"], r["away_name"]))
                if info is None:
                    continue
                fid, iso, ref = info
                # Always normalise api_football_fixture_id; correct kickoff
                # only when it drifted by >1 minute — protects against tz
                # round-tripping noise but catches the Man City case.
                result = await conn.execute(
                    """
                    UPDATE matches
                    SET api_football_fixture_id = $1,
                        kickoff_time = $2::timestamptz,
                        referee = COALESCE($3, referee)
                    WHERE id = $4
                      AND (
                        api_football_fixture_id IS DISTINCT FROM $1
                        OR ABS(EXTRACT(EPOCH FROM (kickoff_time - $2::timestamptz))) > 60
                        OR ($3 IS NOT NULL AND referee IS DISTINCT FROM $3)
                      )
                    """,
                    fid, iso, ref, r["id"],
                )
                if result.endswith(" 1"):
                    # row actually changed
                    if r["api_football_fixture_id"] != fid:
                        ids_set += 1
                    # Can't cheaply tell if the kickoff correction applied
                    # without a second query; approximate by flagging when
                    # the incoming ISO differs from what we had.
                    existing_iso = r["kickoff_time"].isoformat()
                    if existing_iso[:16] != iso[:16]:
                        kickoffs_corrected += 1

    return (ids_set, kickoffs_corrected)


async def run(days: int) -> None:
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("[backfill-fixtures] missing API_FOOTBALL_KEY")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        ids_set, kickoffs_corrected = await _backfill(pool, api_key, days)
        print(f"[backfill-fixtures] set {ids_set} fixture ids, corrected {kickoffs_corrected} kickoff times")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=30)
    args = p.parse_args()
    asyncio.run(run(args.days))


if __name__ == "__main__":
    main()
