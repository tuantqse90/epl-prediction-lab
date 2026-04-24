"""Post the week's picks to a Telegram channel via Bot API.

Requires env:
    TELEGRAM_BOT_TOKEN   — from @BotFather
    TELEGRAM_CHAT_ID     — channel @handle or numeric chat id

Content: top 5 value bets (model edge ≥ threshold) + top 5 confidence picks.
Quiet no-op when env isn't set, so the weekly cron still passes.

Usage:
    python scripts/post_telegram.py [--horizon-days 7] [--threshold 0.05]
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import urllib.parse
import urllib.request
import json
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.ingest.odds import fair_probs
from app.leagues import BY_CODE, DEFAULT_LEAGUE


def _league_prefix(code: str | None) -> str:
    lg = BY_CODE.get(code or DEFAULT_LEAGUE) or BY_CODE[DEFAULT_LEAGUE]
    return f"{lg.emoji} {lg.short}"


SITE = "https://predictor.nullshift.sh"
VALUE_THRESHOLD_DEFAULT = 0.05


from datetime import timezone, timedelta

# Channel audience is VN; if we ever multi-channel, split this.
VN_TZ = timezone(timedelta(hours=7))

_DAYS_VI = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


def _pp(x: float) -> str:
    """Percentage-point delta as a plain signed number (for human readers)."""
    n = round(x * 100, 1)
    sign = "+" if n > 0 else ""
    return f"{sign}{n:g}%"


def _outcome_verb(o: str, home: str, away: str) -> str:
    """e.g. 'Arsenal thắng' / 'Hòa'. Cleaner than 'home / draw / away'."""
    if o == "H":
        return f"{home} thắng"
    if o == "A":
        return f"{away} thắng"
    return "Hòa"


def _kickoff(ts) -> str:
    """'T7 19/04 14:00' style — short, matches the VN match-card convention."""
    local = ts.astimezone(VN_TZ)
    return f"{_DAYS_VI[local.weekday()]} {local.strftime('%d/%m %H:%M')}"


def _escape_md(text: str) -> str:
    # Telegram legacy Markdown only needs these for literal display inside *bold*
    return text.replace("_", "\\_")


async def _fetch_upcoming(pool: asyncpg.Pool, horizon_days: int) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH latest AS (
                SELECT DISTINCT ON (p.match_id)
                    p.match_id, p.p_home_win, p.p_draw, p.p_away_win,
                    p.expected_home_goals, p.expected_away_goals,
                    p.top_scorelines, p.reasoning, p.model_version
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            )
            SELECT m.id, m.kickoff_time, m.league_code,
                   ht.slug AS home_slug, ht.short_name AS home_short, ht.name AS home_name,
                   at.slug AS away_slug, at.short_name AS away_short, at.name AS away_name,
                   l.p_home_win, l.p_draw, l.p_away_win,
                   l.expected_home_goals, l.expected_away_goals,
                   l.top_scorelines, l.reasoning,
                   o.odds_home, o.odds_draw, o.odds_away
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            JOIN latest l ON l.match_id = m.id
            LEFT JOIN LATERAL (
                SELECT * FROM match_odds WHERE match_id = m.id ORDER BY captured_at DESC LIMIT 1
            ) o ON TRUE
            WHERE m.status = 'scheduled'
              AND m.kickoff_time BETWEEN NOW() AND NOW() + ($1 || ' days')::INTERVAL
            ORDER BY m.kickoff_time ASC
            """,
            str(horizon_days),
        )
    return [dict(r) for r in rows]


def _value_bets(matches: list[dict], threshold: float) -> list[dict]:
    picks: list[dict] = []
    for m in matches:
        if m.get("odds_home") is None:
            continue
        probs = {"H": float(m["p_home_win"]), "D": float(m["p_draw"]), "A": float(m["p_away_win"])}
        fair = fair_probs(m["odds_home"], m["odds_draw"], m["odds_away"])
        if not fair:
            continue
        fair_map = {"H": fair[0], "D": fair[1], "A": fair[2]}
        odds_map = {"H": m["odds_home"], "D": m["odds_draw"], "A": m["odds_away"]}
        best = None
        best_edge = -2.0
        for side in "HDA":
            edge = probs[side] - fair_map[side]
            if edge > best_edge:
                best_edge = edge
                best = side
        if best and best_edge >= threshold:
            picks.append({
                "match": m,
                "outcome": best,
                "edge": best_edge,
                "odds": odds_map[best],
            })
    picks.sort(key=lambda x: x["edge"], reverse=True)
    return picks[:5]


def _confidence_picks(matches: list[dict]) -> list[dict]:
    picks: list[dict] = []
    for m in matches:
        probs = {"H": float(m["p_home_win"]), "D": float(m["p_draw"]), "A": float(m["p_away_win"])}
        top = max(probs, key=probs.get)
        picks.append({"match": m, "outcome": top, "confidence": probs[top]})
    picks.sort(key=lambda x: x["confidence"], reverse=True)
    return picks[:5]


def _format_message(value_bets: list[dict], confidence: list[dict]) -> str:
    lines = [
        "🏆 *Top 5 giải châu Âu — dự đoán tuần này*",
        "",
    ]

    if value_bets:
        lines.append("💰 *Top kèo giá trị*")
        lines.append("_Mô hình thấy thị trường đang định giá sai (chênh ≥ 5%)_")
        lines.append("")
        for i, vb in enumerate(value_bets, 1):
            m = vb["match"]
            link = f"{SITE}/match/{m['id']}"
            probs = {
                "H": float(m["p_home_win"]),
                "D": float(m["p_draw"]),
                "A": float(m["p_away_win"]),
            }
            fair = fair_probs(m["odds_home"], m["odds_draw"], m["odds_away"])
            fair_map = {"H": fair[0], "D": fair[1], "A": fair[2]} if fair else {}
            side = vb["outcome"]
            model_p = round(probs[side] * 100)
            market_p = round(fair_map[side] * 100) if fair_map else None
            verb = _outcome_verb(side, _escape_md(m["home_name"]), _escape_md(m["away_name"]))
            prefix = _league_prefix(m.get("league_code"))
            lines.append(
                f"*{i}.* {prefix} · [{_escape_md(m['home_name'])} vs {_escape_md(m['away_name'])}]({link})"
                f" — _{_kickoff(m['kickoff_time'])}_"
            )
            lines.append(
                f"    → Cược *{verb}* (tỷ lệ {vb['odds']:.2f})"
            )
            if market_p is not None:
                lines.append(
                    f"    Mô hình: {model_p}% · Thị trường: {market_p}% · "
                    f"Lợi thế: *{_pp(vb['edge'])}*"
                )
            lines.append("")

    if confidence:
        lines.append("🎯 *Top dự đoán tự tin nhất*")
        lines.append("")
        for i, cp in enumerate(confidence, 1):
            m = cp["match"]
            link = f"{SITE}/match/{m['id']}"
            verb = _outcome_verb(cp["outcome"], _escape_md(m["home_name"]), _escape_md(m["away_name"]))
            prefix = _league_prefix(m.get("league_code"))
            lines.append(
                f"*{i}.* {prefix} · [{_escape_md(m['home_name'])} vs {_escape_md(m['away_name'])}]({link})"
                f" — _{_kickoff(m['kickoff_time'])}_"
            )
            lines.append(f"    → *{verb}* ({round(cp['confidence'] * 100)}%)")
        lines.append("")

    lines.append("📊 [Xem đầy đủ trên dashboard](" + SITE + ")")
    lines.append("")
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


async def run(horizon_days: int, threshold: float) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[telegram] no TELEGRAM_BOT_TOKEN / CHAT_ID set — skipping")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        matches = await _fetch_upcoming(pool, horizon_days)
    finally:
        await pool.close()

    if not matches:
        print("[telegram] no upcoming matches in window; nothing to post")
        return

    value = _value_bets(matches, threshold=threshold)
    conf = _confidence_picks(matches)
    msg = _format_message(value, conf)
    print(f"[telegram] posting {len(value)} value + {len(conf)} confidence picks")
    result = _post(token, chat_id, msg)
    if not result.get("ok"):
        print(f"[telegram] api error: {result}")
    else:
        print(f"[telegram] posted ok (message_id={result['result'].get('message_id')})")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--horizon-days", type=int, default=7)
    p.add_argument("--threshold", type=float, default=VALUE_THRESHOLD_DEFAULT)
    args = p.parse_args()
    asyncio.run(run(args.horizon_days, args.threshold))


if __name__ == "__main__":
    main()
