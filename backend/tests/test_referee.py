"""Tests for app.models.referee — per-ref goals-per-match delta and the
multiplicative λ adjustment applied by predict/service.

Symmetric application: refs affect both teams' goal-scoring environment
equally (they don't favour home or away). Capped at ±10% so a sparse
outlier ref never nukes predictions.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


def _row(referee, home, away):
    return SimpleNamespace(referee=referee, home_goals=home, away_goals=away)


def test_referee_tendency_zero_below_min_samples():
    """Sparse refs (< MIN_SAMPLES matches) get 0 delta — too noisy to trust."""
    from app.models.referee import referee_tendencies

    rows = [_row("Sparse Ref", 2, 1) for _ in range(5)]  # 5 matches only
    out = referee_tendencies(rows, min_matches=20)
    # Sparse refs are excluded from the mapping entirely.
    assert "Sparse Ref" not in out


def test_referee_tendency_high_goals_ref_positive_delta():
    """A ref whose matches average 3.5 goals while league avg is 2.8 → +0.7
    goals-per-match delta."""
    from app.models.referee import referee_tendencies

    # 25 "A. Taylor" matches averaging 3.5 goals each.
    taylor = [_row("A. Taylor", 2, 2) for _ in range(15)] + \
             [_row("A. Taylor", 3, 1) for _ in range(10)]
    # 30 baseline matches at 2.5 goals each → league avg ~2.8.
    baseline = [_row(f"Other {i}", 1, 1) for i in range(15)] + \
               [_row(f"Other {i}", 2, 2) for i in range(15)]
    rows = taylor + baseline

    out = referee_tendencies(rows, min_matches=20)
    assert "A. Taylor" in out
    # Taylor avg = (15*4 + 10*4)/25 = 4.0. League avg = (taylor_goals + baseline_goals) / total
    # = (15*4 + 10*4 + 15*2 + 15*4) / 55 = (60 + 40 + 30 + 60) / 55 = 190/55 = 3.45
    # Delta = 4.0 - 3.45 = +0.55
    delta = out["A. Taylor"]["goals_delta"]
    assert delta == pytest.approx(0.55, abs=0.02)
    assert out["A. Taylor"]["n"] == 25


def test_referee_multiplier_symmetric_and_capped():
    """The multiplier applied to each team's λ is the same sign for both
    (refs don't favour one side) and never outside ±10%."""
    from app.models.referee import referee_multiplier

    # League avg 2.8, ref delta +0.8 → +28% on total goals. Cap at +10%.
    m_capped = referee_multiplier(delta=0.8, league_avg=2.8, cap=0.10)
    assert m_capped == pytest.approx(1.10, abs=1e-6)

    # Modest delta +0.2 on 2.8 → +7.1% → under cap, pass through.
    m_soft = referee_multiplier(delta=0.2, league_avg=2.8, cap=0.10)
    assert m_soft == pytest.approx(1.0 + 0.2 / 2.8, abs=1e-6)

    # Negative delta clamped too.
    m_neg = referee_multiplier(delta=-0.5, league_avg=2.8, cap=0.10)
    assert m_neg == pytest.approx(0.90, abs=1e-6)


def test_referee_multiplier_one_on_missing_data():
    """No ref → multiplier 1.0 (no-op, no shrink)."""
    from app.models.referee import referee_multiplier

    assert referee_multiplier(delta=None, league_avg=2.8) == 1.0


def test_referee_multiplier_one_on_zero_league_avg():
    """Defensive: zero league_avg (shouldn't happen) → 1.0."""
    from app.models.referee import referee_multiplier

    assert referee_multiplier(delta=0.3, league_avg=0.0) == 1.0


def test_league_avg_computed_on_same_sample():
    """If we swap the sample, the baseline moves. Taylor's delta is relative
    to whichever league_avg the same rows imply — not a hard-coded 2.8."""
    from app.models.referee import referee_tendencies

    low_scoring = [_row(f"X{i}", 1, 0) for i in range(30)] + \
                  [_row("Taylor", 2, 2) for _ in range(25)]
    out = referee_tendencies(low_scoring, min_matches=20)
    # Baseline 1.0 + Taylor 4.0 → avg (30 + 100) / 55 = 2.36. Taylor delta = 4 − 2.36 = 1.64
    assert out["Taylor"]["goals_delta"] == pytest.approx(1.64, abs=0.02)
