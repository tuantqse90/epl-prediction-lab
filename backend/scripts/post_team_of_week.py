"""Phase 42.3 — Monday 10:00 UTC team-of-the-week digest.

Ranks teams by xG-overperformance (goals - xG) across last 7 days of finals.
Top 3 get called out on Telegram. Also lists biggest under-performers
(goals - xG < -1.0) as "due for regression back up" candidates (Phase 42.4
overlaps here — intentionally).

Env:
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

Cron: Monday 10:00 UTC.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import urllib.parse
import urllib.request
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
        print(f"[totw] telegram failed: {type(e).__name__}: {e}")
        return False


async def run() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[totw] telegram creds missing")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            # Per-team xG-over-delta = sum(goals) - sum(xg) across home+away.
            rows = await conn.fetch(
                """
                WITH side AS (
                    SELECT ht.name AS team, m.home_goals AS goals, m.home_xg AS xg
                    FROM matches m
                    JOIN teams ht ON ht.id = m.home_team_id
                    WHERE m.status = 'final'
                      AND m.kickoff_time > NOW() - INTERVAL '7 days'
                      AND m.home_xg IS NOT NULL
                    UNION ALL
                    SELECT at.name AS team, m.away_goals AS goals, m.away_xg AS xg
                    FROM matches m
                    JOIN teams at ON at.id = m.away_team_id
                    WHERE m.status = 'final'
                      AND m.kickoff_time > NOW() - INTERVAL '7 days'
                      AND m.away_xg IS NOT NULL
                )
                SELECT team,
                       SUM(goals)::float AS g,
                       SUM(xg) AS xg,
                       SUM(goals)::float - SUM(xg) AS delta,
                       COUNT(*) AS n
                FROM side
                GROUP BY team
                HAVING COUNT(*) >= 1
                ORDER BY delta DESC
                """
            )
    finally:
        await pool.close()

    if not rows:
        print("[totw] no finals last 7 days")
        return

    hot = [dict(r) for r in rows if r["delta"] is not None and r["delta"] >= 0.5][:3]
    cold = [dict(r) for r in rows if r["delta"] is not None and r["delta"] <= -0.8][:3]

    lines = ["🏆 *Team of the week — xG overperformers* (last 7d)", ""]
    if not hot:
        lines.append("_No clear over-performer this week._")
    else:
        for r in hot:
            lines.append(
                f"• *{r['team']}* · {int(r['g'])} goals vs {r['xg']:.1f} xG  "
                f"(+{r['delta']:.1f}) in {r['n']} match(es)"
            )

    if cold:
        lines += ["", "❄️ *Due a bounce — cold finishers* (goals << xG)"]
        for r in cold:
            lines.append(
                f"• *{r['team']}* · {int(r['g'])} goals vs {r['xg']:.1f} xG  "
                f"({r['delta']:.1f}) in {r['n']} match(es)"
            )

    lines.append("")
    lines.append("https://predictor.nullshift.sh/stats")

    ok = _post(token, chat_id, "\n".join(lines))
    print(f"[totw] posted={ok} hot={len(hot)} cold={len(cold)}")


def main() -> None:
    logging.disable(logging.CRITICAL)
    asyncio.run(run())


if __name__ == "__main__":
    main()
