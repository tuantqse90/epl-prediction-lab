"""Walk-forward log-loss comparison for Block 21 wiring.

For a given season, re-scores every finished match under three configs:

    static      ρ = -0.15, no derby bump
    dynamic     ρ looked up per (league, season, quarter)
    dynamic+d   dynamic ρ + λ × 1.03 on recognized derby fixtures

Uses stored home_xg / away_xg as the Poisson rates (Understat output).
We skip the feature-pipeline regeneration because we only want to measure
the ρ + derby effect in isolation; all other λ inputs are held constant.

Metrics: mean log-loss + Brier on the 3-way outcome.

Usage:
    python scripts/backtest_block21.py --season 2024-25
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
from app.models.derbies import derby_tag
from app.models.dynamic_rho import DEFAULT_RHO, quarter_for_matchweek
from app.models.poisson import poisson_score_matrix, apply_dixon_coles, collapse_1x2


def _matrix_3way(lam_h: float, lam_a: float, rho: float, k: int = 10) -> tuple[float, float, float]:
    mat = poisson_score_matrix(lam_h, lam_a, max_goals=k)
    mat = apply_dixon_coles(mat, lam_h, lam_a, rho=rho)
    p_h, p_d, p_a = collapse_1x2(mat)
    total = p_h + p_d + p_a
    if total <= 0:
        return (1 / 3, 1 / 3, 1 / 3)
    return (p_h / total, p_d / total, p_a / total)


def _log_loss_3way(
    p: tuple[float, float, float], outcome: str, eps: float = 1e-6,
) -> float:
    p_h, p_d, p_a = p
    p_h = max(eps, min(1 - eps, p_h))
    p_d = max(eps, min(1 - eps, p_d))
    p_a = max(eps, min(1 - eps, p_a))
    target = {"H": p_h, "D": p_d, "A": p_a}[outcome]
    return -math.log(max(eps, target))


def _brier_3way(
    p: tuple[float, float, float], outcome: str,
) -> float:
    p_h, p_d, p_a = p
    y_h = 1.0 if outcome == "H" else 0.0
    y_d = 1.0 if outcome == "D" else 0.0
    y_a = 1.0 if outcome == "A" else 0.0
    return (p_h - y_h) ** 2 + (p_d - y_d) ** 2 + (p_a - y_a) ** 2


async def run(season: str) -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            matches = await conn.fetch(
                """
                SELECT m.id, m.league_code, m.matchweek, m.home_xg, m.away_xg,
                       m.home_goals, m.away_goals,
                       ht.slug AS home_slug, at.slug AS away_slug
                FROM matches m
                JOIN teams ht ON ht.id = m.home_team_id
                JOIN teams at ON at.id = m.away_team_id
                WHERE m.season = $1
                  AND m.status = 'final'
                  AND m.home_goals IS NOT NULL
                  AND m.home_xg IS NOT NULL AND m.away_xg IS NOT NULL
                """,
                season,
            )
            # Pre-load the full rho_calibration once — cheap.
            rho_rows = await conn.fetch(
                "SELECT league_code, season, quarter, rho FROM rho_calibration WHERE season = $1",
                season,
            )
        rho_map: dict[tuple[str, int], float] = {}
        for r in rho_rows:
            rho_map[(r["league_code"], int(r["quarter"]))] = float(r["rho"])

        configs = {
            "static":     {"use_dyn_rho": False, "use_derby": False},
            "dynamic":    {"use_dyn_rho": True,  "use_derby": False},
            "dynamic+d":  {"use_dyn_rho": True,  "use_derby": True},
        }
        scores: dict[str, dict[str, float]] = {
            k: {"ll": 0.0, "brier": 0.0, "n": 0} for k in configs
        }

        for m in matches:
            hg, ag = int(m["home_goals"]), int(m["away_goals"])
            outcome = "H" if hg > ag else "A" if hg < ag else "D"
            lam_h = float(m["home_xg"]) or 0.0
            lam_a = float(m["away_xg"]) or 0.0
            if lam_h <= 0 or lam_a <= 0:
                continue
            q = quarter_for_matchweek(m.get("matchweek") or 1) if isinstance(m, dict) else quarter_for_matchweek(m["matchweek"])
            dyn_rho = rho_map.get((m["league_code"], q), DEFAULT_RHO)
            is_derby = derby_tag(m["home_slug"], m["away_slug"]) is not None

            for name, cfg in configs.items():
                rho = dyn_rho if cfg["use_dyn_rho"] else DEFAULT_RHO
                lam_h_c, lam_a_c = lam_h, lam_a
                if cfg["use_derby"] and is_derby:
                    lam_h_c *= 1.03
                    lam_a_c *= 1.03
                p = _matrix_3way(lam_h_c, lam_a_c, rho=rho)
                scores[name]["ll"] += _log_loss_3way(p, outcome)
                scores[name]["brier"] += _brier_3way(p, outcome)
                scores[name]["n"] += 1

        print(f"\nSeason: {season}")
        print(f"{'config':<12} {'n':>5} {'log-loss':>10} {'Brier':>10}")
        print("-" * 40)
        for name, s in scores.items():
            n = s["n"]
            ll = s["ll"] / n if n else 0.0
            br = s["brier"] / n if n else 0.0
            print(f"{name:<12} {n:>5} {ll:>10.5f} {br:>10.5f}")

        base_ll = scores["static"]["ll"] / scores["static"]["n"]
        base_br = scores["static"]["brier"] / scores["static"]["n"]
        print()
        for name in ("dynamic", "dynamic+d"):
            n = scores[name]["n"]
            ll = scores[name]["ll"] / n
            br = scores[name]["brier"] / n
            print(f"Δ {name:<9} vs static:  log-loss {ll - base_ll:+.5f}  Brier {br - base_br:+.5f}")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--season", default="2024-25")
    args = p.parse_args()
    asyncio.run(run(args.season))


if __name__ == "__main__":
    main()
