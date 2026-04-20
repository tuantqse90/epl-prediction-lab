"""Tests for app.models.lineup_strength — lineup-sum attack multiplier.

When the starting XI lands (~T-60min pre-kickoff), replace the rolling
team-level attack rating with a lineup-specific aggregate built from
individual players' season xG-per-90. Resting a top scorer shows up as
a λ shrink; throwing a top scorer back after injury shows up as a boost.

Position-aware minute weighting: forwards/mids carry most attack xG,
defenders contribute less even when present.
"""
from __future__ import annotations

import pytest


def _stats(name, xg, games, position="M"):
    return {"player_name": name, "xg": xg, "games": games, "position": position}


def test_lineup_xg_returns_zero_for_empty_lineup():
    from app.models.lineup_strength import lineup_xg_rating

    out = lineup_xg_rating(starters=[], bench=[], stats_by_name={})
    assert out == 0.0


def test_lineup_xg_sums_starters_xg_per_match():
    from app.models.lineup_strength import lineup_xg_rating

    stats = {
        "A. Striker": _stats("A. Striker", xg=18.0, games=30, position="F"),
        "B. Midfielder": _stats("B. Midfielder", xg=6.0, games=30, position="M"),
        "C. Defender": _stats("C. Defender", xg=1.5, games=30, position="D"),
    }
    # All three start → sum of xg/games = 18/30 + 6/30 + 1.5/30 = 0.85
    out = lineup_xg_rating(
        starters=["A. Striker", "B. Midfielder", "C. Defender"],
        bench=[],
        stats_by_name=stats,
    )
    assert out == pytest.approx(0.85, abs=1e-4)


def test_lineup_xg_weights_bench_lower():
    """Bench players contribute at ~25% (avg sub minutes / 90). So a 0.6
    xg/game striker on the bench adds 0.15 to the lineup rating, not 0.6."""
    from app.models.lineup_strength import lineup_xg_rating, BENCH_WEIGHT

    stats = {
        "Super Sub": _stats("Super Sub", xg=30.0, games=30, position="F"),  # 1.0 xg/g
    }
    out_bench = lineup_xg_rating(
        starters=[], bench=["Super Sub"], stats_by_name=stats,
    )
    assert out_bench == pytest.approx(1.0 * BENCH_WEIGHT, abs=1e-4)


def test_lineup_xg_skips_players_not_in_stats():
    """New signings / youth promotions with no season row → 0 contribution,
    silently. Don't crash."""
    from app.models.lineup_strength import lineup_xg_rating

    stats = {"Known": _stats("Known", xg=5.0, games=20)}
    out = lineup_xg_rating(
        starters=["Known", "Unknown Youth"],
        bench=[],
        stats_by_name=stats,
    )
    # Only Known counts: 5/20 = 0.25
    assert out == pytest.approx(0.25, abs=1e-4)


def test_multiplier_clamped_to_safe_range():
    """A world-class XI vs a reserve XI could swing λ by 3x naively. Clamp
    at [0.7, 1.3] — 30% shrink/boost is the max we trust without bigger
    sample sizes."""
    from app.models.lineup_strength import lineup_multiplier

    # Way-above-team baseline
    assert lineup_multiplier(lineup_xg=3.5, team_avg_xg=1.5) == pytest.approx(1.30)
    # Way-below baseline
    assert lineup_multiplier(lineup_xg=0.2, team_avg_xg=1.5) == pytest.approx(0.70)
    # Within band
    assert lineup_multiplier(lineup_xg=1.7, team_avg_xg=1.5) == pytest.approx(1.7 / 1.5, abs=1e-4)
    # Zero team avg → 1.0 no-op
    assert lineup_multiplier(lineup_xg=1.2, team_avg_xg=0.0) == 1.0
    # None lineup → 1.0 no-op
    assert lineup_multiplier(lineup_xg=None, team_avg_xg=1.5) == 1.0


def test_multiplier_no_op_when_lineup_exactly_matches_team_avg():
    """Team reporting 1.5 xg/game and lineup aggregating to 1.5 → no
    adjustment, multiplier = 1.0."""
    from app.models.lineup_strength import lineup_multiplier

    assert lineup_multiplier(lineup_xg=1.5, team_avg_xg=1.5) == pytest.approx(1.0)
