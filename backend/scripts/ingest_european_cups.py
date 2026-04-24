"""UCL + UEL fixture + odds ingest via API-Football Ultra.

Treats each fixture as `competition_type='europe'` so the Block 21.6
prior (`competition_prior.prior_for('europe')`) applies at predict time.

Team names from API-Football sometimes differ from our league-ingest
canonical. We upsert by `(external_id = f"af:{fixture_id}")` so later
reconciliation doesn't depend on name matching.

Env:
    API_FOOTBALL_KEY

Usage:
    python scripts/ingest_european_cups.py --season 2025 [--league UCL|UEL|ALL]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings


UCL = {"code": "UEFA-Champions League", "slug": "ucl", "api_id": 2}
UEL = {"code": "UEFA-Europa League",    "slug": "uel", "api_id": 3}


def _get(url: str, key: str) -> dict:
    req = urllib.request.Request(url, headers={"x-apisports-key": key})
    with urllib.request.urlopen(req, timeout=30) as resp:
        rem = resp.headers.get("x-ratelimit-requests-remaining")
        if rem:
            print(f"[europe] quota remaining: {rem}")
        return json.loads(resp.read())


def _fetch_season_fixtures(key: str, league_id: int, season_year: int) -> list[dict]:
    url = (
        f"https://v3.football.api-sports.io/fixtures"
        f"?league={league_id}&season={season_year}"
    )
    body = _get(url, key)
    return body.get("response", []) or []


def _fetch_odds(key: str, league_id: int, season_year: int) -> list[dict]:
    """Pre-match 1X2 odds for the whole season (paginated)."""
    out: list[dict] = []
    page = 1
    while True:
        url = (
            f"https://v3.football.api-sports.io/odds"
            f"?league={league_id}&season={season_year}&bet=1&page={page}"
        )
        try:
            body = _get(url, key)
        except Exception as e:
            print(f"[europe-odds] fetch failed p{page}: {type(e).__name__}: {e}")
            break
        chunk = body.get("response", []) or []
        out.extend(chunk)
        paging = body.get("paging") or {}
        if page >= int(paging.get("total", 1)):
            break
        page += 1
    return out


async def _upsert_team(conn, name: str) -> int | None:
    if not name:
        return None
    # Reuse existing team if the name matches one we track. Otherwise
    # insert with an auto-generated slug so we don't lose the fixture.
    row = await conn.fetchrow("SELECT id FROM teams WHERE name = $1", name)
    if row:
        return int(row["id"])
    slug = (
        name.lower()
        .replace(" ", "-")
        .replace(".", "")
        .replace("'", "")
    )
    row = await conn.fetchrow("SELECT id FROM teams WHERE slug = $1", slug)
    if row:
        return int(row["id"])
    short = name[:3].upper()
    new_id = await conn.fetchval(
        """
        INSERT INTO teams (slug, name, short_name)
        VALUES ($1, $2, $3) RETURNING id
        """,
        slug, name, short,
    )
    return int(new_id)


async def _upsert_fixture(conn, lg: dict, season: str, season_year: int, fx: dict) -> int | None:
    fixture = fx.get("fixture") or {}
    teams = fx.get("teams") or {}
    goals = fx.get("goals") or {}
    fid = fixture.get("id")
    if not fid:
        return None
    home_name = (teams.get("home") or {}).get("name") or ""
    away_name = (teams.get("away") or {}).get("name") or ""
    home_id = await _upsert_team(conn, home_name)
    away_id = await _upsert_team(conn, away_name)
    if not (home_id and away_id):
        return None
    kickoff_iso = (fixture.get("date") or "").strip()
    try:
        kickoff = datetime.fromisoformat(kickoff_iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    status_short = (fixture.get("status") or {}).get("short") or ""
    status = (
        "final" if status_short in ("FT", "AET", "PEN")
        else "live" if status_short in ("1H", "HT", "2H", "ET", "P", "INT")
        else "scheduled"
    )
    hg = goals.get("home")
    ag = goals.get("away")

    match_id = await conn.fetchval(
        """
        INSERT INTO matches (
            external_id, season, kickoff_time,
            home_team_id, away_team_id, status,
            home_goals, away_goals,
            league_code, api_football_fixture_id, competition_type
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'europe'
        )
        ON CONFLICT (external_id) DO UPDATE SET
            kickoff_time = EXCLUDED.kickoff_time,
            status = EXCLUDED.status,
            home_goals = EXCLUDED.home_goals,
            away_goals = EXCLUDED.away_goals,
            api_football_fixture_id = EXCLUDED.api_football_fixture_id,
            competition_type = 'europe'
        RETURNING id
        """,
        f"af:{fid}", season, kickoff,
        home_id, away_id, status,
        hg if hg is not None else None,
        ag if ag is not None else None,
        lg["code"], int(fid),
    )
    return int(match_id) if match_id else None


async def _upsert_odds_for_match(conn, match_id: int, odds_rows: list[dict]) -> None:
    # API-Football odds schema: bookmaker → bet(id=1 1X2) → values[{value: "Home|Draw|Away", odd: "2.10"}]
    for b in odds_rows:
        name = b.get("name") or "?"
        source = f"af:{name}"
        for bet in b.get("bets") or []:
            if bet.get("id") != 1 and (bet.get("name") or "").lower() != "match winner":
                continue
            vals = {v.get("value"): v.get("odd") for v in (bet.get("values") or [])}
            try:
                oh = float(vals.get("Home") or 0)
                od = float(vals.get("Draw") or 0)
                oa = float(vals.get("Away") or 0)
            except (TypeError, ValueError):
                continue
            if oh <= 1 or od <= 1 or oa <= 1:
                continue
            await conn.execute(
                """
                INSERT INTO match_odds (match_id, source, odds_home, odds_draw, odds_away)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (match_id, source) DO UPDATE SET
                    odds_home = EXCLUDED.odds_home,
                    odds_draw = EXCLUDED.odds_draw,
                    odds_away = EXCLUDED.odds_away,
                    captured_at = NOW()
                """,
                match_id, source, oh, od, oa,
            )


async def _run_league(pool, key: str, lg: dict, season_year: int) -> None:
    season_str = f"{season_year}-{str(season_year + 1)[-2:]}"
    print(f"[europe] {lg['code']} season {season_str}")
    fixtures = _fetch_season_fixtures(key, lg["api_id"], season_year)
    print(f"[europe]   {len(fixtures)} fixtures returned")

    ids: dict[int, int] = {}    # af_fixture_id → match_id
    async with pool.acquire() as conn:
        for fx in fixtures:
            fid = (fx.get("fixture") or {}).get("id")
            mid = await _upsert_fixture(conn, lg, season_str, season_year, fx)
            if mid and fid:
                ids[int(fid)] = mid

    print(f"[europe]   {len(ids)} fixtures upserted")

    # Pull season-wide odds (paginated).
    odds_rows = _fetch_odds(key, lg["api_id"], season_year)
    print(f"[europe]   {len(odds_rows)} odds rows returned")
    async with pool.acquire() as conn:
        odds_written = 0
        for o in odds_rows:
            fid = ((o.get("fixture") or {}).get("id"))
            mid = ids.get(int(fid)) if fid else None
            if not mid:
                continue
            await _upsert_odds_for_match(conn, mid, o.get("bookmakers") or [])
            odds_written += 1
    print(f"[europe]   wrote odds for {odds_written} matches")


async def run(season_year: int, which: str) -> None:
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("[europe] API_FOOTBALL_KEY missing"); return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        leagues = []
        if which in ("UCL", "ALL"):
            leagues.append(UCL)
        if which in ("UEL", "ALL"):
            leagues.append(UEL)
        for lg in leagues:
            await _run_league(pool, api_key, lg, season_year)
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--season", type=int, default=2025,
                   help="season start year — API-Football uses calendar year")
    p.add_argument("--league", default="ALL", choices=["UCL", "UEL", "ALL"])
    args = p.parse_args()
    asyncio.run(run(args.season, args.league))


if __name__ == "__main__":
    main()
