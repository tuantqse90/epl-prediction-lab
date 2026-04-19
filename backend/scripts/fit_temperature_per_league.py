"""Fit the 1X2 temperature scalar separately for each league.

Draw rates differ materially across leagues (Serie A ≈ 25%, Premier ≈ 22%,
Ligue 1 ≈ 27%), so a single global T underfits some and overfits others.
This script groups scored predictions by `league_code` and picks the T that
minimizes log-loss per league on a fine grid.

Emits a copy-pastable dict. Paste into app/predict/service.py to activate.

Usage:
    python scripts/fit_temperature_per_league.py
    python scripts/fit_temperature_per_league.py --seasons 2024-25,2025-26
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


async def _fetch_rows(pool: asyncpg.Pool, seasons: list[str]):
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            WITH latest AS (
                SELECT DISTINCT ON (p.match_id)
                    p.match_id, p.p_home_win, p.p_draw, p.p_away_win
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            )
            SELECT m.league_code,
                   m.home_goals, m.away_goals,
                   l.p_home_win, l.p_draw, l.p_away_win
            FROM matches m
            JOIN latest l ON l.match_id = m.id
            WHERE m.status = 'final' AND m.home_goals IS NOT NULL
              AND m.season = ANY($1::text[])
            """,
            seasons,
        )


def _mean_log_loss(rows, t: float) -> tuple[float, int]:
    n = 0
    ll_sum = 0.0
    for r in rows:
        p_h, p_d, p_a = temperature_scale_1x2(
            float(r["p_home_win"]),
            float(r["p_draw"]),
            float(r["p_away_win"]),
            temperature=t,
        )
        probs = {"H": p_h, "D": p_d, "A": p_a}
        outcome = _outcome(r["home_goals"], r["away_goals"])
        ll_sum += -math.log(max(probs[outcome], 1e-12))
        n += 1
    return (ll_sum / n if n else float("inf"), n)


def _fit(rows) -> tuple[float, float, int]:
    """Grid-search over T ∈ [1.00, 2.00] step 0.05, then refine ±0.05 step 0.01."""
    if not rows:
        return (1.0, float("inf"), 0)
    coarse = [round(1.0 + 0.05 * i, 2) for i in range(0, 21)]
    best_t = 1.0
    best_ll = float("inf")
    for t in coarse:
        ll, _ = _mean_log_loss(rows, t)
        if ll < best_ll:
            best_ll = ll
            best_t = t
    # refine around best
    fine = [round(best_t + 0.01 * i, 3) for i in range(-5, 6)]
    for t in fine:
        if t < 1.0:
            continue
        ll, _ = _mean_log_loss(rows, t)
        if ll < best_ll:
            best_ll = ll
            best_t = round(t, 3)
    return (best_t, best_ll, len(rows))


async def run(seasons: list[str]) -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        rows = await _fetch_rows(pool, seasons)
    finally:
        await pool.close()

    by_league: dict[str | None, list] = {}
    for r in rows:
        by_league.setdefault(r["league_code"], []).append(r)

    print(f"> scored predictions: {len(rows)} across {len(by_league)} leagues")
    print(f"> seasons: {seasons}")
    print()
    print(f"{'league':<22}  {'n':>5}  {'T*':>6}  {'ll@T*':>8}  {'ll@1.35':>8}  {'Δ':>7}")
    print("-" * 66)

    emits: dict[str, float] = {}
    ll_current_sum = 0.0
    ll_optimal_sum = 0.0
    total_n = 0
    for code, grp in sorted(by_league.items(), key=lambda kv: -len(kv[1])):
        t, ll_best, n = _fit(grp)
        ll_current, _ = _mean_log_loss(grp, 1.35)
        delta = ll_current - ll_best
        print(
            f"{str(code or 'NULL'):<22}  {n:>5}  {t:>6.3f}  "
            f"{ll_best:>8.4f}  {ll_current:>8.4f}  {delta:>+7.4f}"
        )
        if code and n >= 50:
            emits[code] = t
        ll_current_sum += ll_current * n
        ll_optimal_sum += ll_best * n
        total_n += n

    print("-" * 66)
    print(
        f"overall weighted log-loss: T=1.35 → {ll_current_sum / total_n:.4f}  · "
        f"per-league → {ll_optimal_sum / total_n:.4f}  · "
        f"Δ {ll_current_sum / total_n - ll_optimal_sum / total_n:+.4f}"
    )

    print()
    print("# --- Copy-paste into app/predict/service.py ---")
    print("LEAGUE_TEMPERATURES: dict[str, float] = {")
    for code in sorted(emits):
        print(f'    "{code}": {emits[code]},')
    print("}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seasons", default="2024-25,2025-26")
    args = p.parse_args()
    seasons = [s.strip() for s in args.seasons.split(",") if s.strip()]
    asyncio.run(run(seasons))


if __name__ == "__main__":
    main()
