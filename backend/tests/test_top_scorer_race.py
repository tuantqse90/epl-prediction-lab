"""Top-scorer race — project end-of-season goals from current rate."""
from __future__ import annotations

import pytest


def test_projection_linear_in_xg_per_match():
    """Player with 10 goals + 0.6 xG/match in 20 games, with 5 team games
    remaining → projected end = 10 + 0.6×5 = 13.0."""
    from app.models.top_scorer_race import project_end_of_season

    out = project_end_of_season(
        current_goals=10,
        xg_per_match=0.6,
        team_remaining=5,
    )
    assert out == pytest.approx(13.0)


def test_zero_remaining_returns_current():
    from app.models.top_scorer_race import project_end_of_season

    assert project_end_of_season(current_goals=22, xg_per_match=0.5, team_remaining=0) == 22


def test_clamp_min_and_max_sanity():
    """Should never project a NEGATIVE projection or absurd blow-up."""
    from app.models.top_scorer_race import project_end_of_season

    assert project_end_of_season(current_goals=5, xg_per_match=-0.1, team_remaining=10) == 5
    # Upper-bound sanity: 30 games left × 1.5 xG/match = +45; clamp to 999 not needed
    assert project_end_of_season(current_goals=0, xg_per_match=1.5, team_remaining=30) == pytest.approx(45.0)


def test_rank_by_projected_then_current_then_xg():
    """Ties on projected → break on current goals → break on xG total."""
    from app.models.top_scorer_race import rank_scorer_race

    rows = [
        {"player": "A", "goals": 15, "xg": 12.0, "games": 30, "team_remaining": 8},
        {"player": "B", "goals": 14, "xg": 13.5, "games": 30, "team_remaining": 8},
        {"player": "C", "goals": 16, "xg": 11.0, "games": 30, "team_remaining": 8},
    ]
    out = rank_scorer_race(rows)
    # Projections:
    # A: 15 + 12/30 * 8 = 15 + 3.20 = 18.20
    # B: 14 + 13.5/30 * 8 = 14 + 3.60 = 17.60
    # C: 16 + 11/30 * 8 = 16 + 2.93 = 18.93
    assert out[0]["player"] == "C"
    assert out[1]["player"] == "A"
    assert out[2]["player"] == "B"
    # Delta to leader
    assert out[0]["gap_to_leader"] == 0
    assert out[1]["gap_to_leader"] < 0  # negative = behind


def test_zero_games_played_handled():
    """Brand-new signing with 0 games played — xg_per_match division by 0
    must not crash."""
    from app.models.top_scorer_race import project_end_of_season, rank_scorer_race

    # Direct: 0/0 should return current goals (no data to project from)
    assert project_end_of_season(current_goals=0, xg_per_match=0.0, team_remaining=10) == 0
    rows = [
        {"player": "New", "goals": 0, "xg": 0.0, "games": 0, "team_remaining": 10},
        {"player": "Est", "goals": 5, "xg": 5.0, "games": 10, "team_remaining": 10},
    ]
    out = rank_scorer_race(rows)
    # Est projects 5 + 0.5*10 = 10; New projects 0
    assert out[0]["player"] == "Est"
