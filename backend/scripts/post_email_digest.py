"""Weekly email digest — every Monday 09:00 UTC.

Queries the same data the web surfaces use: top edges + last-week
performance. Sends to every `confirmed_at IS NOT NULL AND unsubscribed_at
IS NULL` email via Resend, logs last_sent_at so re-runs are idempotent.

Env:
    RESEND_API_KEY
    EMAIL_FROM (optional)

Usage:
    python scripts/post_email_digest.py [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.api.email import render_digest_html, _send_email


async def _fetch_top_picks(pool) -> list[dict]:
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
                   ht.short_name AS home, at.short_name AS away,
                   l.p_home_win, l.p_draw, l.p_away_win,
                   b.bh, b.bd, b.ba
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            JOIN latest l ON l.match_id = m.id
            LEFT JOIN best b ON b.match_id = m.id
            WHERE m.status = 'scheduled'
              AND m.kickoff_time BETWEEN NOW() AND NOW() + INTERVAL '7 days'
            """,
        )
    picks = []
    for r in rows:
        probs = {"H": r["p_home_win"], "D": r["p_draw"], "A": r["p_away_win"]}
        side = max(probs, key=probs.get)
        odds = {"H": r["bh"], "D": r["bd"], "A": r["ba"]}[side]
        if not odds:
            continue
        edge = probs[side] * odds - 1
        if edge < 0.05 or edge > 0.30:
            continue
        picks.append({
            "league_code": r["league_code"],
            "home": r["home"],
            "away": r["away"],
            "pick": r["home"] if side == "H" else r["away"] if side == "A" else "Draw",
            "conf": probs[side],
            "odds": odds,
            "edge_pp": edge * 100,
            "kickoff_time": r["kickoff_time"],
        })
    picks.sort(key=lambda p: -p["edge_pp"])
    return picks


async def _fetch_last_week(pool) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
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
            ),
            graded AS (
                SELECT m.id, m.home_goals, m.away_goals,
                       l.p_home_win, l.p_draw, l.p_away_win,
                       b.bh, b.bd, b.ba
                FROM matches m
                JOIN latest l ON l.match_id = m.id
                LEFT JOIN best b ON b.match_id = m.id
                WHERE m.status = 'final'
                  AND m.kickoff_time > NOW() - INTERVAL '7 days'
                  AND m.home_goals IS NOT NULL
            )
            SELECT
              COUNT(*) AS scored,
              COUNT(*) FILTER (
                WHERE (p_home_win >= p_draw AND p_home_win >= p_away_win AND home_goals > away_goals)
                   OR (p_away_win >= p_home_win AND p_away_win >= p_draw AND home_goals < away_goals)
                   OR (p_draw >= p_home_win AND p_draw >= p_away_win AND home_goals = away_goals)
              ) AS correct,
              COALESCE(SUM(
                CASE
                  WHEN p_home_win >= p_draw AND p_home_win >= p_away_win
                       AND bh IS NOT NULL AND p_home_win * bh - 1 >= 0.05
                    THEN CASE WHEN home_goals > away_goals THEN bh - 1 ELSE -1 END
                  WHEN p_draw >= p_home_win AND p_draw >= p_away_win
                       AND bd IS NOT NULL AND p_draw * bd - 1 >= 0.05
                    THEN CASE WHEN home_goals = away_goals THEN bd - 1 ELSE -1 END
                  WHEN p_away_win >= p_home_win AND p_away_win >= p_draw
                       AND ba IS NOT NULL AND p_away_win * ba - 1 >= 0.05
                    THEN CASE WHEN home_goals < away_goals THEN ba - 1 ELSE -1 END
                END
              ), 0)::float AS pnl,
              COUNT(*) FILTER (
                WHERE (p_home_win >= p_draw AND p_home_win >= p_away_win
                       AND bh IS NOT NULL AND p_home_win * bh - 1 >= 0.05)
                   OR (p_draw >= p_home_win AND p_draw >= p_away_win
                       AND bd IS NOT NULL AND p_draw * bd - 1 >= 0.05)
                   OR (p_away_win >= p_home_win AND p_away_win >= p_draw
                       AND ba IS NOT NULL AND p_away_win * ba - 1 >= 0.05)
              ) AS value_bets
            FROM graded
            """,
        )
    scored = int(row["scored"] or 0)
    correct = int(row["correct"] or 0)
    pnl = float(row["pnl"] or 0.0)
    value_bets = int(row["value_bets"] or 0)
    return {
        "scored": scored,
        "correct": correct,
        "accuracy": (correct / scored) if scored else 0.0,
        "pnl": pnl,
        "roi_pct": (pnl / value_bets * 100) if value_bets else 0.0,
    }


async def run(dry_run: bool) -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        top_picks = await _fetch_top_picks(pool)
        last_week = await _fetch_last_week(pool)
        html_tmpl = render_digest_html(top_picks=top_picks, last_week=last_week)
        print(f"[digest] top_picks={len(top_picks)} last_week_scored={last_week['scored']}")

        async with pool.acquire() as conn:
            subs = await conn.fetch(
                """
                SELECT email, token FROM email_subscriptions
                WHERE confirmed_at IS NOT NULL
                  AND unsubscribed_at IS NULL
                """,
            )
        print(f"[digest] {len(subs)} confirmed subscribers")

        sent = 0
        for s in subs:
            html = html_tmpl.replace("{UNSUB_TOKEN}", s["token"])
            if dry_run:
                print(f"[digest] DRY: would send to {s['email']}")
                continue
            ok, err = _send_email(s["email"], "Prediction Lab — weekly digest", html)
            if ok:
                sent += 1
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE email_subscriptions SET last_sent_at = $1 WHERE email = $2",
                        datetime.now(timezone.utc), s["email"],
                    )
            else:
                print(f"[digest] failed {s['email']}: {err}")
        print(f"[digest] sent {sent}/{len(subs)}")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    asyncio.run(run(args.dry_run))


if __name__ == "__main__":
    main()
