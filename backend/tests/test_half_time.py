import pytest


def test_halftime_split_returns_three_probs_summing_to_one():
    from app.models.half_time import ht_winner_probs

    probs = ht_winner_probs(lam_home=1.8, lam_away=1.2)
    total = probs.p_home_lead + probs.p_draw + probs.p_away_lead
    assert total == pytest.approx(1.0)


def test_halftime_stronger_home_leads_more_often_at_ht_than_away():
    from app.models.half_time import ht_winner_probs

    probs = ht_winner_probs(lam_home=2.5, lam_away=0.8)
    assert probs.p_home_lead > probs.p_away_lead


def test_htft_grid_sums_to_one_across_9_cells():
    from app.models.half_time import htft_grid

    grid = htft_grid(lam_home=1.5, lam_away=1.2)
    # 3 HT states × 3 FT states
    total = sum(grid.cells.values())
    assert total == pytest.approx(1.0)
    assert len(grid.cells) == 9


def test_htft_home_home_is_most_likely_for_heavy_favourite():
    from app.models.half_time import htft_grid

    grid = htft_grid(lam_home=2.7, lam_away=0.6)
    # Most probable cell for heavy favourite → Home/Home
    best_cell = max(grid.cells.items(), key=lambda x: x[1])[0]
    assert best_cell == ("H", "H")
