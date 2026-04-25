"""Cross-post the weekly summary to Reddit.

Authenticated via PRAW; needs a script-type Reddit app (https://www.reddit.com/prefs/apps).
Set 6 env vars on the VPS:
  REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD,
  REDDIT_USER_AGENT (e.g. 'epl-prediction-lab/1.0 by u/<your-username>'),
  REDDIT_SUBREDDITS (comma-separated, e.g. 'soccerbetting,SoccerBetting')

Posts a self-text summary linking back to /proof + /stories + /scorers.
Be conservative: 1 post per subreddit per week, monitored manually.

Cron: Monday 12:00 UTC (after the weekly retrain has finished).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings


SITE = "https://predictor.nullshift.sh"


async def _fetch_week_summary(pool: asyncpg.Pool) -> dict:
    """Pull headline numbers for the last 7 days: scored matches,
    accuracy, baseline delta, top model picks."""
    async with pool.acquire() as conn:
        acc = await conn.fetchrow(
            """
            WITH latest AS (
                SELECT DISTINCT ON (p.match_id)
                    p.match_id, p.p_home_win, p.p_draw, p.p_away_win
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            )
            SELECT COUNT(*) AS scored,
                   SUM(
                       CASE
                           WHEN m.home_goals > m.away_goals AND
                                l.p_home_win >= GREATEST(l.p_draw, l.p_away_win) THEN 1
                           WHEN m.home_goals < m.away_goals AND
                                l.p_away_win >= GREATEST(l.p_draw, l.p_home_win) THEN 1
                           WHEN m.home_goals = m.away_goals AND
                                l.p_draw >= GREATEST(l.p_home_win, l.p_away_win) THEN 1
                           ELSE 0
                       END
                   )::float / NULLIF(COUNT(*), 0) AS accuracy,
                   SUM(
                       CASE WHEN m.home_goals > m.away_goals THEN 1 ELSE 0 END
                   )::float / NULLIF(COUNT(*), 0) AS home_baseline
            FROM matches m
            JOIN latest l ON l.match_id = m.id
            WHERE m.status = 'final'
              AND m.kickoff_time > NOW() - INTERVAL '7 days'
            """,
        )
    return {
        "scored": int(acc["scored"] or 0),
        "accuracy": float(acc["accuracy"] or 0),
        "home_baseline": float(acc["home_baseline"] or 0),
    }


def _format(summary: dict, week: str) -> tuple[str, str]:
    """Returns (title, body)."""
    title = (
        f"[Weekly] xG ensemble model — {week} accuracy report "
        f"({int(summary['accuracy'] * 100)}% on {summary['scored']} matches)"
    )
    body = f"""**Weekly summary — {week}**

Predictions are SHA-256 committed before kickoff so I can't silently edit them after the fact.

**This week ({summary['scored']} matches scored)**
- Model accuracy: **{int(summary['accuracy'] * 100)}%**
- Home-team baseline: **{int(summary['home_baseline'] * 100)}%**
- Lift over baseline: **{int((summary['accuracy'] - summary['home_baseline']) * 100)}pp**

**Methodology**
- Poisson + Dixon-Coles + Elo + XGBoost ensemble (weights 0.20 / 0.20 / 0.60).
- Walk-forward validation: features computed only from matches strictly before kickoff.
- 5 leagues: EPL, La Liga, Serie A, Bundesliga, Ligue 1, plus UCL + UEL.

**Source links**
- Full proof page: {SITE}/proof
- Per-match stories: {SITE}/stories
- 7-season backtest: {SITE}/history

Open-source: github.com/tuantqse90/epl-prediction-lab. AMA in comments — happy to share specific predictions / counter-examples / why we lose to bookies long-term despite a +2pp short-term beat.
"""
    return title, body


async def run() -> None:
    creds = {
        k: os.environ.get(k)
        for k in (
            "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET",
            "REDDIT_USERNAME", "REDDIT_PASSWORD",
            "REDDIT_USER_AGENT",
        )
    }
    if not all(creds.values()):
        print("[reddit] credentials missing; skipping")
        return
    subs = [
        s.strip()
        for s in (os.environ.get("REDDIT_SUBREDDITS") or "").split(",")
        if s.strip()
    ]
    if not subs:
        print("[reddit] REDDIT_SUBREDDITS env empty; skipping")
        return

    try:
        import praw
    except ImportError:
        print("[reddit] praw not installed; pip install praw")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        summary = await _fetch_week_summary(pool)
    finally:
        await pool.close()

    if summary["scored"] == 0:
        print("[reddit] no scored matches this week, skipping")
        return

    week = datetime.now(timezone.utc).strftime("Week %V %Y")
    title, body = _format(summary, week)

    reddit = praw.Reddit(
        client_id=creds["REDDIT_CLIENT_ID"],
        client_secret=creds["REDDIT_CLIENT_SECRET"],
        username=creds["REDDIT_USERNAME"],
        password=creds["REDDIT_PASSWORD"],
        user_agent=creds["REDDIT_USER_AGENT"],
    )
    for sub in subs:
        try:
            sr = reddit.subreddit(sub)
            post = sr.submit(title=title, selftext=body)
            print(f"[reddit] posted to r/{sub} — {post.shortlink}")
        except Exception as e:
            print(f"[reddit] r/{sub} failed: {type(e).__name__}: {e}")


def main() -> None:
    logging.disable(logging.CRITICAL)
    asyncio.run(run())


if __name__ == "__main__":
    main()
