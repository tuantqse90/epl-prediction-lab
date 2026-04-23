"""Monte Carlo title-race simulator.

Given:
    - current standings (team → {played, points, gd, gf})
    - remaining fixtures (home, away, lambda_h, lambda_a)
    - n_simulations + seed

Draws goals from independent Poisson(λ) per side, applies 3/1/0 points
scheme, then ranks teams by (points, gd, gf). Returns per-team finish
distribution: P(champions), P(top-four), P(relegate), mean_points,
P(position=k) histogram.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict


def _sample_poisson(lam: float, rng: random.Random) -> int:
    """Knuth's 1969 method — exact Poisson draw. Adequate for λ ≤ 10 which
    covers football comfortably (fixtures average λ ≈ 1.4)."""
    if lam <= 0:
        return 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p < L:
            return k - 1


def _simulate_match(lambda_h: float, lambda_a: float, rng: random.Random) -> tuple[int, int]:
    return _sample_poisson(lambda_h, rng), _sample_poisson(lambda_a, rng)


def simulate_title_race(
    *,
    standings: dict[str, dict],
    remaining: list[dict],
    n_simulations: int = 10_000,
    seed: int | None = None,
    relegation_count: int = 3,
    top_count: int = 4,
) -> dict[str, dict]:
    """Run N simulations and return per-team finish distribution.

    Per team we report:
      p_champions — final rank 1
      p_top_four  — final rank ≤ top_count
      p_relegate  — final rank ≥ (n_teams - relegation_count + 1)
      mean_points — average end-of-season points
      position_histogram — list[float] length n_teams, position_histogram[k-1]
                           = P(finish at position k)
    """
    rng = random.Random(seed)
    teams = list(standings.keys())
    n_teams = len(teams)
    # Counters
    champ_count = defaultdict(int)
    top_count_count = defaultdict(int)
    releg_count = defaultdict(int)
    points_total = defaultdict(float)
    position_hist = {t: [0] * n_teams for t in teams}

    for _ in range(max(1, n_simulations)):
        # Start from current standings snapshot
        sim_points = {t: standings[t]["points"] for t in teams}
        sim_gd = {t: standings[t]["gd"] for t in teams}
        sim_gf = {t: standings[t]["gf"] for t in teams}

        # Play remaining
        for fx in remaining:
            h, a = fx["home"], fx["away"]
            hg, ag = _simulate_match(fx["lambda_h"], fx["lambda_a"], rng)
            sim_gf[h] = sim_gf.get(h, 0) + hg
            sim_gf[a] = sim_gf.get(a, 0) + ag
            sim_gd[h] = sim_gd.get(h, 0) + (hg - ag)
            sim_gd[a] = sim_gd.get(a, 0) + (ag - hg)
            if hg > ag:
                sim_points[h] += 3
            elif hg < ag:
                sim_points[a] += 3
            else:
                sim_points[h] += 1
                sim_points[a] += 1

        # Rank: points desc, then gd desc, then gf desc
        sorted_teams = sorted(
            teams,
            key=lambda t: (sim_points[t], sim_gd[t], sim_gf[t]),
            reverse=True,
        )
        for rank_idx, t in enumerate(sorted_teams):
            position_hist[t][rank_idx] += 1
            if rank_idx == 0:
                champ_count[t] += 1
            if rank_idx < top_count:
                top_count_count[t] += 1
            if rank_idx >= n_teams - relegation_count:
                releg_count[t] += 1
            points_total[t] += sim_points[t]

    N = n_simulations
    return {
        t: {
            "p_champions": champ_count[t] / N,
            "p_top_four": top_count_count[t] / N,
            "p_relegate": releg_count[t] / N,
            "mean_points": points_total[t] / N,
            "position_histogram": [c / N for c in position_hist[t]],
        }
        for t in teams
    }
