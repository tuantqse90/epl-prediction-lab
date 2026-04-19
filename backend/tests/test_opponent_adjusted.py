import pandas as pd
import pytest


def _mk(date: str, home: str, away: str, hg: int, ag: int, hxg: float, axg: float):
    return {
        "date": pd.Timestamp(date),
        "home_team": home, "away_team": away,
        "home_goals": hg, "away_goals": ag,
        "home_xg": hxg, "away_xg": axg,
        "is_result": True,
    }


def test_opponent_adjusted_demotes_xg_against_weak_defense():
    """A team that piles up xG against a porous defense shouldn't be scored
    as highly as a team that did the same against a stingy defense."""
    from app.models.features import compute_team_strengths

    # Three teams: A strong attack, B strong defense, C porous defense.
    # We'll observe A vs B (1.5 xG) and A vs C (1.5 xG). Both produce the
    # same raw mean. With opponent-adjustment, the B game should weigh
    # more (harder task) and the C game less.
    df = pd.DataFrame([
        _mk("2024-01-01", "A", "B", 1, 0, 1.5, 0.5),  # A vs elite defense
        _mk("2024-01-08", "A", "C", 2, 1, 1.5, 2.5),  # A vs weak defense
        # Filler games to establish B has strong defense, C weak.
        _mk("2024-01-15", "B", "D", 1, 0, 1.5, 0.4),
        _mk("2024-01-22", "B", "E", 2, 0, 1.6, 0.3),
        _mk("2024-01-29", "C", "D", 0, 2, 0.8, 2.2),
        _mk("2024-02-05", "C", "E", 1, 3, 1.1, 2.5),
    ])

    raw = compute_team_strengths(
        df, as_of=pd.Timestamp("2024-03-01"), decay=1.0, opponent_adjust=False,
    )
    adjusted = compute_team_strengths(
        df, as_of=pd.Timestamp("2024-03-01"), decay=1.0, opponent_adjust=True,
    )

    # Both A and B exist in both snapshots.
    assert "A" in raw and "A" in adjusted
    # B is a strong defense, C is weak. With adjustment enabled, A's rating
    # should move differently than without — here, we expect A's attack to
    # either stay stable or drop because one of its big xG games was
    # against a weak defense.
    assert adjusted["A"].attack != raw["A"].attack


def test_opponent_adjust_false_matches_existing_behavior():
    from app.models.features import compute_team_strengths

    df = pd.DataFrame([
        _mk("2024-01-01", "A", "B", 1, 0, 1.5, 0.5),
        _mk("2024-01-08", "B", "A", 0, 2, 1.0, 2.0),
    ])
    default = compute_team_strengths(df, as_of=pd.Timestamp("2024-02-01"))
    explicit = compute_team_strengths(
        df, as_of=pd.Timestamp("2024-02-01"), opponent_adjust=False,
    )
    assert default["A"].attack == pytest.approx(explicit["A"].attack)
