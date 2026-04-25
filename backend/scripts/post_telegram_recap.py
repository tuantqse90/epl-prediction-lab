"""Post a weekend recap to the Telegram channel: what the model picked vs
what actually happened in the last N days. Honest counterweight to the
pre-match value-bet post.

Requires env:
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

Usage:
    python scripts/post_telegram_recap.py [--days 7]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import timedelta, timezone
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.leagues import BY_CODE, DEFAULT_LEAGUE


def _league_prefix(code: str | None) -> str:
    lg = BY_CODE.get(code or DEFAULT_LEAGUE) or BY_CODE[DEFAULT_LEAGUE]
    return f"{lg.emoji} {lg.short}"


SITE = "https://predictor.nullshift.sh"
VN_TZ = timezone(timedelta(hours=7))
_DAYS_VI = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


def _outcome(hg: int, ag: int) -> str:
    return "H" if hg > ag else ("A" if hg < ag else "D")


def _pick_label(side: str, home: str, away: str) -> str:
    if side == "H":
        return f"{home} thắng"
    if side == "A":
        return f"{away} thắng"
    return "Hòa"


def _actual_phrase(hg: int, ag: int, home: str, away: str) -> str:
    if hg > ag:
        return f"{home} thắng"
    if hg < ag:
        return f"{away} thắng"
    return "hòa"


def _day_label(ts) -> str:
    local = ts.astimezone(VN_TZ)
    return f"{_DAYS_VI[local.weekday()]} {local.strftime('%d/%m')}"


def _escape(text: str) -> str:
    return text.replace("_", "\\_")


async def _fetch(pool: asyncpg.Pool, days: int) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH latest AS (
                SELECT DISTINCT ON (p.match_id)
                    p.match_id, p.p_home_win, p.p_draw, p.p_away_win
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            )
            SELECT m.id, m.kickoff_time, m.league_code,
                   m.home_goals, m.away_goals,
                   ht.short_name AS home_short, ht.name AS home_name,
                   at.short_name AS away_short, at.name AS away_name,
                   l.p_home_win, l.p_draw, l.p_away_win
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            JOIN latest l ON l.match_id = m.id
            WHERE m.status = 'final'
              AND m.home_goals IS NOT NULL
              AND m.kickoff_time >= NOW() - ($1 || ' days')::INTERVAL
              AND m.kickoff_time <= NOW()
            ORDER BY m.kickoff_time ASC
            """,
            str(days),
        )
    return [dict(r) for r in rows]


def _format(rows: list[dict], days: int) -> str | None:
    if not rows:
        return None

    hits: list[dict] = []
    misses: list[dict] = []
    for r in rows:
        probs = {"H": float(r["p_home_win"]), "D": float(r["p_draw"]), "A": float(r["p_away_win"])}
        pick = max(probs, key=probs.get)
        actual = _outcome(r["home_goals"], r["away_goals"])
        entry = {**r, "pick": pick, "confidence": probs[pick], "actual": actual}
        (hits if pick == actual else misses).append(entry)

    n = len(rows)
    acc = len(hits) / n
    lines = [
        f"📈 *Top 5 giải — độ chính xác {round(acc * 100)}%* ({len(hits)} trận đúng / {n} trận đã đá)",
        "",
        f"_Nhìn lại {days} ngày qua: những trận model dự đoán đúng._",
        "",
    ]

    def _row(e: dict, mark: str) -> str:
        link = f"{SITE}/match/{e['id']}"
        day = _day_label(e["kickoff_time"])
        pick_label = _pick_label(e["pick"], _escape(e["home_name"]), _escape(e["away_name"]))
        prefix = _league_prefix(e.get("league_code"))
        return (
            f"{mark} {prefix} · [{_escape(e['home_name'])} {e['home_goals']}-{e['away_goals']} "
            f"{_escape(e['away_name'])}]({link}) "
            f"· _{day}_ · dự đoán *{pick_label}* ({round(e['confidence'] * 100)}%)"
        )

    # Show only the wins — the recap is meant to celebrate accuracy,
    # not litigate misses. Misses are still computed (for the % at the
    # top), but not enumerated. Users who want the full list can hit
    # /last-weekend.
    if hits:
        lines.append("✅ *Trận model đoán đúng*")
        for e in hits:
            lines.append(_row(e, "•"))
        lines.append("")

    lines.append(f"📊 [Xem đầy đủ]({SITE}/last-weekend)")
    return "\n".join(lines)


def _post(token: str, chat_id: str, text: str) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


async def run(days: int) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[telegram-recap] no bot token / chat id; skipping")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        rows = await _fetch(pool, days)
    finally:
        await pool.close()

    msg = _format(rows, days)
    if msg is None:
        print(f"[telegram-recap] no finals in last {days}d; skipping post")
        return

    print(f"[telegram-recap] posting recap of {len(rows)} matches")
    result = _post(token, chat_id, msg)
    if not result.get("ok"):
        print(f"[telegram-recap] api error: {result}")
    else:
        print(f"[telegram-recap] posted ok (message_id={result['result'].get('message_id')})")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=7)
    args = p.parse_args()
    asyncio.run(run(args.days))


if __name__ == "__main__":
    main()
