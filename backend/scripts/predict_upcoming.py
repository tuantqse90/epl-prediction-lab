"""Run `predict_all_upcoming` for every scheduled match in a window.

Usage:
    python scripts/predict_upcoming.py [--horizon-days 14] [--with-reasoning]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.llm.reasoning import explain_prediction
from app.predict.service import predict_all_upcoming


async def _status_summary(pool: asyncpg.Pool) -> None:
    rows = await pool.fetch(
        "SELECT status, COUNT(*) AS n FROM matches GROUP BY status ORDER BY status"
    )
    for r in rows:
        print(f"  {r['status']:>10}: {r['n']}")
    upc = await pool.fetchval(
        "SELECT COUNT(*) FROM matches "
        "WHERE status = 'scheduled' AND kickoff_time > NOW()"
    )
    print(f"  upcoming (future kickoff): {upc}")


async def run(horizon_days: int, with_reasoning: bool) -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=4)
    try:
        print("> match status snapshot")
        await _status_summary(pool)

        print(
            f"> running predict_all_upcoming("
            f"rho={settings.default_rho}, last_n={settings.default_last_n}, "
            f"T={settings.default_temperature}, horizon={horizon_days})"
        )
        ids = await predict_all_upcoming(
            pool,
            rho=settings.default_rho,
            model_version=settings.model_version,
            horizon_days=horizon_days,
            last_n=settings.default_last_n,
            temperature=settings.default_temperature,
        )
        print(f"> wrote {len(ids)} predictions")

        if with_reasoning and settings.dashscope_api_key:
            print("> generating reasoning …")
            rows = await pool.fetch(
                "SELECT DISTINCT match_id FROM predictions "
                "WHERE id = ANY($1::int[])",
                ids,
            )
            ok = 0
            for r in rows:
                try:
                    if await explain_prediction(pool, r["match_id"]):
                        ok += 1
                except Exception as e:
                    print(f"  match {r['match_id']}: {e}")
            print(f"> reasoning attached to {ok}/{len(rows)} matches")
    finally:
        await pool.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--horizon-days", type=int, default=14)
    p.add_argument("--with-reasoning", action="store_true")
    args = p.parse_args()
    asyncio.run(run(args.horizon_days, args.with_reasoning))


if __name__ == "__main__":
    main()
