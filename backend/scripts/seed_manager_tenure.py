"""One-shot: seed current managers for top-20 clubs across 5 leagues.

Starting dates are rough (month-level). Data becomes useful when a
manager change happens — the bounce endpoint then flags a short tenure.

Usage:
    python scripts/seed_manager_tenure.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings


# (team_slug, manager_name, started_at)
_SEED: list[tuple[str, str, str]] = [
    # EPL
    ("arsenal",           "Mikel Arteta",          "2019-12-20"),
    ("manchester-city",   "Pep Guardiola",         "2016-07-01"),
    ("manchester-united", "Ruben Amorim",          "2024-11-01"),
    ("liverpool",         "Arne Slot",             "2024-07-01"),
    ("chelsea",           "Enzo Maresca",          "2024-07-01"),
    ("tottenham",         "Thomas Frank",          "2025-06-10"),
    ("aston-villa",       "Unai Emery",            "2022-10-31"),
    ("newcastle-united",  "Eddie Howe",            "2021-11-08"),
    # La Liga
    ("real-madrid",       "Xabi Alonso",           "2025-06-01"),
    ("barcelona",         "Hansi Flick",           "2024-05-29"),
    ("atletico-madrid",   "Diego Simeone",         "2011-12-23"),
    ("athletic-club",     "Ernesto Valverde",      "2022-07-01"),
    # Serie A
    ("inter",             "Cristian Chivu",        "2025-06-01"),
    ("ac-milan",          "Massimiliano Allegri",  "2025-05-30"),
    ("juventus",          "Igor Tudor",            "2025-03-23"),
    ("napoli",            "Antonio Conte",         "2024-06-05"),
    # Bundesliga
    ("bayern-munich",     "Vincent Kompany",       "2024-05-29"),
    ("borussia-dortmund", "Niko Kovač",            "2025-02-02"),
    ("bayer-leverkusen",  "Xabi Alonso",           "2022-10-05"),
    # Ligue 1
    ("paris-saint-germain", "Luis Enrique",        "2023-07-05"),
    ("marseille",         "Roberto De Zerbi",      "2024-06-29"),
    ("monaco",            "Adi Hütter",            "2023-06-01"),
]


async def run() -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        seeded = 0
        async with pool.acquire() as conn:
            for slug, name, started in _SEED:
                # Skip if a current tenure already exists.
                has = await conn.fetchval(
                    "SELECT 1 FROM manager_tenure WHERE team_slug = $1 AND ended_at IS NULL",
                    slug,
                )
                if has:
                    continue
                await conn.execute(
                    """
                    INSERT INTO manager_tenure (team_slug, manager_name, started_at)
                    VALUES ($1, $2, $3::date)
                    """,
                    slug, name, started,
                )
                seeded += 1
                print(f"[manager-seed] {slug:22} {name:30} since {started}")
        print(f"[manager-seed] seeded {seeded} current tenures (skipped existing)")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    asyncio.run(run())


if __name__ == "__main__":
    main()
