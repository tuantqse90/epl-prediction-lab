"""Generate 2k-word per-team stories for the SEO team pages.

Runs weekly (Mon 10:00 UTC, just after the digest). For each team in the
current season, pulls basic stats + recent results + top scorer + xG
trend and asks Qwen-Plus to write a grounded long-form narrative.

Writes team_narratives(team_slug, season, lang='en'). English-only for
now; translations via Block 28 (localisation depth) later.

Env:
    DASHSCOPE_API_KEY

Usage:
    python scripts/generate_team_narratives.py [--limit 200]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.llm.reasoning import _call_qwen


SEASON = "2025-26"

SYSTEM = (
    "You write tight, data-grounded football prose. 500-700 words per team. "
    "Plain English, no hype. Every claim must come from the stats in the "
    "prompt — do not invent players, match results, or narrative arcs you "
    "can't cite. Mention xG trends, finishing vs expectation, how the "
    "form looks, one or two upcoming fixtures, and the top scorer. "
    "Short paragraphs."
)


async def _team_context(conn, slug: str) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT t.slug, t.name, t.short_name
        FROM teams t WHERE t.slug = $1
        """,
        slug,
    )
    if not row:
        return None

    stats = await conn.fetchrow(
        """
        WITH per AS (
            SELECT home_team_id AS tid, 1 AS played,
                   CASE WHEN home_goals > away_goals THEN 3
                        WHEN home_goals = away_goals THEN 1 ELSE 0 END AS pts,
                   home_goals AS gf, away_goals AS ga,
                   home_xg AS xgf, away_xg AS xga,
                   CASE WHEN home_goals > away_goals THEN 'W'
                        WHEN home_goals = away_goals THEN 'D' ELSE 'L' END AS res,
                   kickoff_time
            FROM matches
            WHERE season = $1 AND status = 'final' AND home_team_id = (SELECT id FROM teams WHERE slug = $2)
              AND home_goals IS NOT NULL
            UNION ALL
            SELECT away_team_id, 1,
                   CASE WHEN away_goals > home_goals THEN 3
                        WHEN away_goals = home_goals THEN 1 ELSE 0 END,
                   away_goals, home_goals,
                   away_xg, home_xg,
                   CASE WHEN away_goals > home_goals THEN 'W'
                        WHEN away_goals = home_goals THEN 'D' ELSE 'L' END,
                   kickoff_time
            FROM matches
            WHERE season = $1 AND status = 'final' AND away_team_id = (SELECT id FROM teams WHERE slug = $2)
              AND home_goals IS NOT NULL
        )
        SELECT SUM(played)::int AS played,
               SUM(pts)::int AS points,
               SUM(gf)::int AS gf,
               SUM(ga)::int AS ga,
               SUM(xgf)::float AS xgf,
               SUM(xga)::float AS xga,
               COUNT(*) FILTER (WHERE res = 'W')::int AS wins,
               COUNT(*) FILTER (WHERE res = 'D')::int AS draws,
               COUNT(*) FILTER (WHERE res = 'L')::int AS losses
        FROM per
        """,
        SEASON, slug,
    )

    form = await conn.fetch(
        """
        WITH per AS (
            SELECT 'H' AS side, home_goals, away_goals, kickoff_time,
                   home_team_id = (SELECT id FROM teams WHERE slug = $2) AS is_us
            FROM matches WHERE season = $1 AND status = 'final' AND home_goals IS NOT NULL
              AND (home_team_id = (SELECT id FROM teams WHERE slug = $2) OR away_team_id = (SELECT id FROM teams WHERE slug = $2))
            UNION ALL
            SELECT 'A', home_goals, away_goals, kickoff_time,
                   away_team_id = (SELECT id FROM teams WHERE slug = $2)
            FROM matches WHERE season = $1 AND status = 'final' AND home_goals IS NOT NULL
              AND (home_team_id = (SELECT id FROM teams WHERE slug = $2) OR away_team_id = (SELECT id FROM teams WHERE slug = $2))
        )
        SELECT kickoff_time, side, home_goals, away_goals
        FROM per WHERE is_us
        ORDER BY kickoff_time DESC LIMIT 5
        """,
        SEASON, slug,
    )

    top_scorer = await conn.fetchrow(
        """
        SELECT player_name, goals, xg, assists
        FROM player_season_stats
        WHERE season = $1 AND team_id = (SELECT id FROM teams WHERE slug = $2)
        ORDER BY goals DESC, xg DESC
        LIMIT 1
        """,
        SEASON, slug,
    )

    upcoming = await conn.fetch(
        """
        SELECT ht.slug AS home, at.slug AS away, m.kickoff_time
        FROM matches m
        JOIN teams ht ON ht.id = m.home_team_id
        JOIN teams at ON at.id = m.away_team_id
        WHERE m.season = $1 AND m.status = 'scheduled'
          AND (m.home_team_id = (SELECT id FROM teams WHERE slug = $2) OR m.away_team_id = (SELECT id FROM teams WHERE slug = $2))
        ORDER BY m.kickoff_time ASC LIMIT 3
        """,
        SEASON, slug,
    )

    return {
        "slug": row["slug"], "name": row["name"], "short_name": row["short_name"],
        "stats": dict(stats) if stats else {},
        "form": [dict(f) for f in form],
        "top_scorer": dict(top_scorer) if top_scorer else None,
        "upcoming": [dict(u) for u in upcoming],
    }


def _prompt(ctx: dict) -> str:
    s = ctx["stats"]
    form_str = " / ".join(f"{f['home_goals']}-{f['away_goals']} ({f['side']})" for f in ctx["form"])
    ts = ctx["top_scorer"]
    ts_str = (
        f"{ts['player_name']}: {ts['goals']} goals, {ts['xg']:.1f} xG, {ts['assists']} assists"
        if ts else "no clear top scorer"
    )
    up_str = "; ".join(f"{u['home']} vs {u['away']} on {str(u['kickoff_time'])[:10]}" for u in ctx["upcoming"][:3])
    return (
        f"Team: {ctx['name']}\n"
        f"Season: 2025-26\n\n"
        f"Stats: {s.get('played', 0)} matches, {s.get('points', 0)} pts "
        f"({s.get('wins', 0)}W-{s.get('draws', 0)}D-{s.get('losses', 0)}L)\n"
        f"Goals: {s.get('gf', 0)} scored, {s.get('ga', 0)} conceded\n"
        f"xG: {s.get('xgf', 0) or 0:.1f} for, {s.get('xga', 0) or 0:.1f} against\n"
        f"Last 5: {form_str or 'no recent form'}\n"
        f"Top scorer: {ts_str}\n"
        f"Upcoming: {up_str or 'no scheduled fixtures'}\n\n"
        f"Write a 500-700-word analytical piece describing this team's "
        f"2025-26 season so far. Cover: how xG compares to actual goals "
        f"(finishing luck), form direction, top-scorer sustainability, "
        f"what the upcoming slate looks like. No invented facts."
    )


async def run(limit: int) -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            slugs = [r["slug"] for r in await conn.fetch(
                """
                SELECT DISTINCT t.slug
                FROM teams t
                JOIN matches m ON m.home_team_id = t.id OR m.away_team_id = t.id
                WHERE m.season = $1
                """,
                SEASON,
            )]
        print(f"[narratives] {len(slugs)} teams to process")

        generated = 0
        for slug in slugs[:limit]:
            # Skip if we generated <7 days ago
            async with pool.acquire() as conn:
                existing = await conn.fetchrow(
                    """
                    SELECT generated_at FROM team_narratives
                    WHERE team_slug = $1 AND season = $2 AND lang = 'en'
                    """,
                    slug, SEASON,
                )
            if existing:
                age_days = (
                    (existing["generated_at"].timestamp() - existing["generated_at"].timestamp()) / 86400
                )
                # Actually compute vs now
                from datetime import datetime, timezone
                age_days = (datetime.now(timezone.utc) - existing["generated_at"]).total_seconds() / 86400
                if age_days < 6:
                    print(f"[narratives] {slug}: fresh ({age_days:.1f}d), skip")
                    continue

            async with pool.acquire() as conn:
                ctx = await _team_context(conn, slug)
            if not ctx or not ctx["stats"].get("played"):
                continue

            try:
                story = _call_qwen(
                    _prompt(ctx), "dashscope/qwen-plus",
                    system=SYSTEM, max_tokens=1400, temperature=0.5,
                )
            except Exception as e:
                print(f"[narratives] {slug} LLM failed: {type(e).__name__}: {e}")
                continue

            if not story:
                continue

            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO team_narratives (team_slug, season, lang, story, model)
                    VALUES ($1, $2, 'en', $3, 'dashscope/qwen-plus')
                    ON CONFLICT (team_slug, season, lang) DO UPDATE SET
                      story = EXCLUDED.story,
                      model = EXCLUDED.model,
                      generated_at = NOW()
                    """,
                    slug, SEASON, story,
                )
            generated += 1
            print(f"[narratives] {slug}: wrote {len(story)} chars")

        print(f"[narratives] done. generated={generated}")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=200)
    args = p.parse_args()
    asyncio.run(run(args.limit))


if __name__ == "__main__":
    main()
