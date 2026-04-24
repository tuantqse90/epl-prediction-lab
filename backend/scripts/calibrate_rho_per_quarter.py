"""Fit Dixon-Coles ρ per (league, season, quarter) and populate
rho_calibration table. Cheap grid-search; look at walk-forward log-loss.

Matchweek→quarter mapping matches app/models/dynamic_rho.quarter_for_matchweek.

Usage:
    python scripts/calibrate_rho_per_quarter.py --season 2024-25 --league ENG-Premier League
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import math
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings


CANDIDATES = [-0.25, -0.20, -0.15, -0.10, -0.05, 0.00, 0.05]


def _dc_correction(lam_h: float, lam_a: float, hg: int, ag: int, rho: float) -> float:
    if hg == 0 and ag == 0:
        return max(1e-6, 1.0 - lam_h * lam_a * rho)
    if hg == 0 and ag == 1:
        return max(1e-6, 1.0 + lam_h * rho)
    if hg == 1 and ag == 0:
        return max(1e-6, 1.0 + lam_a * rho)
    if hg == 1 and ag == 1:
        return max(1e-6, 1.0 - rho)
    return 1.0


def _poisson(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 1e-9
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _match_ll(lam_h: float, lam_a: float, hg: int, ag: int, rho: float) -> float:
    p = _poisson(hg, lam_h) * _poisson(ag, lam_a) * _dc_correction(lam_h, lam_a, hg, ag, rho)
    return -math.log(max(1e-9, p))


async def _fit(pool, league: str, season: str) -> dict[int, tuple[float, float, int]]:
    """Returns {quarter: (rho, mean_log_loss, n_matches)}."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.id, m.matchweek, m.home_xg, m.away_xg,
                   m.home_goals, m.away_goals
            FROM matches m
            WHERE m.league_code = $1 AND m.season = $2
              AND m.status = 'final' AND m.home_goals IS NOT NULL
              AND m.home_xg IS NOT NULL AND m.away_xg IS NOT NULL
            """,
            league, season,
        )
    by_q: dict[int, list] = {1: [], 2: [], 3: [], 4: []}
    for r in rows:
        mw = r["matchweek"] or 1
        q = 1 if mw <= 10 else 2 if mw <= 20 else 3 if mw <= 30 else 4
        by_q[q].append(r)
    out: dict[int, tuple[float, float, int]] = {}
    for q, matches in by_q.items():
        if len(matches) < 20:
            continue
        best = (0.0, float("inf"))
        for rho in CANDIDATES:
            ll = 0.0
            for r in matches:
                ll += _match_ll(
                    float(r["home_xg"]), float(r["away_xg"]),
                    int(r["home_goals"]), int(r["away_goals"]), rho,
                )
            mean_ll = ll / len(matches)
            if mean_ll < best[1]:
                best = (rho, mean_ll)
        out[q] = (best[0], best[1], len(matches))
    return out


async def run(season: str, league: str | None) -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        # Leagues to process.
        if league:
            leagues = [league]
        else:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT DISTINCT league_code FROM matches WHERE season = $1 AND status = 'final' AND league_code IS NOT NULL",
                    season,
                )
            leagues = [r["league_code"] for r in rows]

        for lg in leagues:
            fit = await _fit(pool, lg, season)
            if not fit:
                print(f"[rho] {lg}/{season}: not enough data")
                continue
            async with pool.acquire() as conn:
                for q, (rho, ll, n) in fit.items():
                    await conn.execute(
                        """
                        INSERT INTO rho_calibration (league_code, season, quarter, rho, log_loss, n_matches)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (league_code, season, quarter)
                        DO UPDATE SET rho = EXCLUDED.rho, log_loss = EXCLUDED.log_loss,
                                      n_matches = EXCLUDED.n_matches, updated_at = NOW()
                        """,
                        lg, season, q, rho, ll, n,
                    )
                    print(f"[rho] {lg:22} {season} Q{q}  ρ={rho:+.2f}  ll={ll:.4f}  n={n}")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--season", default="2024-25")
    p.add_argument("--league", default=None)
    args = p.parse_args()
    asyncio.run(run(args.season, args.league))


if __name__ == "__main__":
    main()
