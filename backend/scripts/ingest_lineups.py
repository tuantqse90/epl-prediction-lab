"""Fetch starting XI from API-Football for upcoming matches.

Strategy:
  1. Find scheduled matches with kickoff in the next 3 hours.
  2. For any match missing `api_football_fixture_id`, batch-resolve via
     `/fixtures?date=YYYY-MM-DD&league=X` (one call per (date, league)).
  3. For each match with a fixture_id, call
     `/fixtures/lineups?fixture=<id>` and upsert into match_lineups.

Quota-friendly: typical matchday with 15 fixtures across 5 leagues burns
~15 quota for lineups + ~5 for fixture-id resolution = ~20/day total.

Env:
    API_FOOTBALL_KEY

Usage:
    python scripts/ingest_lineups.py [--window-minutes 180]
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

from scripts.ingest_live_scores import NAME_MAP  # noqa: E402


def _canon(name: str) -> str:
    return NAME_MAP.get(name, name)


def _get(url: str, key: str) -> dict:
    req = urllib.request.Request(url, headers={"x-apisports-key": key})
    with urllib.request.urlopen(req, timeout=15) as resp:
        remaining = resp.headers.get("x-ratelimit-requests-remaining")
        if remaining:
            print(f"[lineups] quota remaining: {remaining}")
        return json.loads(resp.read())


def _fetch_fixtures_for_day(key: str, league_id: int, season_year: int, iso_date: str) -> list[dict]:
    url = (
        f"https://v3.football.api-sports.io/fixtures"
        f"?league={league_id}&season={season_year}&date={iso_date}"
    )
    try:
        body = _get(url, key)
    except Exception as e:
        print(f"[lineups] fixtures lookup failed: {type(e).__name__}: {e}")
        return []
    return body.get("response", []) or []


def _fetch_lineups(key: str, fixture_id: int) -> list[dict]:
    url = f"https://v3.football.api-sports.io/fixtures/lineups?fixture={fixture_id}"
    try:
        body = _get(url, key)
    except Exception as e:
        print(f"[lineups] lineups fetch failed ({fixture_id}): {type(e).__name__}: {e}")
        return []
    return body.get("response", []) or []


async def _resolve_fixture_ids(pool: asyncpg.Pool, key: str, window_minutes: int) -> int:
    """For matches in the next N minutes without a fixture_id, resolve it."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.id, m.kickoff_time, m.league_code, m.season,
                   ht.name AS home_name, at.name AS away_name
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.status = 'scheduled'
              AND m.api_football_fixture_id IS NULL
              AND m.kickoff_time BETWEEN NOW() AND NOW() + ($1 || ' minutes')::INTERVAL
            ORDER BY m.kickoff_time ASC
            """,
            str(window_minutes),
        )
    if not rows:
        return 0

    # Group by (league_code, kickoff_date) so one API call covers every
    # match in that bucket.
    buckets: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        iso_date = r["kickoff_time"].date().isoformat()
        buckets.setdefault((r["league_code"], iso_date), []).append(dict(r))

    resolved = 0
    for (league_code, iso_date), bucket in buckets.items():
        lg = BY_CODE.get(league_code)
        if not lg:
            continue
        season_year = int(bucket[0]["season"].split("-")[0])
        fixtures = _fetch_fixtures_for_day(key, lg.api_football_id, season_year, iso_date)
        if not fixtures:
            continue
        by_pair: dict[tuple[str, str], int] = {}
        for f in fixtures:
            teams = f.get("teams") or {}
            h = _canon((teams.get("home") or {}).get("name", "").strip())
            a = _canon((teams.get("away") or {}).get("name", "").strip())
            fid = (f.get("fixture") or {}).get("id")
            if h and a and fid:
                by_pair[(h, a)] = int(fid)

        async with pool.acquire() as conn:
            for r in bucket:
                fid = by_pair.get((r["home_name"], r["away_name"]))
                if fid is None:
                    continue
                await conn.execute(
                    "UPDATE matches SET api_football_fixture_id = $1 WHERE id = $2",
                    fid, r["id"],
                )
                resolved += 1
    return resolved


async def _ingest_lineups(pool: asyncpg.Pool, key: str, window_minutes: int) -> int:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.id, m.api_football_fixture_id,
                   ht.slug AS home_slug, ht.name AS home_name,
                   at.slug AS away_slug, at.name AS away_name
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.status = 'scheduled'
              AND m.api_football_fixture_id IS NOT NULL
              AND m.kickoff_time BETWEEN NOW() AND NOW() + ($1 || ' minutes')::INTERVAL
            ORDER BY m.kickoff_time ASC
            """,
            str(window_minutes),
        )

    total_rows = 0
    for r in rows:
        lineups = _fetch_lineups(key, int(r["api_football_fixture_id"]))
        if not lineups:
            continue
        async with pool.acquire() as conn:
            async with conn.transaction():
                for side in lineups:
                    team_name = _canon((side.get("team") or {}).get("name", "").strip())
                    # Only map to the two teams we already know about. If
                    # the API returns something we can't resolve, skip it.
                    if team_name == r["home_name"]:
                        team_slug = r["home_slug"]
                    elif team_name == r["away_name"]:
                        team_slug = r["away_slug"]
                    else:
                        continue
                    formation = (side.get("formation") or "").strip() or None
                    start_xi = side.get("startXI") or []
                    subs = side.get("substitutes") or []
                    for entry, is_start in [(x, True) for x in start_xi] + [(x, False) for x in subs]:
                        p = (entry.get("player") or {})
                        player_name = (p.get("name") or "").strip()
                        if not player_name:
                            continue
                        await conn.execute(
                            """
                            INSERT INTO match_lineups (
                                match_id, team_slug, player_name, player_number,
                                position, grid, is_starting, formation
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            ON CONFLICT (match_id, team_slug, player_name) DO UPDATE SET
                                player_number = EXCLUDED.player_number,
                                position = EXCLUDED.position,
                                grid = EXCLUDED.grid,
                                is_starting = EXCLUDED.is_starting,
                                formation = EXCLUDED.formation,
                                updated_at = NOW()
                            """,
                            int(r["id"]), team_slug, player_name,
                            int(p["number"]) if p.get("number") is not None else None,
                            (p.get("pos") or "").strip() or None,
                            (p.get("grid") or "").strip() or None,
                            is_start,
                            formation,
                        )
                        total_rows += 1
    return total_rows


async def run(window_minutes: int) -> None:
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("[lineups] missing API_FOOTBALL_KEY")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        resolved = await _resolve_fixture_ids(pool, api_key, window_minutes)
        print(f"[lineups] resolved {resolved} fixture ids")
        n = await _ingest_lineups(pool, api_key, window_minutes)
        print(f"[lineups] upserted {n} lineup rows")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument(
        "--window-minutes", type=int, default=180,
        help="Look N minutes ahead for fixtures (lineups arrive ~60min before KO)",
    )
    args = p.parse_args()
    asyncio.run(run(args.window_minutes))


if __name__ == "__main__":
    main()
