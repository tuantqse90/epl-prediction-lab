"""Daily Telegram digest — top 3 value picks for the next 24 hours.

Fires from the daily cron (or its own timer). Compact morning-friendly copy.
Distinct from post_telegram.py (weekly, 5 picks, longer) and
post_telegram_recap.py (post-match only).

Requires env:
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

Usage:
    python scripts/post_telegram_digest.py [--horizon-hours 24] [--threshold 0.05] [--max 3]
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
from app.ingest.odds import fair_probs
from app.leagues import BY_CODE, DEFAULT_LEAGUE


SITE = "https://predictor.nullshift.sh"
VN_TZ = timezone(timedelta(hours=7))
_DAYS_VI = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
_KELLY_CAP = 0.25


def _league_prefix(code: str | None) -> str:
    lg = BY_CODE.get(code or DEFAULT_LEAGUE) or BY_CODE[DEFAULT_LEAGUE]
    return f"{lg.emoji} {lg.short}"


def _kickoff_short(ts) -> str:
    local = ts.astimezone(VN_TZ)
    return f"{_DAYS_VI[local.weekday()]} {local.strftime('%d/%m %H:%M')}"


def _escape(text: str) -> str:
    return text.replace("_", "\\_")


def _kelly(prob: float, odds: float) -> float:
    if prob <= 0 or odds <= 1:
        return 0.0
    edge = prob * odds - 1
    if edge <= 0:
        return 0.0
    return min(_KELLY_CAP, edge / (odds - 1))


def _outcome_verb(o: str, home: str, away: str) -> str:
    if o == "H":
        return f"{home} thắng"
    if o == "A":
        return f"{away} thắng"
    return "Hòa"


async def _fetch(pool: asyncpg.Pool, horizon_hours: int) -> list[dict]:
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
                   ht.short_name AS home_short,
                   at.short_name AS away_short,
                   l.p_home_win, l.p_draw, l.p_away_win,
                   o.odds_home, o.odds_draw, o.odds_away
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            JOIN latest l ON l.match_id = m.id
            LEFT JOIN LATERAL (
                SELECT * FROM match_odds WHERE match_id = m.id
                ORDER BY captured_at DESC LIMIT 1
            ) o ON TRUE
            WHERE m.status = 'scheduled'
              AND m.kickoff_time BETWEEN NOW() AND NOW() + ($1 || ' hours')::INTERVAL
            ORDER BY m.kickoff_time ASC
            """,
            str(horizon_hours),
        )
    return [dict(r) for r in rows]


def _top_value(matches: list[dict], threshold: float, max_n: int) -> list[dict]:
    picks: list[dict] = []
    for m in matches:
        if m.get("odds_home") is None:
            continue
        fair = fair_probs(m["odds_home"], m["odds_draw"], m["odds_away"])
        if not fair:
            continue
        probs = {"H": float(m["p_home_win"]), "D": float(m["p_draw"]), "A": float(m["p_away_win"])}
        fair_map = {"H": fair[0], "D": fair[1], "A": fair[2]}
        odds_map = {"H": m["odds_home"], "D": m["odds_draw"], "A": m["odds_away"]}
        best = max("HDA", key=lambda s: probs[s] - fair_map[s])
        edge = probs[best] - fair_map[best]
        if edge < threshold:
            continue
        picks.append({
            "match": m,
            "outcome": best,
            "model_prob": probs[best],
            "market_prob": fair_map[best],
            "edge": edge,
            "odds": float(odds_map[best]),
            "kelly": _kelly(probs[best], float(odds_map[best])),
        })
    picks.sort(key=lambda x: x["edge"], reverse=True)
    return picks[:max_n]


def _format(picks: list[dict], horizon_hours: int) -> str | None:
    if not picks:
        return None

    lines = [
        f"⚡ *Giá trị trong {horizon_hours}h tới* · top {len(picks)}",
        "",
    ]
    for i, p in enumerate(picks, 1):
        m = p["match"]
        link = f"{SITE}/match/{m['id']}"
        home = _escape(m["home_short"])
        away = _escape(m["away_short"])
        prefix = _league_prefix(m.get("league_code"))
        verb = _outcome_verb(p["outcome"], home, away)
        lines.append(
            f"*{i}.* {prefix} · [{home} vs {away}]({link}) · _{_kickoff_short(m['kickoff_time'])}_"
        )
        lines.append(
            f"   → *{verb}* @ {p['odds']:.2f} · model {round(p['model_prob'] * 100)}%"
            f" vs thị trường {round(p['market_prob'] * 100)}% · lợi thế *+{round(p['edge'] * 100)}%*"
        )
        if p["kelly"] > 0:
            lines.append(f"   Kelly: {p['kelly'] * 100:.1f}% vốn")
        lines.append("")

    lines.append(f"📊 [Xem tất cả trên dashboard]({SITE})")
    lines.append("_Chỉ để tham khảo, không phải lời khuyên cá cược._")
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


async def run(horizon_hours: int, threshold: float, max_n: int) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[tg-digest] TELEGRAM_BOT_TOKEN / CHAT_ID missing — skipping")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        matches = await _fetch(pool, horizon_hours)
    finally:
        await pool.close()

    if not matches:
        print(f"[tg-digest] no scheduled matches in next {horizon_hours}h — skipping")
        return

    picks = _top_value(matches, threshold=threshold, max_n=max_n)
    msg = _format(picks, horizon_hours)
    if msg is None:
        print(f"[tg-digest] no value picks ≥ {threshold:.0%} in {len(matches)} matches — skipping")
        return

    print(f"[tg-digest] posting {len(picks)} value picks")
    result = _post(token, chat_id, msg)
    if not result.get("ok"):
        print(f"[tg-digest] api error: {result}")
    else:
        print(f"[tg-digest] posted ok (message_id={result['result'].get('message_id')})")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--horizon-hours", type=int, default=24)
    p.add_argument("--threshold", type=float, default=0.05)
    p.add_argument("--max", type=int, default=3)
    args = p.parse_args()
    asyncio.run(run(args.horizon_hours, args.threshold, args.max))


if __name__ == "__main__":
    main()
