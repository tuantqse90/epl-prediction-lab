"""Defense-adjusted player xG — scale a player's xG per match by the
opponent's defensive strength, so goals racked up against weak defenses
count less than against strong ones."""
from __future__ import annotations

import pytest


def test_no_opponent_adjustment_neutral():
    from app.models.defense_adjusted_xg import adjusted_xg

    # Defense coef = 1.0 (league-average opponent) → no change
    assert adjusted_xg(raw_xg=0.5, opp_defense_coef=1.0) == pytest.approx(0.5)


def test_weak_defense_deflates_xg():
    """xG against a very porous defense (coef 1.4 = 40% worse than avg)
    should be multiplied down."""
    from app.models.defense_adjusted_xg import adjusted_xg

    # raw 0.5 / 1.4 ≈ 0.357
    assert adjusted_xg(raw_xg=0.5, opp_defense_coef=1.4) == pytest.approx(0.357, abs=0.01)


def test_strong_defense_inflates_xg():
    """xG against an elite defense (coef 0.6) should inflate."""
    from app.models.defense_adjusted_xg import adjusted_xg

    # 0.5 / 0.6 ≈ 0.833
    assert adjusted_xg(raw_xg=0.5, opp_defense_coef=0.6) == pytest.approx(0.833, abs=0.01)


def test_clamp_band_prevents_explosion():
    """Tiny defense coef must not blow up the adjustment."""
    from app.models.defense_adjusted_xg import adjusted_xg

    val = adjusted_xg(raw_xg=0.5, opp_defense_coef=0.01)
    # Should be clamped to some plausible band — not 50
    assert val < 2.0


def test_schedule_adjusted_projection():
    """Given a player xG/match + list of upcoming opponent defense coefs,
    produce a projected end-of-season xG sum."""
    from app.models.defense_adjusted_xg import schedule_adjusted_xg_sum

    # 0.6 xG/match × 3 matches (weak, avg, strong defenses)
    val = schedule_adjusted_xg_sum(
        xg_per_match=0.6,
        opponent_defense_coefs=[1.4, 1.0, 0.6],
    )
    # 0.6/1.4 + 0.6/1.0 + 0.6/0.6 = 0.428 + 0.6 + 1.0 = 2.028
    assert val == pytest.approx(2.03, abs=0.02)
