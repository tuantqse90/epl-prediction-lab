"""Derived markets from a scoreline probability matrix.

The core Poisson-DC engine produces M[i, j] = P(home=i, away=j) already.
Every over/under, both-teams-to-score, and correct-score market is a
different linear combination of those cells. Keeping this logic here
means a single source of truth when we add new lines (O/U 3.5, draw-no-bet).

Kelly-fraction sizing lives alongside so the FE can surface stake
recommendations next to each value bet.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


def prob_over(matrix: np.ndarray, line: float) -> float:
    """P(home + away > line). Line is inclusive of the .5 half-line."""
    rows, cols = matrix.shape
    total = 0.0
    for i in range(rows):
        for j in range(cols):
            if i + j > line:
                total += float(matrix[i, j])
    return total


def prob_under(matrix: np.ndarray, line: float) -> float:
    """P(home + away < line)."""
    return max(0.0, 1.0 - prob_over(matrix, line) - _prob_exact(matrix, line))


def _prob_exact(matrix: np.ndarray, line: float) -> float:
    # For half-lines (2.5, 3.5), P(exact=line) = 0 — no cell can match.
    if line != int(line):
        return 0.0
    rows, cols = matrix.shape
    total = 0.0
    for i in range(rows):
        for j in range(cols):
            if i + j == int(line):
                total += float(matrix[i, j])
    return total


def prob_btts(matrix: np.ndarray) -> float:
    """P(both teams score ≥ 1)."""
    rows, cols = matrix.shape
    total = 0.0
    for i in range(1, rows):
        for j in range(1, cols):
            total += float(matrix[i, j])
    return total


def prob_home_clean_sheet(matrix: np.ndarray) -> float:
    """P(away_goals == 0)."""
    return float(matrix[:, 0].sum())


def prob_away_clean_sheet(matrix: np.ndarray) -> float:
    """P(home_goals == 0)."""
    return float(matrix[0, :].sum())


KELLY_CAP = 0.25  # no more than 25% of bankroll on a single bet (fractional Kelly)


def kelly_stake(prob: float, odds: float, cap: float = KELLY_CAP) -> float:
    """Fractional Kelly stake.

    Returns the share of the bankroll to wager on a market where the model
    estimates `prob` and the bookmaker offers decimal `odds`. Returns 0 when
    there's no edge. Capped at `cap` (default 0.25) — full Kelly is brutal
    on estimate error.
    """
    if prob <= 0.0 or odds <= 1.0:
        return 0.0
    edge = prob * odds - 1.0
    if edge <= 0.0:
        return 0.0
    stake = edge / (odds - 1.0)
    return max(0.0, min(cap, stake))


@dataclass(frozen=True)
class MarketProbs:
    """Snapshot of derived markets for a single match prediction."""
    prob_over_0_5: float
    prob_over_1_5: float
    prob_over_2_5: float
    prob_over_3_5: float
    prob_btts: float
    prob_home_clean_sheet: float
    prob_away_clean_sheet: float


def markets_from_matrix(matrix: np.ndarray) -> MarketProbs:
    return MarketProbs(
        prob_over_0_5=prob_over(matrix, 0.5),
        prob_over_1_5=prob_over(matrix, 1.5),
        prob_over_2_5=prob_over(matrix, 2.5),
        prob_over_3_5=prob_over(matrix, 3.5),
        prob_btts=prob_btts(matrix),
        prob_home_clean_sheet=prob_home_clean_sheet(matrix),
        prob_away_clean_sheet=prob_away_clean_sheet(matrix),
    )


def _ensure_sane(x: float) -> float:
    """Clamp tiny floating-point noise off probabilities."""
    if not math.isfinite(x):
        return 0.0
    return max(0.0, min(1.0, x))


# ── Asian handicap + SGP ─────────────────────────────────────────────────────

def _ah_half_line(matrix: np.ndarray, line: float, side: str) -> float:
    """Half-line AH: no push possible — strict win or strict lose.

    Line is bettor-perspective: it's added to the chosen side's goals, then
    compared to the opponent's score. `+0.5 home` wins on draw-or-win;
    `-0.5 away` wins only when away wins by 1+."""
    rows, cols = matrix.shape
    total = 0.0
    for i in range(rows):
        for j in range(cols):
            if side == "home":
                if i + line > j:
                    total += float(matrix[i, j])
            else:  # away
                if j + line > i:
                    total += float(matrix[i, j])
    return total


def _ah_integer_line(matrix: np.ndarray, line: float, side: str) -> float:
    """Integer AH: win / push / lose → effective prob = P(win) + 0.5·P(push).

    Push = half stake refund, so the stake-adjusted expected return expressed
    as an implied win probability is `P(win) + 0.5·P(push)` — directly
    comparable to fair decimal odds = 1/p for edge detection."""
    rows, cols = matrix.shape
    p_win = 0.0
    p_push = 0.0
    for i in range(rows):
        for j in range(cols):
            if side == "home":
                delta = i + line - j
            else:
                delta = j + line - i
            cell = float(matrix[i, j])
            if delta > 0:
                p_win += cell
            elif delta == 0:
                p_push += cell
    return p_win + 0.5 * p_push


def prob_asian_handicap(matrix: np.ndarray, line: float, side: str) -> float:
    """Effective win probability for an Asian handicap bet.

    Supports half-lines (.5), integer (.0), and quarter-lines (.25, .75) by
    splitting the stake between the adjacent half and integer lines.

    Returns a single float that can feed `1/p` → fair decimal odds and is
    directly comparable to book prices for edge detection."""
    if side not in ("home", "away"):
        raise ValueError(f"side must be 'home' or 'away', got {side!r}")

    frac = abs(line) - int(abs(line))
    # Quarter-line (±0.25, ±0.75): split stake in half between the two
    # neighbouring lines (half-line above and below).
    if math.isclose(frac, 0.25) or math.isclose(frac, 0.75):
        sign = 1 if line > 0 else -1
        lower = sign * (abs(line) - 0.25)   # nearer to 0
        upper = sign * (abs(line) + 0.25)
        return 0.5 * prob_asian_handicap(matrix, lower, side) \
             + 0.5 * prob_asian_handicap(matrix, upper, side)

    if math.isclose(frac, 0.5):
        return _ah_half_line(matrix, line, side)
    return _ah_integer_line(matrix, line, side)


def prob_sgp_btts_and_over(matrix: np.ndarray, line: float) -> float:
    """Same-game parlay: P(both teams score AND total > line).

    Summed directly over matrix cells so the natural correlation between
    BTTS and goal totals is preserved — NOT the naive product of marginals
    that books sometimes price."""
    rows, cols = matrix.shape
    total = 0.0
    for i in range(1, rows):
        for j in range(1, cols):
            if i + j > line:
                total += float(matrix[i, j])
    return total
