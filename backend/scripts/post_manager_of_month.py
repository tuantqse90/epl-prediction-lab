"""Phase 42.2 — Manager of the month Telegram post.

Ranks active-tenure managers by xG-improvement delta over their recent
window (last 10 league finals). Surfaces the top over-performer + a name
underperforming by the same metric.

Env:
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

Cron: 1st of every month at 09:00 UTC.
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
        print(f"[motm] telegram failed: {type(e).__name__}: {e}")
        return False


async def run() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[motm] telegram creds missing")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                WITH active AS (
                    SELECT team_slug, manager_name, started_at
                    FROM manager_tenure
                    WHERE ended_at IS NULL
                ),
                team_side AS (
                    SELECT ht.slug AS team_slug,
                           m.home_goals AS g,
                           m.home_xg AS xg,
                           m.kickoff_time
                    FROM matches m
                    JOIN teams ht ON ht.id = m.home_team_id
                    WHERE m.status = 'final' AND m.home_xg IS NOT NULL
                    UNION ALL
                    SELECT at.slug AS team_slug,
                           m.away_goals AS g,
                           m.away_xg AS xg,
                           m.kickoff_time
                    FROM matches m
                    JOIN teams at ON at.id = m.away_team_id
                    WHERE m.status = 'final' AND m.away_xg IS NOT NULL
                ),
                recent AS (
                    SELECT a.manager_name, a.team_slug,
                           SUM(ts.g)::float AS g,
                           SUM(ts.xg) AS xg,
                           COUNT(*) AS n
                    FROM active a
                    JOIN team_side ts ON ts.team_slug = a.team_slug
                                     AND ts.kickoff_time >= a.started_at
                                     AND ts.kickoff_time > NOW() - INTERVAL '45 days'
                    GROUP BY a.manager_name, a.team_slug
                    HAVING COUNT(*) >= 4
                )
                SELECT manager_name, team_slug,
                       g, xg, n, (g - xg) AS delta
                FROM recent
                ORDER BY (g - xg) DESC
                """
            )
    finally:
        await pool.close()

    if not rows:
        print("[motm] no tenures with ≥4 recent matches")
        return

    top = rows[0]
    bottom = rows[-1] if len(rows) >= 3 else None

    month = datetime.now(timezone.utc).strftime("%B %Y")
    lines = [f"🎩 *Manager of the month — {month}*", ""]
    lines.append(
        f"🏆 *{top['manager_name']}* ({top['team_slug']}): "
        f"{int(top['g'])} goals vs {top['xg']:.1f} xG  "
        f"(+{top['delta']:.1f}) across {top['n']} matches."
    )
    if bottom and float(bottom["delta"]) <= -0.8:
        lines += [
            "",
            f"❄️ Underperformer: *{bottom['manager_name']}* "
            f"({bottom['team_slug']}): {int(bottom['g'])} goals vs "
            f"{bottom['xg']:.1f} xG ({bottom['delta']:.1f}) in {bottom['n']} matches.",
        ]
    lines += ["", "https://predictor.nullshift.sh/"]

    ok = _post(token, chat_id, "\n".join(lines))
    print(f"[motm] posted={ok} top={top['manager_name']} n_tenures={len(rows)}")


def main() -> None:
    logging.disable(logging.CRITICAL)
    asyncio.run(run())


if __name__ == "__main__":
    main()
