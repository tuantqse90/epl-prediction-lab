"""Full-squad photos: for every team in our top-5 leagues, pull its
current roster from API-Football and update photo_url for every player
we already have a season-stats row for.

Two-phase:
  1) /teams?league={id}&season={year} — 1 call per league, ~20 teams each.
     Matches by normalized name → stores teams.api_football_id.
  2) /players/squads?team={api_football_id} — 1 call per team, ~25 players.
     Matches by normalized-name candidate keys → updates photo_url +
     api_football_player_id.

Budget per run: ~100 API calls (5 leagues + ~100 teams). Well under Ultra
450/min cap even at 0.15s throttle.

Usage:
    python scripts/ingest_full_squad_photos.py [--season 2025-26]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.leagues import LEAGUES


def _normalize(name: str) -> str:
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    flat = ascii_only.lower().replace("-", " ").replace("'", "").replace("'", "")
    return " ".join(flat.split())


def _candidate_keys(name: str) -> list[str]:
    normalized = _normalize(name)
    if not normalized:
        return []
    parts = normalized.replace(".", "").split()
    keys: list[str] = [normalized, normalized.replace(".", "")]
    if len(parts) >= 2:
        first = parts[0]
        for tok in parts[1:]:
            keys.append(f"{first[0]} {tok}")
            keys.append(f"{first[0]}. {tok}")
            keys.append(tok)
        keys.append(parts[-1])
    seen: set[str] = set()
    out: list[str] = []
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _af_get(key: str, path: str) -> list[dict]:
    """GET + 0.15s throttle to respect 450 req/min cap."""
    time.sleep(0.15)
    url = f"https://v3.football.api-sports.io{path}"
    req = urllib.request.Request(url, headers={"x-apisports-key": key})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.loads(r.read())
    except Exception as e:
        print(f"[squad-photos] {path}: {type(e).__name__}: {e}")
        return []
    return body.get("response", []) or []


async def _resolve_team_ids(pool: asyncpg.Pool, key: str, year: int) -> int:
    """Phase 1: /teams?league= → populate teams.api_football_id."""
    updated = 0
    for lg in [l for l in LEAGUES if l.slug != "all"]:
        resp = _af_get(key, f"/teams?league={lg.api_football_id}&season={year}")
        if not resp:
            continue
        # Build name → api_id index, covering canonical + its candidate forms.
        idx: dict[str, int] = {}
        for entry in resp:
            team = entry.get("team") or {}
            api_name = (team.get("name") or "").strip()
            api_id = team.get("id")
            if not api_name or not api_id:
                continue
            for k in _candidate_keys(api_name):
                idx.setdefault(k, int(api_id))

        # Pull our teams in this league (via any match) and try to match.
        async with pool.acquire() as conn:
            our_teams = await conn.fetch(
                """
                SELECT DISTINCT t.id, t.name
                FROM teams t
                JOIN matches m ON (m.home_team_id = t.id OR m.away_team_id = t.id)
                WHERE m.league_code = $1
                  AND t.api_football_id IS NULL
                """,
                lg.code,
            )
        for row in our_teams:
            for k in _candidate_keys(row["name"]):
                api_id = idx.get(k)
                if api_id:
                    async with pool.acquire() as conn:
                        await conn.execute(
                            "UPDATE teams SET api_football_id = $2 WHERE id = $1",
                            row["id"], api_id,
                        )
                    updated += 1
                    break
        print(f"[squad-photos] {lg.short}: matched {updated}/{len(our_teams)} teams")
    return updated


async def _pull_squads(pool: asyncpg.Pool, key: str, season: str) -> tuple[int, int]:
    """Phase 2: /players/squads per team → update photo_url."""
    async with pool.acquire() as conn:
        teams = await conn.fetch(
            """
            SELECT id, name, slug, api_football_id
            FROM teams
            WHERE api_football_id IS NOT NULL
            ORDER BY id
            """,
        )
    print(f"[squad-photos] pulling squads for {len(teams)} teams")

    total_matched = 0
    total_players_seen = 0
    for t in teams:
        resp = _af_get(key, f"/players/squads?team={t['api_football_id']}")
        if not resp:
            continue
        # Response is either a single-squad object (older API) or a list; normalize.
        squads = resp if isinstance(resp, list) else [resp]
        # Build name-index scoped to this team.
        async with pool.acquire() as conn:
            our_players = await conn.fetch(
                """
                SELECT id, player_name, photo_url
                FROM player_season_stats
                WHERE team_id = $1 AND season = $2
                """,
                t["id"], season,
            )
        idx: dict[str, list[dict]] = {}
        for r in our_players:
            entry = {"id": r["id"], "name": r["player_name"], "has_photo": bool(r["photo_url"])}
            for k in _candidate_keys(r["player_name"]):
                idx.setdefault(k, []).append(entry)

        for sq in squads:
            for p in sq.get("players", []) or []:
                pname = (p.get("name") or "").strip()
                photo = p.get("photo")
                pid = p.get("id")
                if not pname:
                    continue
                total_players_seen += 1
                if not photo:
                    continue
                candidates: list[dict] = []
                for k in _candidate_keys(pname):
                    if k in idx:
                        candidates = idx[k]
                        break
                if not candidates:
                    continue
                # Prefer candidates that don't have a photo yet (so we
                # don't overwrite a real photo with a dupe).
                missing = [c for c in candidates if not c["has_photo"]] or candidates
                for c in missing:
                    async with pool.acquire() as conn:
                        await conn.execute(
                            """
                            UPDATE player_season_stats
                            SET photo_url = COALESCE($2, photo_url),
                                api_football_player_id = COALESCE($3, api_football_player_id)
                            WHERE id = $1
                            """,
                            c["id"], photo, int(pid) if pid else None,
                        )
                    c["has_photo"] = True  # cheap in-memory dedupe
                    total_matched += 1
                    break  # one DB row per API name; don't overwrite siblings

    return total_matched, total_players_seen


async def run(season: str) -> None:
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        print("[squad-photos] missing API_FOOTBALL_KEY")
        return
    year = int(season.split("-")[0])
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        teams_updated = await _resolve_team_ids(pool, key, year)
        print(f"[squad-photos] phase 1: stored api_football_id on {teams_updated} teams")
        matched, seen = await _pull_squads(pool, key, season)
        print(f"[squad-photos] phase 2: {matched} player photos updated ({seen} API players scanned)")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--season", default="2025-26")
    args = p.parse_args()
    asyncio.run(run(args.season))


if __name__ == "__main__":
    main()
