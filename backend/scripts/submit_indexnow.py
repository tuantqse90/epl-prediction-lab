"""Submit every indexable URL on the site to IndexNow (Bing/Yandex).

Bulk submission, runs once after first deploy + can be re-run any time
content shifts shape (new league added, etc.). Daily incremental pings
on new stories happen automatically inside generate_story.

URL set:
  - Static surfaces (pricing, stories, leagues hub, every league page,
    proof, methodology, calibration, equity-curve, table, scorers,
    last-weekend, blog, faq, faq-entries, etc.)
  - Every match with a story (NewsArticle pages — high content density)
  - Every team page (one per team in matches table)

IndexNow caps each request at 10k URLs; we batch in 1000-URL chunks.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.indexnow import submit


SITE = "https://predictor.nullshift.sh"
STATIC_PATHS = [
    "/", "/stories", "/pricing", "/proof", "/table", "/scorers",
    "/last-weekend", "/methodology", "/calibration", "/equity-curve",
    "/title-race", "/relegation", "/scorers-race", "/power-rankings",
    "/arbs", "/middles", "/kelly-explorer", "/strategies",
    "/strategies/compare", "/parlay", "/fpl", "/roi", "/roi/by-league",
    "/leagues", "/europe", "/about", "/faq", "/glossary", "/changelog",
    "/press-kit", "/blog", "/welcome",
    "/leagues/epl", "/leagues/laliga", "/leagues/seriea",
    "/leagues/bundesliga", "/leagues/ligue1",
]


async def run() -> None:
    if not os.environ.get("INDEXNOW_KEY"):
        print("[indexnow] INDEXNOW_KEY missing; skipping")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        # Match URLs that have a story = highest-value pages.
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id FROM matches
                WHERE status = 'final' AND story IS NOT NULL
                ORDER BY kickoff_time DESC
                """,
            )
        match_urls = [f"{SITE}/match/{r['id']}" for r in rows]

        # Team URLs — every team appearing in matches.
        async with pool.acquire() as conn:
            tslugs = await conn.fetch("SELECT DISTINCT slug FROM teams")
        team_urls = [f"{SITE}/teams/{r['slug']}" for r in tslugs]
    finally:
        await pool.close()

    static_urls = [f"{SITE}{p}" for p in STATIC_PATHS]
    all_urls = static_urls + match_urls + team_urls
    total = len(all_urls)
    print(f"[indexnow] submitting {total} URLs in batches of 1000")

    ok_batches = 0
    for i in range(0, total, 1000):
        chunk = all_urls[i:i + 1000]
        if submit(chunk):
            ok_batches += 1
            print(f"[indexnow] batch {i // 1000 + 1} ok ({len(chunk)} URLs)")
        else:
            print(f"[indexnow] batch {i // 1000 + 1} FAILED ({len(chunk)} URLs)")

    print(f"[indexnow] done: {ok_batches}/{(total + 999) // 1000} batches ok")


def main() -> None:
    logging.disable(logging.CRITICAL)
    asyncio.run(run())


if __name__ == "__main__":
    main()
