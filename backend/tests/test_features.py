"""TDD tests for features — team strength + per-match lambda derivation.

Input schema matches `soccerdata.Understat.read_schedule()`:
    columns include date, home_team, away_team, home_xg, away_xg, is_result
Tests use tiny synthetic DataFrames so no network is required.
"""

from __future__ import annotations

import pandas as pd
import pytest


def _toy_schedule() -> pd.DataFrame:
    """3 teams, round-robin home+away, fixed xG values for predictable arithmetic."""
    rows = [
        # A strong (high xG for, low against); C weak (opposite); B average
        ("2024-08-10", "A", "C", 3.0, 0.5),
        ("2024-08-17", "C", "A", 0.4, 2.6),
        ("2024-08-24", "B", "A", 1.0, 2.0),
        ("2024-08-31", "A", "B", 2.2, 0.9),
        ("2024-09-07", "B", "C", 1.8, 0.7),
        ("2024-09-14", "C", "B", 0.6, 1.6),
    ]
    df = pd.DataFrame(rows, columns=["date", "home_team", "away_team", "home_xg", "away_xg"])
    df["date"] = pd.to_datetime(df["date"])
    df["is_result"] = True
    return df


def test_compute_team_strengths_returns_entry_per_team():
    from app.models.features import compute_team_strengths

    df = _toy_schedule()
    strengths = compute_team_strengths(df, as_of=pd.Timestamp("2024-10-01"))

    assert set(strengths.keys()) == {"A", "B", "C"}
    for team, s in strengths.items():
        assert s.attack > 0
        assert s.defense > 0


def test_compute_team_strengths_excludes_future_matches():
    """Strength must only see matches strictly before `as_of`."""
    from app.models.features import compute_team_strengths

    df = _toy_schedule()
    early = compute_team_strengths(df, as_of=pd.Timestamp("2024-08-20"))
    # Before 2024-08-20 only 2 matches are done: A-C and C-A.
    # Team B has played zero matches yet → should be absent or default(1.0, 1.0).
    assert "B" not in early or (early["B"].attack == 1.0 and early["B"].defense == 1.0)


def test_compute_team_strengths_attack_ordering_reflects_xg():
    """Team A (high xG for) must have higher attack strength than team C (low)."""
    from app.models.features import compute_team_strengths

    df = _toy_schedule()
    s = compute_team_strengths(df, as_of=pd.Timestamp("2024-10-01"))
    assert s["A"].attack > s["B"].attack > s["C"].attack
    # And defense — lower xG conceded = better defense = LOWER defense factor
    assert s["A"].defense < s["B"].defense < s["C"].defense


def test_match_lambdas_applies_home_advantage():
    from app.models.features import TeamStrength, match_lambdas

    home = TeamStrength(attack=1.2, defense=0.9)
    away = TeamStrength(attack=1.0, defense=1.0)
    league_avg_goals = 1.4

    lam_h, lam_a = match_lambdas(home, away, league_avg_goals=league_avg_goals, home_adv=1.3)

    # lam_h = 1.4 * 1.2 * 1.0 * 1.3 = 2.184
    assert lam_h == pytest.approx(1.4 * 1.2 * 1.0 * 1.3)
    # lam_a = 1.4 * 1.0 * 0.9 = 1.26
    assert lam_a == pytest.approx(1.4 * 1.0 * 0.9)


def test_match_lambdas_stronger_home_produces_higher_home_lambda():
    from app.models.features import TeamStrength, match_lambdas

    strong = TeamStrength(attack=1.4, defense=0.7)
    weak = TeamStrength(attack=0.7, defense=1.4)

    lam_h, lam_a = match_lambdas(strong, weak, league_avg_goals=1.4)
    assert lam_h > lam_a
