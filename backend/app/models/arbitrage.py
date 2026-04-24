"""Arbitrage detector.

For each match we look at every book's 1X2 odds, pick the MAX odds per
outcome across books, and check whether Σ(1/best_odds) < 1. If yes,
stake proportional to implied probability yields guaranteed profit.

    stake_k = (1 / best_odds_k) / Σ(1 / best_odds_j)
    bankroll returns (stake_k * best_odds_k) regardless of k that wins
    profit_percent = 100 * (1 / Σ(1 / best_odds_j) - 1)

Returns the single best arb per fixture, or None if no combination is
sub-100%.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ArbOpportunity:
    profit_percent: float
    home_source: str
    draw_source: str
    away_source: str
    home_odds: float
    draw_odds: float
    away_odds: float
    stake_home: float       # fraction of bankroll
    stake_draw: float
    stake_away: float


def best_arb(rows: Iterable) -> ArbOpportunity | None:
    """Scan odds rows (each with odds_home/draw/away + source) and emit
    the best arb, or None. Rejects any row with odds ≤ 1.0 as malformed."""
    rows = list(rows)

    best_h = None   # (odds, source)
    best_d = None
    best_a = None
    for r in rows:
        h = float(getattr(r, "odds_home", 0) or 0)
        d = float(getattr(r, "odds_draw", 0) or 0)
        a = float(getattr(r, "odds_away", 0) or 0)
        src = getattr(r, "source", "?")
        if h > 1.0 and (best_h is None or h > best_h[0]):
            best_h = (h, src)
        if d > 1.0 and (best_d is None or d > best_d[0]):
            best_d = (d, src)
        if a > 1.0 and (best_a is None or a > best_a[0]):
            best_a = (a, src)

    if best_h is None or best_d is None or best_a is None:
        return None

    total_imp = 1.0 / best_h[0] + 1.0 / best_d[0] + 1.0 / best_a[0]
    if total_imp >= 1.0:
        return None

    profit_pct = (1.0 / total_imp - 1.0) * 100.0
    stake_h = (1.0 / best_h[0]) / total_imp
    stake_d = (1.0 / best_d[0]) / total_imp
    stake_a = (1.0 / best_a[0]) / total_imp

    return ArbOpportunity(
        profit_percent=profit_pct,
        home_source=best_h[1], draw_source=best_d[1], away_source=best_a[1],
        home_odds=best_h[0], draw_odds=best_d[0], away_odds=best_a[0],
        stake_home=stake_h, stake_draw=stake_d, stake_away=stake_a,
    )
