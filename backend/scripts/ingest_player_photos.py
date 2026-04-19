"""Pull player photo URLs (+ api-football player ids) via the
/players/topscorers endpoint for each of the top-5 leagues.

One API call per league returns the top 20 goal-scorers with their
photo CDN URL. We name-match back to our Understat-canonical player
names, UPDATE the row with photo_url + api_football_player_id.

Usage:
    python scripts/ingest_player_photos.py [--season 2025-26]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import unicodedata
import urllib.request
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.leagues import LEAGUES


def _fetch(key: str, path: str) -> list[dict]:
    url = f"https://v3.football.api-sports.io{path}"
    req = urllib.request.Request(url, headers={"x-apisports-key": key})
    with urllib.request.urlopen(req, timeout=20) as r:
        body = json.loads(r.read())
    return body.get("response", []) or []


def _normalize(name: str) -> str:
    """Strip diacritics, lowercase, collapse whitespace. Understat often
    uses ASCII forms while API-Football keeps accents — normalize to
    compare. e.g. 'Gonçalo Ramos' → 'goncalo ramos'."""
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(ascii_only.lower().split())


def _candidate_keys(name: str) -> list[str]:
    """All reasonable ways this player could be referenced. Used to build
    a multi-key index so 'Erling Haaland' (Understat) matches 'E. Haaland'
    (API-Football), 'Domingos Duarte' matches 'D. Duarte', etc.

    Order doesn't matter — we insert into a map and try lookup on all
    forms emitted from either side.
    """
    normalized = _normalize(name)
    if not normalized:
        return []
    parts = normalized.replace(".", "").split()
    keys = [normalized, normalized.replace(".", "")]
    if len(parts) >= 2:
        first, last = parts[0], parts[-1]
        keys.append(f"{first[0]} {last}")          # 'e haaland'
        keys.append(f"{first[0]}. {last}")         # 'e. haaland' (API form)
        keys.append(last)                          # 'haaland' — last-name only
    # de-dupe while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


async def run(season: str) -> None:
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        print("[player-photos] missing API_FOOTBALL_KEY")
        return

    year = int(season.split("-")[0])
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            our_rows = await conn.fetch(
                """
                SELECT id, player_name, team_id, goals
                FROM player_season_stats
                WHERE season = $1
                """,
                season,
            )
        # Build multi-key index so 'Erling Haaland' (our) resolves on
        # lookup of 'e. haaland' / 'haaland' (API-Football). Every DB row
        # is inserted under every candidate key it emits.
        by_norm: dict[str, list[dict]] = {}
        for r in our_rows:
            entry = {
                "id": r["id"],
                "team_id": r["team_id"],
                "goals": r["goals"] or 0,
                "name": r["player_name"],
            }
            for k in _candidate_keys(r["player_name"]):
                by_norm.setdefault(k, []).append(entry)

        total_matched = 0
        total_unmatched = 0
        for lg in [l for l in LEAGUES if l.slug != "all"]:
            resp = _fetch(
                key,
                f"/players/topscorers?league={lg.api_football_id}&season={year}",
            )
            for entry in resp:
                player = entry.get("player") or {}
                pname = (player.get("name") or "").strip()
                photo = player.get("photo")
                pid = player.get("id")
                if not pname or not photo:
                    continue
                # Try every candidate-key form this API name could be
                # referenced by, in preference order. Stop at first hit.
                candidates: list[dict] = []
                for k in _candidate_keys(pname):
                    if k in by_norm:
                        candidates = by_norm[k]
                        break
                if not candidates:
                    total_unmatched += 1
                    continue
                # If multiple DB rows share the normalized name (same player
                # on two teams mid-season, transfer), prefer the one with
                # the highest goals count — best heuristic short of team id.
                best = max(candidates, key=lambda c: c["goals"])
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE player_season_stats
                        SET photo_url = $2, api_football_player_id = $3
                        WHERE id = $1
                        """,
                        best["id"], photo, int(pid) if pid else None,
                    )
                total_matched += 1
            print(f"[player-photos] {lg.short}: {len(resp)} topscorers returned")

        print(f"[player-photos] total matched: {total_matched}, unmatched: {total_unmatched}")
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
