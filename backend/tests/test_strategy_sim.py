"""Tests for the Phase 15 strategy simulator.

Each strategy is a pure function that walks historical value-bet rows
(same shape as the Kelly bankroll simulator) and returns a bankroll
trajectory. Uniform output so the FE chart is reusable across strategies.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest


def _row(*, kickoff, p_h=0.6, p_d=0.2, p_a=0.2,
         oh=1.8, od=3.6, oa=4.5,
         best_h=1.9, best_d=3.7, best_a=4.8,
         hg=1, ag=0, league="eng.1"):
    return SimpleNamespace(
        kickoff_time=kickoff,
        league_code=league,
        p_home_win=p_h, p_draw=p_d, p_away_win=p_a,
        odds_home=oh, odds_draw=od, odds_away=oa,
        best_home=best_h, best_draw=best_d, best_away=best_a,
        home_goals=hg, away_goals=ag,
    )


def _dt(days_from_now):
    return datetime.now(timezone.utc) + timedelta(days=days_from_now)


# ── 15.1 Value ladder ────────────────────────────────────────────────────────


def test_value_ladder_scales_stake_linearly_with_edge_pp():
    """5pp edge → 1× base_unit. 10pp edge → 2×. 20pp edge → 4× (under cap)."""
    from app.api.stats import _simulate_value_ladder

    # Home win at 0.60 prob, fair~0.527 → edge ~7.4pp → stake 7.4/5 = 1.47× base
    # best=1.9, win → PnL = 1.47 * 0.9 = 1.32
    rows = [_row(kickoff=_dt(-1), p_h=0.60, hg=1, ag=0)]
    out = _simulate_value_ladder(rows, threshold=0.05, starting=100.0,
                                 base_unit=1.0, cap_mult=5.0)
    assert out["bets"] == 1
    # Edge ≈ 7.4pp → stake 1.47, win 1.47 * 0.9 = 1.32
    assert out["final_units"] == pytest.approx(101.32, abs=0.1)


def test_value_ladder_caps_stake_at_cap_mult():
    """Extreme edge clamped. E.g., 60pp edge should not stake 12× base."""
    from app.api.stats import _simulate_value_ladder

    # p_h=0.95, fair(~0.33) → edge ~62pp → raw ladder = 12.4× → cap at 5×
    rows = [_row(kickoff=_dt(-1), p_h=0.95, p_d=0.03, p_a=0.02,
                 oh=3.0, od=3.0, oa=3.0, best_h=3.0, best_d=3.0, best_a=3.0,
                 hg=1, ag=0)]
    out = _simulate_value_ladder(rows, threshold=0.05, starting=100.0,
                                 base_unit=1.0, cap_mult=5.0)
    # Stake clamped to 5.0 base_unit, win at odds 3.0 → 5 * 2 = +10
    assert out["final_units"] == pytest.approx(110.0, abs=0.2)


def test_value_ladder_skips_below_threshold():
    from app.api.stats import _simulate_value_ladder

    # Tiny edge — no bet.
    rows = [_row(kickoff=_dt(-1), p_h=0.36, p_d=0.33, p_a=0.31,
                 oh=3.0, od=3.0, oa=3.0, best_h=3.0, best_d=3.0, best_a=3.0)]
    out = _simulate_value_ladder(rows, threshold=0.05, starting=100.0,
                                 base_unit=1.0, cap_mult=5.0)
    assert out["bets"] == 0
    assert out["final_units"] == pytest.approx(100.0)


def test_value_ladder_tracks_peak_and_drawdown():
    from app.api.stats import _simulate_value_ladder

    rows = [
        _row(kickoff=_dt(-2), p_h=0.6, hg=1, ag=0),  # win
        _row(kickoff=_dt(-1), p_h=0.6, hg=0, ag=1),  # lose
    ]
    out = _simulate_value_ladder(rows, threshold=0.05, starting=100.0,
                                 base_unit=1.0, cap_mult=5.0)
    assert out["peak_units"] >= out["starting_units"]
    assert 0 <= out["max_drawdown_pct"] <= 100


# ── 15.2 High-confidence filter ──────────────────────────────────────────────


def test_highconf_filter_skips_low_confidence_bets():
    """Filter: model_prob ≥ 0.60 AND edge ≥ threshold. Low model_prob → skip."""
    from app.api.stats import _simulate_high_confidence

    # p_h=0.52 → below 60% confidence floor → skipped even with edge ≥ 5pp
    rows = [_row(kickoff=_dt(-1), p_h=0.52, p_d=0.25, p_a=0.23,
                 oh=2.2, od=3.5, oa=3.8, best_h=2.2, best_d=3.5, best_a=3.8,
                 hg=1, ag=0)]
    out = _simulate_high_confidence(rows, threshold=0.05, starting=100.0,
                                    min_confidence=0.60)
    assert out["bets"] == 0
    assert out["final_units"] == pytest.approx(100.0)


def test_highconf_filter_takes_bet_when_confidence_met():
    """p_h=0.65, edge well above 5pp → flat 1u bet."""
    from app.api.stats import _simulate_high_confidence

    rows = [_row(kickoff=_dt(-1), p_h=0.65, p_d=0.20, p_a=0.15,
                 oh=1.8, od=3.5, oa=5.5, best_h=1.9, best_d=3.6, best_a=5.7,
                 hg=1, ag=0)]
    out = _simulate_high_confidence(rows, threshold=0.05, starting=100.0,
                                    min_confidence=0.60)
    assert out["bets"] == 1
    # Flat 1u win @ 1.9 → +0.9
    assert out["final_units"] == pytest.approx(100.9, abs=1e-3)


# ── 15.3 Martingale ──────────────────────────────────────────────────────────


def test_martingale_doubles_after_loss_resets_on_win():
    """Stake: 1, 2, 4 (three losses in a row)... then win clears to 1 again."""
    from app.api.stats import _simulate_martingale

    rows = [
        _row(kickoff=_dt(-4), p_h=0.6, best_h=2.0, hg=0, ag=1),  # lose @ stake 1 → -1
        _row(kickoff=_dt(-3), p_h=0.6, best_h=2.0, hg=0, ag=1),  # lose @ stake 2 → -2
        _row(kickoff=_dt(-2), p_h=0.6, best_h=2.0, hg=0, ag=1),  # lose @ stake 4 → -4
        _row(kickoff=_dt(-1), p_h=0.6, best_h=2.0, hg=1, ag=0),  # win  @ stake 8 → +8
    ]
    out = _simulate_martingale(rows, threshold=0.05, starting=100.0, base_unit=1.0)
    # After all four: 100 - 1 - 2 - 4 + 8 = 101
    assert out["final_units"] == pytest.approx(101.0, abs=0.01)
    assert out["bets"] == 4


def test_martingale_stops_at_bankroll_depleted():
    """Losing streak that would require a stake > current bankroll → sim
    clamps to remaining and loop exits."""
    from app.api.stats import _simulate_martingale

    # 6 losses in a row at base=10 → stakes 10,20,40,80 takes us past 100
    rows = [_row(kickoff=_dt(-6 + i), p_h=0.6, best_h=2.0, hg=0, ag=1) for i in range(6)]
    out = _simulate_martingale(rows, threshold=0.05, starting=100.0, base_unit=10.0)
    assert out["final_units"] == pytest.approx(0.0)
    # Not every row was bet — loop bailed early.
    assert out["bets"] < 6
