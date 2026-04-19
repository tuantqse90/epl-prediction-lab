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
