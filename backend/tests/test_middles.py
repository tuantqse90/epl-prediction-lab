"""O/U middles — two bets on different lines where an exact scoreline
makes both win."""
from __future__ import annotations

from types import SimpleNamespace

import pytest


def _ou(source, line, outcome, odds):
    return SimpleNamespace(source=source, line=line, outcome_code=outcome, odds=odds)


def test_detect_middle_2_5_over_vs_3_5_under():
    from app.models.middles import find_ou_middles

    rows = [
        _ou("A", 2.5, "OVER", 1.90),
        _ou("B", 3.5, "UNDER", 1.95),
    ]
    ms = find_ou_middles(rows)
    assert len(ms) == 1
    m = ms[0]
    # Middle: 3 goals exactly
    assert m["middle_low"] == 2.5
    assert m["middle_high"] == 3.5
    # Win payout when middle hits: 1 × odds_over + 1 × odds_under - 2 stakes
    assert m["middle_pnl"] == pytest.approx(1.90 + 1.95 - 2.0)
    # No-middle outcome: one wins, one loses
    assert m["miss_pnl_low"] == pytest.approx(1.95 - 2.0)   # under 2.5 → under wins
    assert m["miss_pnl_high"] == pytest.approx(1.90 - 2.0)  # over 3.5 → over wins


def test_no_middle_when_overlapping():
    """If A.line > B.line we'd have NO middle gap (over X wins whenever
    under Y wins when Y > X — no exclusive middle band)."""
    from app.models.middles import find_ou_middles

    rows = [
        _ou("A", 3.5, "OVER", 1.90),
        _ou("B", 2.5, "UNDER", 1.95),
    ]
    assert find_ou_middles(rows) == []


def test_equal_lines_not_middle():
    """Same line on both books is a straight 2-way, not a middle."""
    from app.models.middles import find_ou_middles

    rows = [
        _ou("A", 2.5, "OVER", 1.90),
        _ou("B", 2.5, "UNDER", 1.95),
    ]
    assert find_ou_middles(rows) == []


def test_picks_best_across_multiple_combinations():
    """When several O/U pairs qualify, return them all, sorted by profit."""
    from app.models.middles import find_ou_middles

    rows = [
        _ou("A", 2.5, "OVER", 2.10),   # generous over
        _ou("B", 3.5, "UNDER", 2.00),
        _ou("C", 1.5, "OVER", 1.50),   # tight over
        _ou("D", 2.5, "UNDER", 1.80),
    ]
    ms = find_ou_middles(rows)
    assert len(ms) >= 1
    # Most profitable on middle hit should be sorted first
    assert ms[0]["middle_pnl"] >= ms[-1]["middle_pnl"]
