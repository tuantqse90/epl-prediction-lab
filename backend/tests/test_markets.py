import numpy as np
import pytest


def test_prob_over_2_5_counts_cells_with_sum_greater_than_25():
    from app.models.markets import prob_over
    # 3x3 matrix where each cell is 1/9 (uniform)
    m = np.ones((3, 3)) / 9.0
    # sums: 0 (0+0), 1 (0+1 / 1+0), 2, 3, 4 possibilities
    # over 2.5 means home+away >= 3 → (1,2) (2,1) (2,2)
    p = prob_over(m, 2.5)
    assert p == pytest.approx(3.0 / 9.0)


def test_prob_over_0_5_is_one_minus_p_00():
    from app.models.markets import prob_over
    m = np.zeros((4, 4))
    m[0, 0] = 0.3
    m[1, 0] = 0.4
    m[0, 1] = 0.3
    assert prob_over(m, 0.5) == pytest.approx(0.7)


def test_prob_btts_counts_only_cells_where_both_nonzero():
    from app.models.markets import prob_btts
    m = np.zeros((3, 3))
    m[0, 0] = 0.1
    m[1, 0] = 0.2
    m[0, 1] = 0.2
    m[1, 1] = 0.3
    m[2, 1] = 0.2
    assert prob_btts(m) == pytest.approx(0.5)


def test_kelly_positive_when_prob_exceeds_fair():
    from app.models.markets import kelly_stake
    # odds=2.0 means fair prob is 0.5. If model says 0.6, edge positive.
    s = kelly_stake(prob=0.6, odds=2.0)
    assert s == pytest.approx((0.6 * 2.0 - 1.0) / (2.0 - 1.0))
    assert 0 < s < 1


def test_kelly_zero_when_no_edge():
    from app.models.markets import kelly_stake
    assert kelly_stake(prob=0.4, odds=2.0) == 0.0
    assert kelly_stake(prob=0.5, odds=2.0) == 0.0


def test_kelly_fractional_default_clamped_to_25_percent():
    from app.models.markets import kelly_stake
    # Extreme edge: prob=0.9, odds=5 → full Kelly = 0.875, clamp → 0.25.
    assert kelly_stake(prob=0.9, odds=5.0) == pytest.approx(0.25)


# ── Asian handicap math ──────────────────────────────────────────────────────


def _simple_matrix():
    """3x3 matrix with cells summing to 1. Handy for hand-checking AH/SGP."""
    m = np.zeros((3, 3))
    m[0, 0] = 0.10   # 0-0
    m[1, 0] = 0.20   # 1-0
    m[0, 1] = 0.15   # 0-1
    m[1, 1] = 0.15   # 1-1
    m[2, 0] = 0.15   # 2-0
    m[0, 2] = 0.10   # 0-2
    m[2, 1] = 0.10   # 2-1
    m[1, 2] = 0.05   # 1-2
    return m


def test_ah_half_line_plus_zero_five_home_wins_on_draw_or_win():
    from app.models.markets import prob_asian_handicap
    m = _simple_matrix()
    # +0.5 means home covers if home_goals + 0.5 > away_goals, i.e.
    # home wins outright OR draws. Cells: 0-0, 1-0, 1-1, 2-0, 2-1 = 0.70
    p = prob_asian_handicap(m, line=+0.5, side="home")
    assert p == pytest.approx(0.70)


def test_ah_half_line_minus_one_home_covers_only_if_wins_by_2():
    from app.models.markets import prob_asian_handicap
    m = _simple_matrix()
    # -1 handicap: home wins if home_goals - 1 > away_goals. -1.5 line: must
    # win by 2+. Qualifying cells: 2-0 = 0.15
    p = prob_asian_handicap(m, line=-1.5, side="home")
    assert p == pytest.approx(0.15)


def test_ah_integer_line_returns_effective_prob_with_half_push_credit():
    from app.models.markets import prob_asian_handicap
    m = _simple_matrix()
    # 0.0 line means home wins outright → stake back on draw → lose if home
    # loses. Effective prob = P(home_wins) + 0.5 * P(draw).
    # Home wins: 1-0(0.20) + 2-0(0.15) + 2-1(0.10) = 0.45
    # Draws: 0-0(0.10) + 1-1(0.15) = 0.25
    p = prob_asian_handicap(m, line=0.0, side="home")
    assert p == pytest.approx(0.45 + 0.5 * 0.25)


def test_ah_away_side_mirrors_home():
    from app.models.markets import prob_asian_handicap
    m = _simple_matrix()
    # At +0.5 home, home covers = wins or draws (0.70). Away side at -0.5 is
    # the opposing bet → should be 1 − 0.70 = 0.30 on the same matrix mass.
    p_home = prob_asian_handicap(m, line=+0.5, side="home")
    p_away = prob_asian_handicap(m, line=-0.5, side="away")
    assert p_home + p_away == pytest.approx(1.0)


def test_ah_quarter_line_averages_two_half_lines():
    from app.models.markets import prob_asian_handicap
    m = _simple_matrix()
    # +0.75 = half stake at +0.5 + half stake at +1.0.
    # +0.5 on home → 0.70 (as above). +1.0 on home → effective:
    #   home outright OR draw (win) OR loss by 1 (push):
    #   wins = 0.45, draws = 0.25, losses-by-1: 0-1(0.15) + 1-2(0.05) = 0.20
    #   effective = 0.45 + 0.25 + 0.5 * 0.20 = 0.80
    # Average of 0.70 and 0.80 = 0.75.
    p = prob_asian_handicap(m, line=+0.75, side="home")
    assert p == pytest.approx(0.75, abs=1e-6)


# ── Same-game parlay (SGP) ───────────────────────────────────────────────────


def test_sgp_btts_and_over_counts_cells_meeting_both():
    from app.models.markets import prob_sgp_btts_and_over
    m = _simple_matrix()
    # BTTS & Over 2.5 → both teams score AND total > 2.5.
    # Cells with h≥1, a≥1, h+a≥3: 2-1(0.10) + 1-2(0.05) = 0.15
    p = prob_sgp_btts_and_over(m, line=2.5)
    assert p == pytest.approx(0.15)


def test_sgp_is_not_product_of_marginals_when_correlated():
    """Sanity: correlated SGP prob should differ from naive P(A)*P(B)."""
    from app.models.markets import prob_sgp_btts_and_over, prob_btts, prob_over
    m = _simple_matrix()
    p_joint = prob_sgp_btts_and_over(m, line=2.5)
    naive = prob_btts(m) * prob_over(m, 2.5)
    # They're NOT equal — the joint is strictly less than or equal to each
    # marginal, but not the product for a correlated matrix.
    assert abs(p_joint - naive) > 0.001
