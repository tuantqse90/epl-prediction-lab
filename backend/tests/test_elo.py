import pandas as pd
import pytest


def test_home_win_raises_home_elo_and_lowers_away_elo():
    from app.models.elo import update_ratings

    result = update_ratings(home_elo=1500, away_elo=1500, home_goals=2, away_goals=0)
    assert result.home_new > 1500
    assert result.away_new < 1500
    # Symmetric update: total should be conserved
    assert result.home_new - 1500 == pytest.approx(1500 - result.away_new)


def test_draw_pulls_higher_elo_down_and_lower_elo_up():
    from app.models.elo import update_ratings

    result = update_ratings(home_elo=1700, away_elo=1500, home_goals=1, away_goals=1)
    # Home was higher-rated favourite; the draw penalises them.
    assert result.home_new < 1700
    assert result.away_new > 1500


def test_big_win_margin_shifts_more_than_small_margin():
    from app.models.elo import update_ratings

    small = update_ratings(home_elo=1500, away_elo=1500, home_goals=1, away_goals=0)
    big = update_ratings(home_elo=1500, away_elo=1500, home_goals=4, away_goals=0)
    assert big.home_new - 1500 > small.home_new - 1500


def test_3way_from_elo_sums_to_one_and_favours_stronger_home():
    from app.models.elo import elo_to_3way

    probs = elo_to_3way(home_elo=1600, away_elo=1400)
    assert probs.p_home_win + probs.p_draw + probs.p_away_win == pytest.approx(1.0)
    assert probs.p_home_win > probs.p_away_win


def test_3way_equal_elos_with_home_adv_still_favours_home():
    from app.models.elo import elo_to_3way

    probs = elo_to_3way(home_elo=1500, away_elo=1500)
    assert probs.p_home_win > probs.p_away_win


def test_compute_all_ratings_handles_empty_dataframe():
    from app.models.elo import compute_ratings

    empty = pd.DataFrame(columns=["date", "home_team", "away_team", "home_goals", "away_goals", "is_result"])
    ratings = compute_ratings(empty)
    assert ratings == {}


def test_compute_all_ratings_orders_by_date():
    from app.models.elo import compute_ratings

    df = pd.DataFrame([
        {"date": pd.Timestamp("2024-01-01"), "home_team": "A", "away_team": "B",
         "home_goals": 2, "away_goals": 0, "is_result": True},
        {"date": pd.Timestamp("2024-01-08"), "home_team": "B", "away_team": "A",
         "home_goals": 1, "away_goals": 3, "is_result": True},
    ])
    r = compute_ratings(df)
    # A won both → should be above 1500; B below.
    assert r["A"] > 1500
    assert r["B"] < 1500
    assert r["A"] + r["B"] == pytest.approx(3000.0, abs=0.1)


def test_compute_ratings_skips_unfinished_matches():
    from app.models.elo import compute_ratings

    df = pd.DataFrame([
        {"date": pd.Timestamp("2024-01-01"), "home_team": "A", "away_team": "B",
         "home_goals": None, "away_goals": None, "is_result": False},
    ])
    r = compute_ratings(df)
    # No matches played → no rating change → everyone stays at 1500 (or absent)
    for team in ("A", "B"):
        assert r.get(team, 1500) == pytest.approx(1500)
