"""GET /api/fpl/value — FPL underpriced-players leaderboard by xG per £m.

Fetches FPL bootstrap-static live (cached 30 min), joins to
player_season_stats by canonicalised player name + team slug. No DB
table needed — the FPL data is ephemeral (gameweek-sensitive) and we
only read it on the /fpl page, a handful of times per day.

The value column is `season_xg / price_m` where `price_m` is the FPL
millions price (not the tenths-of-million cost field). Sorts descending.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/fpl", tags=["fpl"])


_FPL_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
_CACHE: dict[str, Any] = {"ts": 0.0, "body": None}
_CACHE_TTL_SEC = 30 * 60

POSITION_LABEL = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _fetch_bootstrap() -> dict[str, Any]:
    now = time.time()
    if _CACHE["body"] is not None and now - _CACHE["ts"] < _CACHE_TTL_SEC:
        return _CACHE["body"]
    req = urllib.request.Request(_FPL_URL, headers={"User-Agent": "epl-lab/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read())
    _CACHE["ts"] = now
    _CACHE["body"] = body
    return body


# FPL team short name → our Understat canonical team name. FPL short names
# are 3 letters (ARS, CHE, etc.) whereas our `teams.name` is the full form.
FPL_TEAM_TO_NAME: dict[str, str] = {
    "ARS": "Arsenal",
    "AVL": "Aston Villa",
    "BOU": "Bournemouth",
    "BRE": "Brentford",
    "BHA": "Brighton",
    "BUR": "Burnley",
    "CHE": "Chelsea",
    "CRY": "Crystal Palace",
    "EVE": "Everton",
    "FUL": "Fulham",
    "LEE": "Leeds",
    "LEI": "Leicester",
    "LIV": "Liverpool",
    "MCI": "Manchester City",
    "MUN": "Manchester United",
    "NEW": "Newcastle United",
    "NFO": "Nottingham Forest",
    "SOU": "Southampton",
    "SUN": "Sunderland",
    "TOT": "Tottenham",
    "WHU": "West Ham",
    "WOL": "Wolverhampton Wanderers",
    "IPS": "Ipswich",
}


class FplPick(BaseModel):
    fpl_id: int
    web_name: str
    full_name: str
    position: str
    team_slug: str
    team_short: str
    price_m: float
    total_points: int
    season_xg: float
    season_games: int
    value: float     # xg / price_m — core ranking signal


@router.get("/value", response_model=list[FplPick])
async def fpl_value(
    request: Request,
    min_games: int = Query(3, ge=0, le=38, description="Minimum appearances to qualify"),
    limit: int = Query(20, ge=1, le=100),
    position: str | None = Query(None, pattern="^(GK|DEF|MID|FWD)$"),
) -> list[FplPick]:
    pool = request.app.state.pool

    try:
        body = _fetch_bootstrap()
    except Exception:
        return []

    fpl_teams = {t["id"]: t["short_name"] for t in body.get("teams", [])}
    elements = body.get("elements", []) or []

    # Build Understat side once.
    async with pool.acquire() as conn:
        us_rows = await conn.fetch(
            """
            SELECT p.player_name, p.games, p.xg, p.position,
                   t.slug AS team_slug, t.name AS team_name, t.short_name AS team_short
            FROM player_season_stats p
            JOIN teams t ON t.id = p.team_id
            WHERE p.season = '2025-26'
              AND p.games >= $1
              AND p.xg IS NOT NULL
            """,
            min_games,
        )

    # Index Understat stats by (team_name, last_name_slug). FPL uses
    # `web_name` which is typically a last name (e.g., "Saka"). Understat
    # uses full name ("Bukayo Saka"). We match on last-word slug + team.
    us_by_key: dict[tuple[str, str], dict] = {}
    for r in us_rows:
        last = r["player_name"].strip().split()[-1]
        us_by_key[(r["team_name"], _slugify(last))] = dict(r)

    out: list[FplPick] = []
    for el in elements:
        pos_id = el.get("element_type")
        pos = POSITION_LABEL.get(pos_id, "?")
        if position and pos != position:
            continue
        team_short = fpl_teams.get(el.get("team"))
        team_name = FPL_TEAM_TO_NAME.get(team_short or "")
        if not team_name:
            continue
        web_name = (el.get("web_name") or "").strip()
        key = (team_name, _slugify(web_name))
        us_row = us_by_key.get(key)
        if us_row is None:
            continue
        price_m = float(el.get("now_cost", 0)) / 10.0
        season_xg = float(us_row["xg"] or 0.0)
        if price_m <= 0 or season_xg <= 0:
            continue
        out.append(
            FplPick(
                fpl_id=int(el.get("id")),
                web_name=web_name,
                full_name=f"{el.get('first_name', '')} {el.get('second_name', '')}".strip(),
                position=pos,
                team_slug=us_row["team_slug"],
                team_short=us_row["team_short"],
                price_m=round(price_m, 1),
                total_points=int(el.get("total_points", 0)),
                season_xg=round(season_xg, 2),
                season_games=int(us_row["games"] or 0),
                value=round(season_xg / price_m, 3),
            )
        )

    out.sort(key=lambda x: x.value, reverse=True)
    return out[:limit]
