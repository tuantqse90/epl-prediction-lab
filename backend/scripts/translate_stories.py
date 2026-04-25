"""Translate every existing match story to en/th/zh/ko.

Idempotent — skips rows already in match_story_translations. Caps per
run so a fresh deploy doesn't burn the qwen-plus daily quota in one shot.

Usage:
    python scripts/translate_stories.py [--limit 30] [--days 30]
                                        [--langs en,th,zh,ko]
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
from app.llm.translate import SUPPORTED_LANGS, translate_story


async def run(days: int, limit: int, langs: list[str]) -> None:
    settings = get_settings()
    if not settings.dashscope_api_key:
        print("[translate] DASHSCOPE_API_KEY missing; skipping")
        return

    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        for lang in langs:
            if lang not in SUPPORTED_LANGS:
                print(f"[translate] skipping unsupported lang={lang}")
                continue
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT m.id FROM matches m
                    LEFT JOIN match_story_translations t
                      ON t.match_id = m.id AND t.lang = $1
                    WHERE m.story IS NOT NULL
                      AND t.id IS NULL
                      AND m.kickoff_time > NOW() - make_interval(days => $2)
                    ORDER BY m.kickoff_time DESC
                    LIMIT $3
                    """,
                    lang, days, limit,
                )
            if not rows:
                print(f"[translate] {lang}: nothing to translate")
                continue
            wrote = skipped = 0
            for r in rows:
                try:
                    text = await translate_story(pool, int(r["id"]), lang)
                except Exception as e:
                    print(f"[translate] {r['id']} {lang} error: {type(e).__name__}: {e}")
                    skipped += 1
                    continue
                if text:
                    wrote += 1
                else:
                    skipped += 1
            print(f"[translate] {lang}: wrote={wrote} skipped={skipped}")
    finally:
        await pool.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--limit", type=int, default=20,
                   help="per-language cap")
    p.add_argument("--langs", default="en,th,zh,ko")
    args = p.parse_args()
    langs = [s.strip() for s in args.langs.split(",") if s.strip()]
    logging.disable(logging.CRITICAL)
    asyncio.run(run(args.days, args.limit, langs))


if __name__ == "__main__":
    main()
