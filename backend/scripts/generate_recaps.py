"""Fill `matches.recap` for finals in the last N days that don't yet have one.

Run daily — cheap (Qwen-Turbo ~$0.003/call), idempotent.

Usage:
    python scripts/generate_recaps.py [--days 7] [--limit 80]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.llm.recap import generate_recap


async def run(days: int, limit: int) -> None:
    settings = get_settings()
    if not settings.dashscope_api_key:
        print("[recap] DASHSCOPE_API_KEY missing; skipping")
        return

    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT m.id
                FROM matches m
                WHERE m.status = 'final'
                  AND m.home_goals IS NOT NULL
                  AND m.recap IS NULL
                  AND m.kickoff_time >= NOW() - ($1 || ' days')::INTERVAL
                  AND EXISTS (SELECT 1 FROM predictions p WHERE p.match_id = m.id)
                ORDER BY m.kickoff_time DESC
                LIMIT $2
                """,
                str(days),
                limit,
            )
        print(f"[recap] {len(rows)} finals need recap in last {days}d")
        ok = 0
        for r in rows:
            try:
                text = await generate_recap(pool, r["id"])
                if text:
                    ok += 1
            except Exception as e:
                print(f"  match {r['id']}: {e}")
        print(f"[recap] generated {ok}/{len(rows)}")
    finally:
        await pool.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--limit", type=int, default=80)
    args = p.parse_args()
    asyncio.run(run(args.days, args.limit))


if __name__ == "__main__":
    main()
