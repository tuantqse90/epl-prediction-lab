"""Half-time markets from the Poisson engine.

Splits the full-match λ using the standard 45/55 empirical split — the
first half averages ~45% of the total goals, the second ~55%. From there
every half-time market is a linear combination of a scoreline matrix.

Exposed markets:
    ht_winner_probs   — (p_home_lead, p_draw, p_away_lead) at the break
    halftime_correct_score_top  — top-N most likely HT scorelines
    htft_grid         — 3×3 of HT outcome × FT outcome probabilities
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.models.poisson import (
    apply_dixon_coles,
    collapse_1x2,
    poisson_score_matrix,
    top_scorelines,
)


FIRST_HALF_SHARE = 0.45


@dataclass(frozen=True)
class HTProbs:
    p_home_lead: float
    p_draw: float
    p_away_lead: float


@dataclass(frozen=True)
class HTFTGrid:
    """Nested HT×FT outcome probabilities. Keys: ("H"|"D"|"A", "H"|"D"|"A")."""
    cells: dict[tuple[str, str], float]


def _first_half_lambdas(lam_home: float, lam_away: float) -> tuple[float, float]:
    return lam_home * FIRST_HALF_SHARE, lam_away * FIRST_HALF_SHARE


def _second_half_lambdas(lam_home: float, lam_away: float) -> tuple[float, float]:
    return lam_home * (1.0 - FIRST_HALF_SHARE), lam_away * (1.0 - FIRST_HALF_SHARE)


def ht_winner_probs(
    lam_home: float, lam_away: float, rho: float = -0.15, max_goals: int = 5,
) -> HTProbs:
    lh, la = _first_half_lambdas(lam_home, lam_away)
    base = poisson_score_matrix(lh, la, max_goals=max_goals)
    adj = apply_dixon_coles(base, lh, la, rho)
    p_h, p_d, p_a = collapse_1x2(adj)
    return HTProbs(p_home_lead=p_h, p_draw=p_d, p_away_lead=p_a)


def halftime_correct_score_top(
    lam_home: float, lam_away: float, n: int = 3, rho: float = -0.15, max_goals: int = 4,
) -> list[tuple[int, int, float]]:
    lh, la = _first_half_lambdas(lam_home, lam_away)
    base = poisson_score_matrix(lh, la, max_goals=max_goals)
    adj = apply_dixon_coles(base, lh, la, rho)
    return top_scorelines(adj, n=n)


def _1x2_from_matrix(matrix: np.ndarray) -> tuple[float, float, float]:
    return collapse_1x2(matrix)


def htft_grid(
    lam_home: float, lam_away: float, rho: float = -0.15, max_goals: int = 5,
) -> HTFTGrid:
    """Probability of each (HT_outcome, FT_outcome) pair.

    Models H1 and H2 as independent half-match Poisson draws, which is the
    industry-standard approximation — actual HT results do correlate with
    FT behavior (momentum, game state), but the correction is small and
    book-maker HT/FT markets use the same assumption.
    """
    h1_h, h1_a = _first_half_lambdas(lam_home, lam_away)
    h2_h, h2_a = _second_half_lambdas(lam_home, lam_away)

    h1_matrix = apply_dixon_coles(
        poisson_score_matrix(h1_h, h1_a, max_goals=max_goals), h1_h, h1_a, rho,
    )
    h2_matrix = apply_dixon_coles(
        poisson_score_matrix(h2_h, h2_a, max_goals=max_goals), h2_h, h2_a, rho,
    )

    # Enumerate every (h1_home, h1_away, h2_home, h2_away) combination and
    # classify its HT + FT outcomes, accumulating probability mass.
    grid: dict[tuple[str, str], float] = {
        (ht, ft): 0.0 for ht in ("H", "D", "A") for ft in ("H", "D", "A")
    }

    rows, cols = h1_matrix.shape
    for i1 in range(rows):
        for j1 in range(cols):
            p1 = float(h1_matrix[i1, j1])
            if p1 == 0.0:
                continue
            ht = "H" if i1 > j1 else ("A" if j1 > i1 else "D")
            for i2 in range(rows):
                for j2 in range(cols):
                    p2 = float(h2_matrix[i2, j2])
                    if p2 == 0.0:
                        continue
                    fh, fa = i1 + i2, j1 + j2
                    ft = "H" if fh > fa else ("A" if fa > fh else "D")
                    grid[(ht, ft)] += p1 * p2

    total = sum(grid.values())
    if total > 0:
        grid = {k: v / total for k, v in grid.items()}
    return HTFTGrid(cells=grid)
