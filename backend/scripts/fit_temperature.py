"""Fit the 1X2 temperature-scaling factor on already-scored predictions.

Pulls every prediction whose match is final, applies a grid of candidate T
values to the stored (p_home_win, p_draw, p_away_win) triple, and reports the
T that minimizes mean log-loss. Baseline (T=1.0) is included so you can see
the lift.

Usage:
    python scripts/fit_temperature.py [--season 2025-26]
"""

from __future__ import annotations

import argparse
import asyncio
import math
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.models.poisson import temperature_scale_1x2


def _outcome(hg: int, ag: int) -> str:
    return "H" if hg > ag else ("A" if hg < ag else "D")


async def _fetch_rows(pool: asyncpg.Pool, season: str):
    async with pool.acquire() as conn:
        if season.lower() == "all":
            return await conn.fetch(
                """
                WITH latest AS (
                    SELECT DISTINCT ON (p.match_id)
                        p.match_id, p.p_home_win, p.p_draw, p.p_away_win
                    FROM predictions p
                    ORDER BY p.match_id, p.created_at DESC
                )
                SELECT m.home_goals, m.away_goals,
                       l.p_home_win, l.p_draw, l.p_away_win
                FROM matches m
                JOIN latest l ON l.match_id = m.id
                WHERE m.status = 'final' AND m.home_goals IS NOT NULL
                """,
            )
        return await conn.fetch(
            """
            WITH latest AS (
                SELECT DISTINCT ON (p.match_id)
                    p.match_id, p.p_home_win, p.p_draw, p.p_away_win
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            )
            SELECT m.home_goals, m.away_goals,
                   l.p_home_win, l.p_draw, l.p_away_win
            FROM matches m
            JOIN latest l ON l.match_id = m.id
            WHERE m.status = 'final' AND m.season = $1
              AND m.home_goals IS NOT NULL
            """,
            season,
        )


def _metrics(rows, t: float) -> tuple[float, float, float]:
    """Return (mean_log_loss, accuracy, brier) under temperature t."""
    n = 0
    ll_sum = 0.0
    correct = 0
    brier_sum = 0.0
    for r in rows:
        p_h, p_d, p_a = temperature_scale_1x2(
            float(r["p_home_win"]),
            float(r["p_draw"]),
            float(r["p_away_win"]),
            temperature=t,
        )
        outcome = _outcome(r["home_goals"], r["away_goals"])
        probs = {"H": p_h, "D": p_d, "A": p_a}
        ll_sum += -math.log(max(probs[outcome], 1e-12))
        if max(probs, key=probs.get) == outcome:
            correct += 1
        for k in "HDA":
            diff = probs[k] - (1.0 if k == outcome else 0.0)
            brier_sum += diff * diff
        n += 1
    return (ll_sum / n, correct / n, brier_sum / n) if n else (float("inf"), 0.0, 0.0)


async def run(season: str) -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        rows = await _fetch_rows(pool, season)
        if not rows:
            print(f"> no scored predictions for {season}")
            return
        print(f"> fitting on {len(rows)} scored matches in {season}")

        candidates = [round(1.0 + 0.05 * i, 2) for i in range(0, 21)]  # 1.00 .. 2.00
        print(f"{'T':>5} | {'log-loss':>9} | {'accuracy':>9} | {'brier':>6}")
        print("-" * 40)

        best = (None, float("inf"), 0.0, 0.0)
        for t in candidates:
            ll, acc, br = _metrics(rows, t)
            print(f"{t:>5.2f} | {ll:>9.4f} | {acc:>8.1%} | {br:>6.4f}")
            if ll < best[1]:
                best = (t, ll, acc, br)

        print("-" * 40)
        t, ll, acc, br = best
        ll_base, acc_base, br_base = _metrics(rows, 1.0)
        print(f"> best T = {t:.2f}  (log-loss {ll:.4f} vs {ll_base:.4f} at T=1.0, "
              f"Δ={ll_base - ll:+.4f})")
        print(f"            (accuracy {acc:.1%} vs {acc_base:.1%}, "
              f"brier {br:.4f} vs {br_base:.4f})")
    finally:
        await pool.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--season", default="2025-26")
    args = p.parse_args()
    asyncio.run(run(args.season))


if __name__ == "__main__":
    main()
