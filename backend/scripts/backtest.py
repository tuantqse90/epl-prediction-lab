"""Walk-forward backtest: predict every final match using only prior matches.

The production predict flow only writes predictions for upcoming fixtures.
This script backfills predictions for already-played matches so we can measure
the model's accuracy on known outcomes. Idempotent: skips matches that already
have a prediction row.

Usage:
    python scripts/backtest.py [--season 2025-26]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.predict.service import predict_and_persist


async def run(season: str) -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=4)
    try:
        final_ids = await pool.fetch(
            """
            SELECT m.id
            FROM matches m
            WHERE m.status = 'final'
              AND m.season = $1
              AND m.home_goals IS NOT NULL
              AND m.home_xg IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM predictions p
                  WHERE p.match_id = m.id
                    AND p.model_version LIKE $2 || '%'
              )
            ORDER BY m.kickoff_time ASC
            """,
            season, f"{settings.model_version}:",
        )
        print(
            f"> {len(final_ids)} finals in {season} without a {settings.model_version} "
            f"prediction — backfilling"
        )

        made = 0
        for i, r in enumerate(final_ids, start=1):
            try:
                await predict_and_persist(
                    pool,
                    r["id"],
                    rho=settings.default_rho,
                    model_version=f"{settings.model_version}:backtest",
                    last_n=settings.default_last_n,
                    temperature=settings.default_temperature,
                )
                made += 1
            except Exception as e:
                print(f"  match {r['id']}: {type(e).__name__}: {e}")
            if i % 50 == 0:
                print(f"  ...{i}/{len(final_ids)}")
        print(f"> wrote {made} predictions")
    finally:
        await pool.close()


def main() -> None:
    import logging

    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--season", default="2025-26")
    args = p.parse_args()
    asyncio.run(run(args.season))


if __name__ == "__main__":
    main()
