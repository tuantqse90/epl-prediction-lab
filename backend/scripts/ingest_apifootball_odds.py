"""Pull pre-match odds from API-Football /odds endpoint and upsert into
match_odds + match_odds_markets.

Why a second odds source on top of the-odds-api:
- API-Football Ultra allows 75k requests/day (the-odds-api free is 500/mo)
- Includes BTTS (blocked on our the-odds-api tier)
- Provides many more O/U lines in one call (0.5, 1.5, 2.5, 3.5, 4.5)
- Per-book odds from 20+ bookmakers (Bet365, Pinnacle, William Hill, …)

Source naming convention on match_odds + match_odds_markets:
- `af:<bookmaker_name>` per-book rows (e.g. `af:Bet365`)
- `af:avg` pooled-average row (parallel to the-odds-api:avg)

Quota-light: each call is filtered by (league, season, bet_id), one page
typically holds 10 fixtures. Top-5 leagues × 4 bet types × ~3 pages = ~60
calls per full ingest run — less than 0.1% of daily quota.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import asyncpg
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.ingest.odds import OddsRow, upsert_odds
from app.leagues import LEAGUES

# Bet-type IDs in API-Football's registry. See /odds/bets for the full 337.
BET_1X2 = 1
BET_AH = 4
BET_OU = 5
BET_BTTS = 8

# API-Football team names sometimes drift from Understat's canonical. Reuse
# the same NAME_MAP from the football-data flow via _canon.
from app.ingest.odds import _canon as _canon_od

# Additional mappings specific to API-Football's labels.
AF_NAME_MAP: dict[str, str] = {
    "Manchester City": "Manchester City",   # identity — kept to make this dict authoritative
    "Manchester United": "Manchester United",
    "Newcastle": "Newcastle United",
    "Tottenham": "Tottenham",
    "Leeds": "Leeds",
    "Wolves": "Wolverhampton Wanderers",
    "West Ham": "West Ham",
    "Nottingham Forest": "Nottingham Forest",
    "Crystal Palace": "Crystal Palace",
    "Athletic Club": "Athletic Club",
    "Atletico Madrid": "Atletico Madrid",
    "Real Madrid": "Real Madrid",
    "FC Barcelona": "Barcelona",
    "Real Sociedad": "Real Sociedad",
    "Real Betis": "Real Betis",
    "Rayo Vallecano": "Rayo Vallecano",
    "Celta Vigo": "Celta Vigo",
    "Real Oviedo": "Real Oviedo",
    "Bayern München": "Bayern Munich",
    "Bayer Leverkusen": "Bayer Leverkusen",
    "Borussia Dortmund": "Borussia Dortmund",
    "RB Leipzig": "RasenBallsport Leipzig",
    "Eintracht Frankfurt": "Eintracht Frankfurt",
    "VfB Stuttgart": "VfB Stuttgart",
    "Borussia Mönchengladbach": "Borussia M.Gladbach",
    "FC Köln": "FC Cologne",
    "1. FC Heidenheim": "FC Heidenheim",
    "FSV Mainz 05": "Mainz 05",
    "1. FC Union Berlin": "Union Berlin",
    "St. Pauli": "St. Pauli",
    "Hamburger SV": "Hamburger SV",
    "Paris Saint Germain": "Paris Saint Germain",
    "Olympique Marseille": "Marseille",
    "Olympique Lyonnais": "Lyon",
    "Stade Rennais": "Rennes",
    "AS Monaco": "Monaco",
}


def _canon(name: str) -> str:
    return AF_NAME_MAP.get(name, _canon_od(name))


def _fetch(key: str, path: str) -> dict:
    url = f"https://v3.football.api-sports.io{path}"
    req = urllib.request.Request(url, headers={"x-apisports-key": key})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def _iter_pages(key: str, league_id: int, season_year: int, bet: int):
    """Yield every event across paginated pages for (league, bet)."""
    page = 1
    while True:
        path = f"/odds?league={league_id}&season={season_year}&bet={bet}&page={page}"
        body = _fetch(key, path)
        resp = body.get("response", []) or []
        for ev in resp:
            yield ev
        paging = body.get("paging", {}) or {}
        total = int(paging.get("total") or 1)
        if page >= total:
            return
        page += 1
        time.sleep(0.2)  # polite — stays well under the 450 req/min limit


async def _find_match_id(conn, home_name: str, away_name: str, kickoff_iso: str) -> int | None:
    """Resolve an AF fixture to matches.id by name + date (Understat-canonical)."""
    try:
        d = pd.to_datetime(kickoff_iso).date()
    except Exception:
        return None
    return await conn.fetchval(
        """
        SELECT m.id FROM matches m
        JOIN teams ht ON ht.id = m.home_team_id
        JOIN teams at ON at.id = m.away_team_id
        WHERE ht.name = $1 AND at.name = $2
          AND DATE(m.kickoff_time) = $3
        LIMIT 1
        """,
        _canon(home_name), _canon(away_name), d,
    )


def _parse_1x2(bet_values: list[dict]) -> tuple[float, float, float] | None:
    out = {"Home": None, "Draw": None, "Away": None}
    for v in bet_values:
        val = v.get("value")
        odd = v.get("odd")
        if val not in out:
            continue
        try:
            out[val] = float(odd)
        except (TypeError, ValueError):
            continue
    if None in out.values():
        return None
    return out["Home"], out["Draw"], out["Away"]


def _parse_ou(bet_values: list[dict]) -> list[tuple[float, str, float]]:
    """Return (line, outcome_code, odds) tuples from O/U values like
    'Over 2.5' / 'Under 1.5'."""
    out: list[tuple[float, str, float]] = []
    for v in bet_values:
        val = (v.get("value") or "").strip()
        odd = v.get("odd")
        if not val or not odd:
            continue
        parts = val.split()
        if len(parts) != 2:
            continue
        side = parts[0].upper()
        if side not in ("OVER", "UNDER"):
            continue
        try:
            line = float(parts[1])
            price = float(odd)
        except ValueError:
            continue
        out.append((line, side, price))
    return out


def _parse_btts(bet_values: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for v in bet_values:
        val = (v.get("value") or "").strip().upper()
        odd = v.get("odd")
        if val not in ("YES", "NO") or not odd:
            continue
        try:
            out[val] = float(odd)
        except ValueError:
            continue
    return out


def _parse_ah(bet_values: list[dict]) -> list[tuple[float, str, float]]:
    """Return (line_home_perspective, side_code, odds) from AH values like
    'Home -1' / 'Away -0.5'. line is stored from the home perspective so both
    sides hit the same match_odds_markets key family."""
    out: list[tuple[float, str, float]] = []
    for v in bet_values:
        val = (v.get("value") or "").strip()
        odd = v.get("odd")
        if not val or not odd:
            continue
        # Normalise whitespace, split
        parts = val.replace("+", " +").replace("-", " -").split()
        # Expected form: 'Home', '-1' or 'Away', '+0.5'
        if len(parts) < 2:
            continue
        side_name = parts[0].lower()
        line_str = "".join(parts[1:])
        try:
            raw_line = float(line_str)
            price = float(odd)
        except ValueError:
            continue
        if side_name == "home":
            out.append((raw_line, "HOME", price))
        elif side_name == "away":
            # Away -0.5 = Home +0.5 for storage key
            out.append((-raw_line, "AWAY", price))
    return out


async def _upsert_1x2(conn, match_id: int, source: str, h: float, d: float, a: float) -> int:
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
        match_id, source, h, d, a,
    )
    return 1


async def _upsert_mkt(conn, match_id: int, source: str, market: str,
                     line: float | None, outcome: str, odds: float) -> int:
    await conn.execute(
        """
        INSERT INTO match_odds_markets (
            match_id, source, market_code, line, outcome_code, odds
        ) VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (match_id, source, market_code, line, outcome_code)
        DO UPDATE SET odds = EXCLUDED.odds, captured_at = NOW()
        """,
        match_id, source, market, line, outcome, odds,
    )
    return 1


async def run(season: str, leagues: list) -> None:
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        print("[af-odds] missing API_FOOTBALL_KEY")
        return
    season_year = int(season.split("-")[0])

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        total_1x2 = 0
        total_mkt = 0
        async with pool.acquire() as conn:
            for lg in leagues:
                lg_1x2 = 0
                lg_mkt = 0
                for bet_id in (BET_1X2, BET_OU, BET_BTTS, BET_AH):
                    try:
                        for ev in _iter_pages(key, lg.api_football_id, season_year, bet_id):
                            fx = ev.get("fixture") or {}
                            home = (ev.get("teams") or {}).get("home", {}).get("name") or ""
                            away = (ev.get("teams") or {}).get("away", {}).get("name") or ""
                            kickoff = fx.get("date")
                            if not (home and away and kickoff):
                                continue
                            match_id = await _find_match_id(conn, home, away, kickoff)
                            if match_id is None:
                                continue

                            # Averages across books per bet type.
                            pool_vals: dict[str, list] = {}

                            for bk in ev.get("bookmakers") or []:
                                book_name = bk.get("name") or ""
                                if not book_name:
                                    continue
                                book_src = f"af:{book_name}"
                                for bet in bk.get("bets") or []:
                                    values = bet.get("values") or []
                                    if bet_id == BET_1X2:
                                        triple = _parse_1x2(values)
                                        if triple:
                                            await _upsert_1x2(conn, match_id, book_src, *triple)
                                            lg_1x2 += 1
                                            pool_vals.setdefault("1x2", []).append(triple)
                                    elif bet_id == BET_OU:
                                        for line, side, price in _parse_ou(values):
                                            await _upsert_mkt(conn, match_id, book_src, "OU", line, side, price)
                                            lg_mkt += 1
                                            pool_vals.setdefault(("OU", line, side), []).append(price)
                                    elif bet_id == BET_BTTS:
                                        for side, price in _parse_btts(values).items():
                                            await _upsert_mkt(conn, match_id, book_src, "BTTS", None, side, price)
                                            lg_mkt += 1
                                            pool_vals.setdefault(("BTTS", None, side), []).append(price)
                                    elif bet_id == BET_AH:
                                        for line, side, price in _parse_ah(values):
                                            await _upsert_mkt(conn, match_id, book_src, "AH", line, side, price)
                                            lg_mkt += 1
                                            pool_vals.setdefault(("AH", line, side), []).append(price)

                            # Pooled average per key.
                            if bet_id == BET_1X2 and "1x2" in pool_vals:
                                hs = [t[0] for t in pool_vals["1x2"]]
                                ds = [t[1] for t in pool_vals["1x2"]]
                                as_ = [t[2] for t in pool_vals["1x2"]]
                                await _upsert_1x2(conn, match_id, "af:avg",
                                                  sum(hs)/len(hs), sum(ds)/len(ds), sum(as_)/len(as_))
                                lg_1x2 += 1
                            else:
                                for k, prices in pool_vals.items():
                                    if not isinstance(k, tuple):
                                        continue
                                    market, line, side = k
                                    avg = sum(prices) / len(prices)
                                    await _upsert_mkt(conn, match_id, "af:avg", market, line, side, avg)
                                    lg_mkt += 1
                    except Exception as e:
                        print(f"[af-odds] {lg.short} bet={bet_id}: {type(e).__name__}: {e}")
                        continue
                print(f"[af-odds] {lg.short}: 1X2 {lg_1x2} · markets {lg_mkt}")
                total_1x2 += lg_1x2
                total_mkt += lg_mkt
        print(f"[af-odds] total: 1X2 {total_1x2} / markets {total_mkt}")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    from app.leagues import LEAGUES, get_league
    p = argparse.ArgumentParser()
    p.add_argument("--season", default="2025-26")
    p.add_argument("--league", default=None,
                   help="optional single-league slug; default = top 5")
    args = p.parse_args()
    # Only top 5 by default — API-Football Ultra covers more, but our FE
    # slug map only handles the top 5.
    if args.league:
        leagues = [get_league(args.league)]
    else:
        leagues = [lg for lg in LEAGUES if lg.slug in ("epl", "laliga", "seriea", "bundesliga", "ligue1")]
    asyncio.run(run(args.season, leagues))


if __name__ == "__main__":
    main()
