"""Title-race Monte Carlo — pure simulator over remaining fixtures.

Takes current points + remaining (home_team, away_team, lambda_h, lambda_a)
rows and runs N sims, drawing goals from independent Poisson(λ) per side.
Returns per-team finish distribution (P(champions), P(top-4), P(relegate),
mean_points, P(position=k)).
"""
from __future__ import annotations

import pytest


def test_simulate_zero_remaining_returns_current_standings():
    """With no fixtures left, every sim returns the current table untouched.

    P(champions) = 1.0 for the leader; 0 for the rest.
    """
    from app.models.title_race import simulate_title_race

    standings = {
        "A": {"played": 38, "points": 85, "gd": 60, "gf": 80},
        "B": {"played": 38, "points": 80, "gd": 50, "gf": 70},
        "C": {"played": 38, "points": 60, "gd": 10, "gf": 45},
    }
    result = simulate_title_race(
        standings=standings,
        remaining=[],
        n_simulations=500,
        seed=42,
    )
    assert result["A"]["p_champions"] == 1.0
    assert result["B"]["p_champions"] == 0.0
    assert result["C"]["p_champions"] == 0.0
    # Mean final points = current points (no fixtures).
    assert result["A"]["mean_points"] == 85.0


def test_leader_with_one_remaining_must_not_lose_for_rival_to_catch_up():
    """Classic two-horse race. A has 85, B has 83. A needs ≥ 1 pt from their
    last match vs Z to clinch. Sanity-check: A's title share > 0.5 under
    any reasonable lambda pair."""
    from app.models.title_race import simulate_title_race

    standings = {
        "A": {"played": 37, "points": 85, "gd": 40, "gf": 70},
        "B": {"played": 38, "points": 83, "gd": 38, "gf": 65},
        "Z": {"played": 37, "points": 40, "gd": -10, "gf": 30},
    }
    remaining = [
        {"home": "A", "away": "Z", "lambda_h": 2.0, "lambda_a": 0.8},
    ]
    res = simulate_title_race(
        standings=standings, remaining=remaining, n_simulations=2000, seed=7,
    )
    # A averages 2-0; loses only when Z wins. Should be champion > 80%.
    assert res["A"]["p_champions"] > 0.8
    # Sum of P(champions) must = 1 exactly (one title per sim).
    total_p = sum(t["p_champions"] for t in res.values())
    assert total_p == pytest.approx(1.0, abs=0.001)


def test_seed_reproducibility():
    from app.models.title_race import simulate_title_race

    standings = {
        "X": {"played": 30, "points": 55, "gd": 15, "gf": 50},
        "Y": {"played": 30, "points": 52, "gd": 10, "gf": 45},
    }
    remaining = [{"home": "X", "away": "Y", "lambda_h": 1.4, "lambda_a": 1.2}]
    a = simulate_title_race(standings=standings, remaining=remaining, n_simulations=500, seed=123)
    b = simulate_title_race(standings=standings, remaining=remaining, n_simulations=500, seed=123)
    assert a["X"]["p_champions"] == b["X"]["p_champions"]


def test_tiebreak_goal_difference_then_goals_for():
    """Two teams end with same points → goal difference decides. If GD
    also ties → goals for. Model this in the sim."""
    from app.models.title_race import simulate_title_race

    # Both teams on 85 pts, only 1 match left each, both vs weak common
    # opponent. We set λ so each draws 1-1 with high probability (no pts
    # change vs current differential).
    standings = {
        "A": {"played": 37, "points": 85, "gd": 30, "gf": 60},
        "B": {"played": 37, "points": 85, "gd": 30, "gf": 55},
        "C": {"played": 38, "points": 20, "gd": -50, "gf": 20},
    }
    # No more fixtures — A and B locked on 85 / GD 30 / but A has more GF.
    result = simulate_title_race(
        standings=standings, remaining=[], n_simulations=100, seed=0,
    )
    assert result["A"]["p_champions"] == 1.0
    assert result["B"]["p_champions"] == 0.0


def test_relegation_probability_for_bottom_team():
    """P(relegate) = P(final position in bottom 3) for each team."""
    from app.models.title_race import simulate_title_race

    standings = {chr(65 + i): {"played": 30, "points": 60 - i * 4, "gd": 20 - i * 3, "gf": 40 - i} for i in range(20)}
    result = simulate_title_race(
        standings=standings, remaining=[], n_simulations=50, seed=0,
        relegation_count=3,
    )
    # Bottom three letters (R, S, T) must have P(relegate) = 1.0
    for tc in "RST":
        assert result[tc]["p_relegate"] == 1.0
    # Leader must have 0.
    assert result["A"]["p_relegate"] == 0.0


def test_top_four_probability_when_fixture_outcomes_uncertain():
    """Mid-table team with fixtures left can finish above or below top-4
    depending on Poisson draws — P(top_4) must be strictly between 0 and 1."""
    from app.models.title_race import simulate_title_race

    # Eight teams clustered close in points; 2 fixtures each to go.
    standings = {chr(65 + i): {"played": 36, "points": 65 - i, "gd": 15 - i, "gf": 55 - i} for i in range(8)}
    remaining = []
    # Let mid-table teams play each other so outcomes matter.
    teams = list(standings.keys())
    remaining.append({"home": "D", "away": "E", "lambda_h": 1.5, "lambda_a": 1.3})
    remaining.append({"home": "E", "away": "F", "lambda_h": 1.4, "lambda_a": 1.4})
    remaining.append({"home": "F", "away": "D", "lambda_h": 1.3, "lambda_a": 1.3})
    res = simulate_title_race(
        standings=standings, remaining=remaining, n_simulations=2000, seed=1,
    )
    # E's top-4 probability must be non-trivial (they can pass B, C)
    assert 0.0 < res["E"]["p_top_four"] < 1.0
