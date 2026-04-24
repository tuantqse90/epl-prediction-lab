"""Phase 42.5 — Friday 18:00 UTC weekend preview.

Pulls every scheduled fixture Fri-Sun across 5 leagues + UCL/UEL + ranks by
"must-watch" heuristic (max-prob margin < 15pp OR any side prob > 70%).
Hands the list to Qwen for a 500-700 word preview, posts to Telegram.

Env:
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DASHSCOPE_API_KEY

Cron: Friday 18:00 UTC.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.llm.reasoning import _call_qwen


PREVIEW_SYSTEM = (
    "Bạn là cây bút bóng đá cuối tuần. Viết preview 500-700 từ, tiếng Việt, "
    "giọng dễ đọc. Dùng đúng số liệu được cung cấp. Không phóng đại. "
    "Chia thành phần giới thiệu + 3-5 trận đáng chú ý + câu kết."
)


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
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[weekend-preview] telegram failed: {type(e).__name__}: {e}")
        return False


async def _gather_fixtures(pool: asyncpg.Pool) -> list[dict]:
    now = datetime.now(timezone.utc)
    # Friday 00:00 UTC through Sunday 23:59 UTC (any Fri/Sat/Sun kickoffs).
    weekday = now.weekday()
    days_to_friday = (4 - weekday) % 7
    if days_to_friday == 0 and now.hour >= 12:
        # Running on Fri afternoon — use today as the start.
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = (now + timedelta(days=days_to_friday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    end = start + timedelta(days=3)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH latest AS (
                SELECT DISTINCT ON (p.match_id)
                    p.match_id, p.p_home_win, p.p_draw, p.p_away_win, p.top_scorelines
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            )
            SELECT m.id, m.league_code, m.kickoff_time,
                   ht.short_name AS home, at.short_name AS away,
                   l.p_home_win, l.p_draw, l.p_away_win
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            LEFT JOIN latest l ON l.match_id = m.id
            WHERE m.status = 'scheduled'
              AND m.kickoff_time >= $1
              AND m.kickoff_time < $2
            ORDER BY m.kickoff_time ASC
            """,
            start, end,
        )
    return [dict(r) for r in rows]


def _score_fixture(f: dict) -> float:
    if f["p_home_win"] is None:
        return 0.0
    ph, pd, pa = float(f["p_home_win"]), float(f["p_draw"]), float(f["p_away_win"])
    top = max(ph, pd, pa)
    second = sorted([ph, pd, pa], reverse=True)[1]
    # Favour either tight matches (margin < 15pp) OR blowouts (>70% one side).
    tightness = max(0.0, 0.15 - (top - second)) * 10
    blowout = max(0.0, top - 0.70) * 5
    return tightness + blowout


def _format_fixture(f: dict) -> str:
    ko = f["kickoff_time"].strftime("%a %H:%M UTC")
    if f["p_home_win"] is None:
        return f"- {ko} · {f['home']} vs {f['away']} · no prediction yet"
    ph, pd, pa = float(f["p_home_win"]), float(f["p_draw"]), float(f["p_away_win"])
    return (
        f"- {ko} · {f['home']} vs {f['away']} · "
        f"{int(ph*100)}/{int(pd*100)}/{int(pa*100)}"
    )


async def run() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[weekend-preview] telegram creds missing")
        return

    settings = get_settings()
    if not settings.dashscope_api_key:
        print("[weekend-preview] DASHSCOPE_API_KEY missing")
        return

    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        fixtures = await _gather_fixtures(pool)
    finally:
        await pool.close()

    if not fixtures:
        print("[weekend-preview] no scheduled fixtures Fri-Sun")
        return

    fixtures_scored = sorted(fixtures, key=_score_fixture, reverse=True)
    highlight = fixtures_scored[:8]
    total = len(fixtures)
    fixture_lines = "\n".join(_format_fixture(f) for f in highlight)

    prompt = (
        f"Có {total} trận đấu từ thứ 6 đến Chủ nhật. Top 8 đáng chú ý theo model:\n"
        f"{fixture_lines}\n\n"
        f"Viết preview 500-700 từ, tiếng Việt. Chia 3 phần:\n"
        f"- Mở bài 1 đoạn: tổng quan cuối tuần\n"
        f"- Thân bài: chọn 3-5 trận nổi bật (lý do model thích/không thích, "
        f"rủi ro chính) — bullet hoặc đoạn ngắn\n"
        f"- Kết: 1 câu dự báo cuối tuần sẽ có nhiều bất ngờ hay không."
    )

    try:
        body = _call_qwen(
            prompt,
            model="dashscope/qwen-plus-latest",
            system=PREVIEW_SYSTEM,
            max_tokens=1200,
            temperature=0.6,
        )
    except Exception as e:
        print(f"[weekend-preview] qwen failed: {type(e).__name__}: {e}")
        return

    header = "🎬 *Weekend Preview*\n\n"
    footer = "\n\nhttps://predictor.nullshift.sh/"
    msg = header + body + footer
    # Telegram message limit is 4096 chars — truncate body if needed.
    if len(msg) > 4000:
        msg = header + body[:4000 - len(header) - len(footer) - 3] + "…" + footer

    ok = _post(token, chat_id, msg)
    print(f"[weekend-preview] posted={ok} fixtures={total} body_chars={len(body)}")


def main() -> None:
    logging.disable(logging.CRITICAL)
    asyncio.run(run())


if __name__ == "__main__":
    main()
