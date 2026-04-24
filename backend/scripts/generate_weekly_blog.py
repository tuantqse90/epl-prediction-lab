"""Weekly auto-blog — Mon 10:00 UTC, draft "Week N: what the model learned".

Pulls last-week metrics + notable matches + notable picks and asks
Qwen to write a ~600-word reflective post. Inserts into
auto_blog_posts, which the Next.js /blog route reads alongside the
file-based posts.

Env:
    DASHSCOPE_API_KEY

Usage:
    python scripts/generate_weekly_blog.py [--force]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.llm.reasoning import _call_qwen


SYSTEM = (
    "You are a football-analytics writer. 500-700 words. Reflective tone, "
    "not hypey. Ground every claim in the provided week metrics + match "
    "list. Do not invent scores, player names, or narrative beats that "
    "aren't in the prompt. Structure: short intro, what the numbers say, "
    "2-3 notable matches, what it tells us about the model, a one-line "
    "look-ahead to the coming week. Markdown. Use ## for section headers."
)


async def _gather_week(conn) -> dict:
    """Accuracy + P&L + 3 notable matches from the last 7 days."""
    row = await conn.fetchrow(
        """
        WITH latest AS (
            SELECT DISTINCT ON (p.match_id)
              p.match_id, p.p_home_win, p.p_draw, p.p_away_win
            FROM predictions p
            ORDER BY p.match_id, p.created_at DESC
        ),
        graded AS (
            SELECT m.id, m.home_goals, m.away_goals,
                   l.p_home_win, l.p_draw, l.p_away_win
            FROM matches m
            JOIN latest l ON l.match_id = m.id
            WHERE m.status = 'final'
              AND m.kickoff_time > NOW() - INTERVAL '7 days'
              AND m.home_goals IS NOT NULL
        )
        SELECT COUNT(*) AS scored,
          COUNT(*) FILTER (
            WHERE (p_home_win >= p_draw AND p_home_win >= p_away_win AND home_goals > away_goals)
               OR (p_away_win >= p_home_win AND p_away_win >= p_draw AND home_goals < away_goals)
               OR (p_draw >= p_home_win AND p_draw >= p_away_win AND home_goals = away_goals)
          ) AS correct
        FROM graded
        """,
    )
    scored = int(row["scored"] or 0)
    correct = int(row["correct"] or 0)

    notable = await conn.fetch(
        """
        WITH latest AS (
            SELECT DISTINCT ON (p.match_id)
              p.match_id, p.p_home_win, p.p_draw, p.p_away_win
            FROM predictions p
            ORDER BY p.match_id, p.created_at DESC
        )
        SELECT ht.short_name AS home, at.short_name AS away,
               m.home_goals, m.away_goals, m.league_code, m.kickoff_time,
               l.p_home_win, l.p_draw, l.p_away_win
        FROM matches m
        JOIN teams ht ON ht.id = m.home_team_id
        JOIN teams at ON at.id = m.away_team_id
        JOIN latest l ON l.match_id = m.id
        WHERE m.status = 'final'
          AND m.kickoff_time > NOW() - INTERVAL '7 days'
          AND m.home_goals IS NOT NULL
        ORDER BY GREATEST(l.p_home_win, l.p_draw, l.p_away_win) DESC
        LIMIT 4
        """,
    )

    return {
        "scored": scored, "correct": correct,
        "accuracy": (correct / scored) if scored else 0.0,
        "matches": [dict(r) for r in notable],
    }


def _prompt(week: dict, now: datetime) -> str:
    lines = [f"Week ending {now.strftime('%Y-%m-%d')}"]
    lines.append(
        f"Matches graded: {week['scored']}, correct: {week['correct']} "
        f"({week['accuracy']*100:.1f}% accuracy)."
    )
    lines.append("")
    lines.append("Notable matches (model's most-confident picks):")
    for m in week["matches"]:
        probs = {"H": m["p_home_win"], "D": m["p_draw"], "A": m["p_away_win"]}
        pick = max(probs, key=probs.get)
        conf = probs[pick] * 100
        pick_label = m["home"] if pick == "H" else m["away"] if pick == "A" else "Draw"
        actual = "H" if m["home_goals"] > m["away_goals"] else "A" if m["home_goals"] < m["away_goals"] else "D"
        hit = "HIT" if pick == actual else "MISS"
        lines.append(
            f"- {m['league_code']}: {m['home']} {m['home_goals']}-{m['away_goals']} {m['away']} "
            f"- model picked {pick_label} @ {conf:.0f}% → {hit}"
        )
    lines.append("")
    lines.append(
        "Write the weekly reflection. What did the model get right, "
        "where did it miss, and what do the numbers tell us?"
    )
    return "\n".join(lines)


def _slug_and_title(now: datetime) -> tuple[str, str]:
    week_num = now.isocalendar().week
    year = now.year
    slug = f"week-{week_num:02d}-{year}"
    title = f"Week {week_num}, {year}: what the model learned"
    return slug, title


async def run(force: bool) -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        now = datetime.now(timezone.utc)
        slug, title = _slug_and_title(now)

        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT generated_at FROM auto_blog_posts WHERE slug = $1", slug
            )
        if existing and not force:
            print(f"[blog] {slug} already exists (generated {existing['generated_at']}), skip")
            return

        async with pool.acquire() as conn:
            week = await _gather_week(conn)
        if week["scored"] == 0:
            print("[blog] no graded matches last week; skip")
            return

        body_md = _call_qwen(
            _prompt(week, now), "dashscope/qwen-plus",
            system=SYSTEM, max_tokens=1400, temperature=0.55,
        )
        if not body_md:
            print("[blog] LLM returned empty")
            return

        excerpt = (
            f"Week {now.isocalendar().week}: {week['correct']}/{week['scored']} "
            f"correct ({week['accuracy']*100:.1f}%)."
        )

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO auto_blog_posts (slug, title, excerpt, body_md, tags, lang, model)
                VALUES ($1, $2, $3, $4, ARRAY['weekly','model']::text[], 'en', 'dashscope/qwen-plus')
                ON CONFLICT (slug) DO UPDATE SET
                  title = EXCLUDED.title,
                  excerpt = EXCLUDED.excerpt,
                  body_md = EXCLUDED.body_md,
                  generated_at = NOW()
                """,
                slug, title, excerpt, body_md,
            )
        print(f"[blog] wrote {slug} ({len(body_md)} chars)")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    asyncio.run(run(args.force))


if __name__ == "__main__":
    main()
