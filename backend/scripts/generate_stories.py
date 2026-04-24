"""Fill `matches.story` for finals in the last N days that don't yet have one.

Run daily — Qwen-Plus call is ~5s / ~$0.02 per match. Idempotent via the
`story IS NULL` guard.

Usage:
    python scripts/generate_stories.py [--days 30] [--limit 40]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.llm.story import generate_story


async def run(days: int, limit: int) -> None:
    settings = get_settings()
    if not settings.dashscope_api_key:
        print("[story] DASHSCOPE_API_KEY missing; skipping")
        return

    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT m.id FROM matches m
                WHERE m.status = 'final'
                  AND m.home_goals IS NOT NULL
                  AND m.recap IS NOT NULL
                  AND m.story IS NULL
                  AND m.kickoff_time > NOW() - make_interval(days => $1)
                  AND EXISTS (SELECT 1 FROM predictions p WHERE p.match_id = m.id)
                ORDER BY m.kickoff_time DESC
                LIMIT $2
                """,
                days, limit,
            )
        wrote = skipped = 0
        for r in rows:
            try:
                text = await generate_story(pool, int(r["id"]))
            except Exception as e:
                print(f"[story] {r['id']} error: {type(e).__name__}: {e}")
                skipped += 1
                continue
            if text:
                wrote += 1
                print(f"[story] match {r['id']}: {len(text)} chars")
            else:
                skipped += 1
        print(f"[story] wrote={wrote} skipped={skipped}")
    finally:
        await pool.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--limit", type=int, default=40)
    args = p.parse_args()
    asyncio.run(run(args.days, args.limit))


if __name__ == "__main__":
    main()
