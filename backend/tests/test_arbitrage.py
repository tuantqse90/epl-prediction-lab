"""Arbitrage detector — find (book_h, book_d, book_a) combinations
where Σ(1/odds) < 1, i.e. staking appropriately yields guaranteed profit
regardless of outcome.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


def _odds(source, home, draw, away):
    return SimpleNamespace(source=source, odds_home=home, odds_draw=draw, odds_away=away)


def test_no_arb_when_single_book():
    from app.models.arbitrage import best_arb

    rows = [_odds("pinnacle", 2.0, 3.5, 4.0)]
    r = best_arb(rows)
    # 1/2.0 + 1/3.5 + 1/4.0 = 0.5 + 0.286 + 0.25 = 1.036 → no arb
    assert r is None or r.profit_percent < 0


def test_arb_across_three_books():
    from app.models.arbitrage import best_arb

    rows = [
        _odds("book_home", 2.50, 3.00, 2.50),   # best H = 2.50
        _odds("book_draw", 2.00, 4.00, 2.00),   # best D = 4.00
        _odds("book_away", 2.00, 3.00, 3.10),   # best A = 3.10
    ]
    # 1/2.50 + 1/4.00 + 1/3.10 = 0.400 + 0.250 + 0.323 = 0.973
    # profit ≈ 2.7%
    r = best_arb(rows)
    assert r is not None
    assert r.profit_percent > 2.0
    assert r.profit_percent < 4.0
    # Each source chosen matches the best-for-outcome
    assert r.home_source == "book_home"
    assert r.draw_source == "book_draw"
    assert r.away_source == "book_away"


def test_stakes_sum_to_bankroll():
    from app.models.arbitrage import best_arb

    rows = [
        _odds("A", 2.50, 3.00, 2.50),
        _odds("B", 2.00, 4.00, 2.00),
        _odds("C", 2.00, 3.00, 3.10),
    ]
    r = best_arb(rows)
    assert r is not None
    total = r.stake_home + r.stake_draw + r.stake_away
    assert total == pytest.approx(1.0, abs=0.001)


def test_stakes_produce_same_return_across_outcomes():
    """Arb stakes are sized so every outcome yields identical net return."""
    from app.models.arbitrage import best_arb

    rows = [
        _odds("A", 2.50, 3.00, 2.50),
        _odds("B", 2.00, 4.00, 2.00),
        _odds("C", 2.00, 3.00, 3.10),
    ]
    r = best_arb(rows)
    assert r is not None
    ret_h = r.stake_home * r.home_odds
    ret_d = r.stake_draw * r.draw_odds
    ret_a = r.stake_away * r.away_odds
    assert ret_h == pytest.approx(ret_d, abs=0.01)
    assert ret_d == pytest.approx(ret_a, abs=0.01)


def test_handles_missing_outcome_gracefully():
    """Row with any odds ≤ 1.0 shouldn't crash; returns None."""
    from app.models.arbitrage import best_arb

    rows = [_odds("weird", 0.0, 2.0, 3.0)]
    assert best_arb(rows) is None
