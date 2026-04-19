"""Dixon-Coles Poisson match prediction engine.

The model assumes goals for each side are Poisson-distributed with rates
(lambda_home, lambda_away) derived from team strengths, with a small correction
(Dixon-Coles) applied to the four low-scoring cells to match empirical data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import poisson


@dataclass(frozen=True)
class MatchPrediction:
    p_home_win: float
    p_draw: float
    p_away_win: float
    expected_home_goals: float
    expected_away_goals: float
    top_scorelines: list[tuple[int, int, float]]


def poisson_score_matrix(
    lam_home: float,
    lam_away: float,
    max_goals: int = 5,
) -> np.ndarray:
    """Return (max_goals+1, max_goals+1) matrix where M[i, j] = P(home=i, away=j).

    Independence is assumed (Dixon-Coles correction is applied separately).
    """
    if lam_home <= 0 or lam_away <= 0:
        raise ValueError("lambdas must be strictly positive")

    home_pmf = poisson.pmf(np.arange(max_goals + 1), lam_home)
    away_pmf = poisson.pmf(np.arange(max_goals + 1), lam_away)
    return np.outer(home_pmf, away_pmf)


def dixon_coles_tau(
    home_goals: int,
    away_goals: int,
    lam_home: float,
    lam_away: float,
    rho: float,
) -> float:
    """Dixon-Coles (1997) correction factor for the four low-scoring cells.

    Returns 1.0 for any (h, a) outside {(0,0), (0,1), (1,0), (1,1)}.
    """
    if home_goals == 0 and away_goals == 0:
        return 1.0 - lam_home * lam_away * rho
    if home_goals == 0 and away_goals == 1:
        return 1.0 + lam_home * rho
    if home_goals == 1 and away_goals == 0:
        return 1.0 + lam_away * rho
    if home_goals == 1 and away_goals == 1:
        return 1.0 - rho
    return 1.0


def apply_dixon_coles(
    matrix: np.ndarray,
    lam_home: float,
    lam_away: float,
    rho: float,
) -> np.ndarray:
    """Return a copy of `matrix` with tau applied to the four low-scoring cells."""
    out = matrix.copy()
    out[0, 0] *= 1.0 - lam_home * lam_away * rho
    out[0, 1] *= 1.0 + lam_home * rho
    out[1, 0] *= 1.0 + lam_away * rho
    out[1, 1] *= 1.0 - rho
    return out


def collapse_1x2(matrix: np.ndarray) -> tuple[float, float, float]:
    """Reduce a scoreline matrix to (P(home win), P(draw), P(away win)).

    Normalizes so the three probabilities sum to 1, covering the tail mass
    lost to the `max_goals` truncation and any Dixon-Coles imbalance.
    """
    rows, cols = matrix.shape
    p_home = 0.0
    p_draw = 0.0
    p_away = 0.0
    for i in range(rows):
        for j in range(cols):
            if i > j:
                p_home += matrix[i, j]
            elif i == j:
                p_draw += matrix[i, j]
            else:
                p_away += matrix[i, j]
    total = p_home + p_draw + p_away
    return p_home / total, p_draw / total, p_away / total


def top_scorelines(
    matrix: np.ndarray,
    n: int = 5,
) -> list[tuple[int, int, float]]:
    """Return the top-n (home_goals, away_goals, probability) cells, descending."""
    rows, cols = matrix.shape
    cells = [(i, j, float(matrix[i, j])) for i in range(rows) for j in range(cols)]
    cells.sort(key=lambda c: c[2], reverse=True)
    return cells[:n]


def temperature_scale_1x2(
    p_home: float,
    p_draw: float,
    p_away: float,
    *,
    temperature: float,
) -> tuple[float, float, float]:
    """Scale a 1X2 probability triple by temperature, preserving normalization.

    Identity when T=1. T>1 flattens (reduces confidence on the max class);
    T<1 sharpens. Ordering is preserved. Pure in-simplex operation — does
    not touch the underlying scoreline matrix.
    """
    if temperature == 1.0:
        return p_home, p_draw, p_away
    inv = 1.0 / temperature
    raw = [max(p, 1e-12) ** inv for p in (p_home, p_draw, p_away)]
    z = sum(raw)
    return raw[0] / z, raw[1] / z, raw[2] / z


@dataclass(frozen=True)
class LivePrediction:
    p_home_win: float
    p_draw: float
    p_away_win: float
    expected_remaining_home_goals: float
    expected_remaining_away_goals: float


def live_probabilities(
    lam_home: float,
    lam_away: float,
    current_home: int,
    current_away: int,
    *,
    minute: int,
    rho: float = 0.0,
    max_additional: int = 6,
) -> LivePrediction:
    """Re-derive P(H/D/A) partway through a live match.

    Treats the match as two legs: what already happened (known score) plus
    remaining time modeled as a fresh Poisson draw with rates scaled by the
    minutes left (`rem = max(0, (90-minute)/90)`). Dixon-Coles ρ correction is
    applied to the remaining-goals matrix only — DC is a low-score adjustment,
    which still makes sense for the residual distribution.
    """
    rem = max(0.0, min(1.0, (90 - minute) / 90.0))

    if rem == 0:
        # Match over — result is locked in.
        if current_home > current_away:
            return LivePrediction(1.0, 0.0, 0.0, 0.0, 0.0)
        if current_home < current_away:
            return LivePrediction(0.0, 0.0, 1.0, 0.0, 0.0)
        return LivePrediction(0.0, 1.0, 0.0, 0.0, 0.0)

    lam_h_rem = lam_home * rem
    lam_a_rem = lam_away * rem
    matrix = poisson_score_matrix(lam_h_rem, lam_a_rem, max_goals=max_additional)
    if rho != 0.0:
        matrix = apply_dixon_coles(matrix, lam_h_rem, lam_a_rem, rho)

    total = float(matrix.sum())
    p_h = p_d = p_a = 0.0
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            final_h = current_home + i
            final_a = current_away + j
            cell = float(matrix[i, j]) / total
            if final_h > final_a:
                p_h += cell
            elif final_h < final_a:
                p_a += cell
            else:
                p_d += cell

    return LivePrediction(
        p_home_win=p_h,
        p_draw=p_d,
        p_away_win=p_a,
        expected_remaining_home_goals=lam_h_rem,
        expected_remaining_away_goals=lam_a_rem,
    )


def predict_match(
    lam_home: float,
    lam_away: float,
    rho: float = 0.1,
    max_goals: int = 5,
    top_n: int = 5,
    temperature: float = 1.0,
    elo_probs: tuple[float, float, float] | None = None,
    elo_weight: float = 0.0,
) -> MatchPrediction:
    """Full Dixon-Coles prediction with optional Elo-ensemble blend.

    If `elo_probs` is provided (a 3-way triple already summing to 1) and
    `elo_weight > 0`, the final 1X2 is a convex blend of the Poisson-derived
    triple and the Elo-derived triple. The scoreline matrix and `top_scorelines`
    stay pure Poisson so the most-likely scoreline list keeps its natural
    ordering — Elo is a 1X2-only signal.
    """
    base = poisson_score_matrix(lam_home, lam_away, max_goals=max_goals)
    adjusted = apply_dixon_coles(base, lam_home, lam_away, rho)
    p_h, p_d, p_a = collapse_1x2(adjusted)

    if elo_probs is not None and elo_weight > 0.0:
        w = min(1.0, max(0.0, elo_weight))
        eh, ed, ea = elo_probs
        p_h = (1.0 - w) * p_h + w * eh
        p_d = (1.0 - w) * p_d + w * ed
        p_a = (1.0 - w) * p_a + w * ea
        # Re-normalize in case of floating-point drift.
        z = p_h + p_d + p_a
        p_h, p_d, p_a = p_h / z, p_d / z, p_a / z

    p_h, p_d, p_a = temperature_scale_1x2(p_h, p_d, p_a, temperature=temperature)
    return MatchPrediction(
        p_home_win=p_h,
        p_draw=p_d,
        p_away_win=p_a,
        expected_home_goals=lam_home,
        expected_away_goals=lam_away,
        top_scorelines=top_scorelines(adjusted, n=top_n),
    )
