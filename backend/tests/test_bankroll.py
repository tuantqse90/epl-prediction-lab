"""Pure tests for the virtual-bankroll simulator used by /api/stats/roi
when ?staking=kelly.

The simulator walks historical value bets chronologically, sizes each stake
via fractional Kelly on the current bankroll, settles via match result, and
tracks peak + drawdown. It's the analytics-only counterpart of placing
Kelly-sized bets — no custody, no real stakes, just what would have
compounded if you'd followed the rule.
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


def test_bankroll_starts_at_starting_units_with_no_bets():
    from app.api.stats import _compute_kelly_bankroll
    out = _compute_kelly_bankroll([], threshold=0.05, cap=0.25, starting=100.0)
    assert out["final_units"] == pytest.approx(100.0)
    assert out["peak_units"] == pytest.approx(100.0)
    assert out["max_drawdown_pct"] == 0.0
    assert out["bets"] == 0
    assert out["points"] == []


def test_bankroll_winning_bet_grows_by_stake_times_odds_minus_one():
    from app.api.stats import _compute_kelly_bankroll
    # Home edge ~7pp, best_home=1.9, cap=0.25, starting=100
    # Kelly fraction = (0.60 * 1.9 - 1) / (1.9 - 1) ≈ 0.1556, well under cap.
    # Stake = 100 * 0.1556 = 15.56. Win → pnl = 15.56 * 0.9 = 14.00.
    rows = [_row(kickoff=_dt(-1), p_h=0.6, hg=1, ag=0)]
    out = _compute_kelly_bankroll(rows, threshold=0.05, cap=0.25, starting=100.0)
    assert out["bets"] == 1
    assert out["final_units"] == pytest.approx(114.00, abs=0.1)
    assert out["peak_units"] == pytest.approx(out["final_units"])


def test_bankroll_losing_bet_shrinks_by_stake():
    from app.api.stats import _compute_kelly_bankroll
    # Same edge as above but home LOSES → stake 15.56 lost.
    rows = [_row(kickoff=_dt(-1), p_h=0.6, hg=0, ag=1)]
    out = _compute_kelly_bankroll(rows, threshold=0.05, cap=0.25, starting=100.0)
    assert out["bets"] == 1
    assert out["final_units"] == pytest.approx(100.0 - 15.56, abs=0.1)


def test_bankroll_second_bet_compounds_on_reduced_balance():
    """Consecutive losing bets: the second stake is smaller because the
    bankroll shrank. This is the key property of Kelly compounding."""
    from app.api.stats import _compute_kelly_bankroll
    rows = [
        _row(kickoff=_dt(-2), p_h=0.6, hg=0, ag=1),  # lose 15.56 → 84.44
        _row(kickoff=_dt(-1), p_h=0.6, hg=0, ag=1),  # second stake = 84.44 * 0.1556 ≈ 13.14
    ]
    out = _compute_kelly_bankroll(rows, threshold=0.05, cap=0.25, starting=100.0)
    assert out["bets"] == 2
    # After both losses: 100 - 15.56 - 13.14 ≈ 71.30
    assert out["final_units"] == pytest.approx(71.30, abs=0.2)


def test_bankroll_cap_enforced_on_extreme_edge():
    from app.api.stats import _compute_kelly_bankroll
    # p_h=0.95, best_home=5.0 → full Kelly = (0.95*5-1)/(5-1) ≈ 0.9375 — way
    # over any sane cap. Must clamp to `cap` (0.25 by default).
    rows = [_row(kickoff=_dt(-1), p_h=0.95, p_d=0.03, p_a=0.02, oh=5.0, od=5.0, oa=5.0,
                 best_h=5.0, best_d=5.0, best_a=5.0, hg=1, ag=0)]
    out = _compute_kelly_bankroll(rows, threshold=0.05, cap=0.25, starting=100.0)
    # Stake = 100 * 0.25 = 25. Win → 25 * 4 = 100. Final = 200.
    assert out["final_units"] == pytest.approx(200.0, abs=0.5)


def test_bankroll_tracks_peak_and_drawdown():
    """Drawdown = (peak − trough_after_peak) / peak * 100."""
    from app.api.stats import _compute_kelly_bankroll
    rows = [
        _row(kickoff=_dt(-3), p_h=0.6, hg=1, ag=0),  # win → ~114
        _row(kickoff=_dt(-2), p_h=0.6, hg=0, ag=1),  # lose ~18 → ~96
        _row(kickoff=_dt(-1), p_h=0.6, hg=0, ag=1),  # lose ~15 → ~81
    ]
    out = _compute_kelly_bankroll(rows, threshold=0.05, cap=0.25, starting=100.0)
    assert out["peak_units"] == pytest.approx(114.0, abs=0.5)
    # DD = (114 − 81) / 114 ≈ 28.9%
    assert out["max_drawdown_pct"] == pytest.approx(28.9, abs=1.0)


def test_bankroll_rows_processed_in_chronological_order():
    """Even if input is reversed, simulator sorts by kickoff so older bets
    compound first."""
    from app.api.stats import _compute_kelly_bankroll
    a = _row(kickoff=_dt(-2), p_h=0.6, hg=1, ag=0)  # older — win
    b = _row(kickoff=_dt(-1), p_h=0.6, hg=0, ag=1)  # newer — lose
    out_forward = _compute_kelly_bankroll([a, b], threshold=0.05, cap=0.25, starting=100.0)
    out_reversed = _compute_kelly_bankroll([b, a], threshold=0.05, cap=0.25, starting=100.0)
    assert out_forward["final_units"] == pytest.approx(out_reversed["final_units"])
    assert out_forward["peak_units"] == pytest.approx(out_reversed["peak_units"])


def test_bankroll_zero_stake_when_edge_below_threshold():
    """If no side has model_prob − fair ≥ threshold, we don't bet — bankroll
    untouched even though there's match data."""
    from app.api.stats import _compute_kelly_bankroll
    # Flat fair odds → ~33% each, model says 36/34/30 → max edge ~3pp
    rows = [_row(kickoff=_dt(-1), p_h=0.36, p_d=0.34, p_a=0.30,
                 oh=3.0, od=3.0, oa=3.0, best_h=3.0, best_d=3.0, best_a=3.0)]
    out = _compute_kelly_bankroll(rows, threshold=0.05, cap=0.25, starting=100.0)
    assert out["bets"] == 0
    assert out["final_units"] == pytest.approx(100.0)


def test_bankroll_stakes_only_highest_edge_side_per_match():
    """Mutual-exclusivity fix: if two sides of the same match both flag
    edge ≥ threshold, only the higher-edge side is staked. Staking both
    blindly would exceed the per-match cap and explode drawdown on 1X2."""
    from app.api.stats import _compute_kelly_bankroll
    # Construct a match where Home AND Draw both flag edges: model says
    # H=0.55, D=0.30, A=0.15 but fair is H=0.45, D=0.20, A=0.35.
    # Edges: H=+10pp, D=+10pp, A=-20pp. Both H and D above threshold.
    # Away actually wins (hg=0, ag=1) → if we bet BOTH H and D, both lose.
    # The simulator must bet only ONE side (the higher edge), not two.
    rows = [_row(
        kickoff=_dt(-1),
        p_h=0.55, p_d=0.30, p_a=0.15,
        oh=2.10, od=3.90, oa=3.10,   # fair devig ≈ (0.45, 0.24, 0.31)
        best_h=2.20, best_d=4.00, best_a=3.20,
        hg=0, ag=1,
    )]
    out = _compute_kelly_bankroll(rows, threshold=0.05, cap=0.25, starting=100.0)
    # One bet (not two). Loss of one stake only.
    assert out["bets"] == 1
