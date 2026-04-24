"""Daily 10:00 UTC Telegram digest — today's top edges.

Picks up to 3 fixtures kicking off today where the model has an edge
≥ 5pp vs best available odds. Idempotent per day via
`matches.morning_notified_at` column (auto-adds if missing).

Env:
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

Usage:
    python scripts/post_matchday_morning.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings


def _post(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[morning-digest] telegram failed: {type(e).__name__}: {e}")
        return False


def _league_emoji(code: str | None) -> str:
    return {
        "ENG-Premier League": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "ESP-La Liga": "🇪🇸",
        "ITA-Serie A": "🇮🇹",
        "GER-Bundesliga": "🇩🇪",
        "FRA-Ligue 1": "🇫🇷",
        "UEFA-Champions League": "⭐",
        "UEFA-Europa League": "🏆",
    }.get(code or "", "⚽")


async def run() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[morning-digest] missing telegram creds")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        # Ensure the dedup column exists — cheap idempotent migration.
        async with pool.acquire() as conn:
            await conn.execute(
                "ALTER TABLE matches ADD COLUMN IF NOT EXISTS morning_notified_at TIMESTAMPTZ"
            )

        today_date = datetime.now(timezone.utc).date()
        today_utc = today_date.isoformat()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                WITH latest AS (
                    SELECT DISTINCT ON (p.match_id)
                      p.match_id, p.p_home_win, p.p_draw, p.p_away_win
                    FROM predictions p
                    ORDER BY p.match_id, p.created_at DESC
                ),
                best AS (
                    SELECT o.match_id,
                           MAX(o.odds_home) AS bh,
                           MAX(o.odds_draw) AS bd,
                           MAX(o.odds_away) AS ba
                    FROM match_odds o GROUP BY o.match_id
                )
                SELECT m.id, m.league_code, m.kickoff_time,
                       ht.short_name AS home_short, at.short_name AS away_short,
                       l.p_home_win, l.p_draw, l.p_away_win,
                       b.bh, b.bd, b.ba
                FROM matches m
                JOIN teams ht ON ht.id = m.home_team_id
                JOIN teams at ON at.id = m.away_team_id
                JOIN latest l ON l.match_id = m.id
                LEFT JOIN best b ON b.match_id = m.id
                WHERE m.status = 'scheduled'
                  AND m.kickoff_time::date = $1
                  AND m.morning_notified_at IS NULL
                """,
                today_date,
            )

        edges: list[dict] = []
        for r in rows:
            probs = {"H": r["p_home_win"], "D": r["p_draw"], "A": r["p_away_win"]}
            side = max(probs, key=probs.get)
            conf = float(probs[side])
            odds = {"H": r["bh"], "D": r["bd"], "A": r["ba"]}[side]
            if not odds:
                continue
            edge_pp = (conf * float(odds) - 1) * 100
            # 5-30 band — above 30 is almost always stale/mispriced data.
            if not (5.0 <= edge_pp <= 30.0):
                continue
            pick = (
                r["home_short"] if side == "H"
                else r["away_short"] if side == "A"
                else "Draw"
            )
            edges.append({
                "match_id": r["id"],
                "league_code": r["league_code"],
                "ko": r["kickoff_time"],
                "home": r["home_short"], "away": r["away_short"],
                "pick": pick, "conf": conf,
                "odds": float(odds), "edge_pp": edge_pp,
            })

        edges.sort(key=lambda e: -e["edge_pp"])
        if not edges:
            print("[morning-digest] no eligible edges today")
            return

        lines = [f"☀️ *Matchday morning — top edges* _({today_utc})_", ""]
        picked_ids: list[int] = []
        for e in edges[:3]:
            ko_label = str(e["ko"])[11:16]
            lines.append(
                f"{_league_emoji(e['league_code'])} {ko_label}  "
                f"*{e['home']}* vs *{e['away']}*"
            )
            lines.append(
                f"   → {e['pick']} · {int(e['conf']*100)}% @ {e['odds']:.2f} · +{e['edge_pp']:.1f}% edge"
            )
            lines.append("")
            picked_ids.append(e["match_id"])
        lines.append("https://predictor.nullshift.sh/live")

        ok = _post(token, chat_id, "\n".join(lines))
        if ok:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE matches
                    SET morning_notified_at = NOW()
                    WHERE id = ANY($1::int[])
                    """,
                    picked_ids,
                )
            print(f"[morning-digest] posted, marked {len(picked_ids)} matches notified")
        else:
            print("[morning-digest] telegram post failed; no matches flagged")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    asyncio.run(run())


if __name__ == "__main__":
    main()
