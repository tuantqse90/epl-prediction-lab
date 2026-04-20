"""Pure-function tests for the ROI aggregator + per-league grouping used by
`/api/stats/roi` and `/api/stats/roi/by-league`.

Both endpoints walk the same per-match rows (from match + prediction + odds
joins) and score each side where model edge ≥ threshold. Extracting the
arithmetic into a pure function makes it TDD-able without a running DB.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


def _row(
    *,
    league="eng.1",
    p_h=0.6,
    p_d=0.2,
    p_a=0.2,
    oh=1.8,
    od=3.6,
    oa=4.5,
    best_h=1.9,
    best_d=3.7,
    best_a=4.8,
    hg=1,
    ag=0,
):
    """A minimal asyncpg-row-shaped stand-in (attr access via SimpleNamespace)."""
    return SimpleNamespace(
        league_code=league,
        p_home_win=p_h, p_draw=p_d, p_away_win=p_a,
        odds_home=oh, odds_draw=od, odds_away=oa,
        best_home=best_h, best_draw=best_d, best_away=best_a,
        home_goals=hg, away_goals=ag,
    )


def test_compute_roi_counts_only_bets_above_threshold():
    from app.api.stats import _compute_roi_metrics

    # p_H=0.60; fair devig ≈ (0.556, 0.278, 0.222)/sum ≈ normalise…
    # Precompute: raw = [1/1.8, 1/3.6, 1/4.5] = [0.5556, 0.2778, 0.2222] sum=1.0556
    # fair_H ≈ 0.5263 → edge = 0.60 − 0.5263 = 0.0737 > 0.05 ✓
    rows = [_row(p_h=0.6, p_d=0.2, p_a=0.2, hg=1, ag=0)]  # home wins

    m = _compute_roi_metrics(rows, threshold=0.05)
    assert m["bets"] == 1
    assert m["wins"] == 1
    # PnL using best_odds_home = 1.9, stake 1u, won → +0.9
    assert m["pnl_vig"] == pytest.approx(0.9, abs=1e-4)


def test_compute_roi_skips_rows_below_threshold():
    from app.api.stats import _compute_roi_metrics

    # Prob ≈ fair → edge tiny, below 5pp threshold everywhere.
    rows = [_row(p_h=0.53, p_d=0.28, p_a=0.19)]
    m = _compute_roi_metrics(rows, threshold=0.05)
    assert m["bets"] == 0
    assert m["wins"] == 0
    assert m["pnl_vig"] == pytest.approx(0.0)


def test_compute_roi_loss_bets_subtract_one_unit():
    from app.api.stats import _compute_roi_metrics

    # Edge 7pp on home, but home LOSES.
    rows = [_row(p_h=0.6, p_d=0.2, p_a=0.2, hg=0, ag=1)]
    m = _compute_roi_metrics(rows, threshold=0.05)
    assert m["bets"] == 1
    assert m["wins"] == 0
    assert m["pnl_vig"] == pytest.approx(-1.0)


def test_compute_roi_no_vig_pnl_uses_devigged_odds():
    """No-vig PnL simulates Polymarket-style zero-overround market."""
    from app.api.stats import _compute_roi_metrics

    rows = [_row(p_h=0.6, p_d=0.2, p_a=0.2, hg=1, ag=0)]
    m = _compute_roi_metrics(rows, threshold=0.05)
    # Fair home ≈ 0.5263 → no-vig decimal ≈ 1.9. PnL on win ≈ +0.9
    assert m["pnl_nov"] == pytest.approx(1.0 / 0.5263 - 1.0, rel=1e-3)


def test_roi_by_league_groups_rows_by_league_code():
    from app.api.stats import _compute_roi_by_league

    rows = [
        _row(league="eng.1", p_h=0.6, hg=1, ag=0),   # win
        _row(league="eng.1", p_h=0.6, hg=0, ag=1),   # loss
        _row(league="esp.1", p_h=0.6, hg=1, ag=0),   # win
    ]
    out = _compute_roi_by_league(rows, threshold=0.05)

    by = {r["league_code"]: r for r in out}
    assert by["eng.1"]["bets"] == 2
    assert by["eng.1"]["wins"] == 1
    assert by["esp.1"]["bets"] == 1
    assert by["esp.1"]["wins"] == 1


def test_roi_by_league_sorts_by_bets_desc():
    """UI expects most-active leagues first."""
    from app.api.stats import _compute_roi_by_league

    rows = [
        _row(league="eng.1", p_h=0.6, hg=1, ag=0),
        _row(league="eng.1", p_h=0.6, hg=0, ag=1),
        _row(league="eng.1", p_h=0.6, hg=1, ag=0),
        _row(league="esp.1", p_h=0.6, hg=1, ag=0),
    ]
    out = _compute_roi_by_league(rows, threshold=0.05)
    assert [r["league_code"] for r in out] == ["eng.1", "esp.1"]
