"""TDD tests for Dixon-Coles Poisson engine."""

import numpy as np
import pytest


def test_score_matrix_shape_and_sum():
    """6x6 matrix summing to ~1 when max_goals=5 (tail is small)."""
    from app.models.poisson import poisson_score_matrix

    m = poisson_score_matrix(lam_home=1.5, lam_away=1.2, max_goals=5)

    assert m.shape == (6, 6)
    # Most of the mass sits inside 0..5 for modest lambdas
    assert 0.95 < m.sum() < 1.0


def test_score_matrix_is_independent_product():
    """M[i, j] must equal P(home=i) * P(away=j) — independence assumption."""
    from scipy.stats import poisson

    from app.models.poisson import poisson_score_matrix

    lam_h, lam_a = 1.8, 1.1
    m = poisson_score_matrix(lam_h, lam_a, max_goals=5)

    for i in range(6):
        for j in range(6):
            expected = poisson.pmf(i, lam_h) * poisson.pmf(j, lam_a)
            assert m[i, j] == pytest.approx(expected, rel=1e-9)


def test_score_matrix_rejects_non_positive_lambda():
    from app.models.poisson import poisson_score_matrix

    with pytest.raises(ValueError):
        poisson_score_matrix(lam_home=0, lam_away=1.0)
    with pytest.raises(ValueError):
        poisson_score_matrix(lam_home=1.0, lam_away=-0.1)


# --- Dixon-Coles tau correction ---


def test_dc_tau_rho_zero_is_identity():
    """With rho=0 the correction must be 1 for every cell — DC collapses to plain Poisson."""
    from app.models.poisson import dixon_coles_tau

    for h, a in [(0, 0), (0, 1), (1, 0), (1, 1), (2, 3), (4, 0)]:
        assert dixon_coles_tau(h, a, lam_home=1.5, lam_away=1.2, rho=0.0) == 1.0


def test_dc_tau_matches_formula_for_low_scoring_cells():
    """tau values for the 4 special cells follow Dixon-Coles (1997) exactly."""
    from app.models.poisson import dixon_coles_tau

    lam_h, lam_a, rho = 1.5, 1.2, 0.1

    assert dixon_coles_tau(0, 0, lam_h, lam_a, rho) == pytest.approx(1 - lam_h * lam_a * rho)
    assert dixon_coles_tau(0, 1, lam_h, lam_a, rho) == pytest.approx(1 + lam_h * rho)
    assert dixon_coles_tau(1, 0, lam_h, lam_a, rho) == pytest.approx(1 + lam_a * rho)
    assert dixon_coles_tau(1, 1, lam_h, lam_a, rho) == pytest.approx(1 - rho)


def test_dc_tau_is_identity_outside_four_cells():
    """Any scoreline with max(home, away) >= 2 must get tau=1 regardless of rho."""
    from app.models.poisson import dixon_coles_tau

    for h, a in [(2, 0), (0, 2), (2, 2), (3, 1), (1, 3), (5, 5)]:
        assert dixon_coles_tau(h, a, lam_home=1.5, lam_away=1.2, rho=0.1) == 1.0


# --- apply_dixon_coles: cell-wise multiplication by tau ---


def test_apply_dc_with_rho_zero_is_noop():
    from app.models.poisson import apply_dixon_coles, poisson_score_matrix

    base = poisson_score_matrix(1.5, 1.2)
    out = apply_dixon_coles(base, lam_home=1.5, lam_away=1.2, rho=0.0)
    np.testing.assert_allclose(out, base)


def test_apply_dc_only_touches_four_cells():
    from app.models.poisson import apply_dixon_coles, poisson_score_matrix

    lam_h, lam_a, rho = 1.5, 1.2, 0.1
    base = poisson_score_matrix(lam_h, lam_a)
    out = apply_dixon_coles(base, lam_h, lam_a, rho)

    # Cells outside the 2x2 corner are untouched
    for i in range(6):
        for j in range(6):
            if i >= 2 or j >= 2:
                assert out[i, j] == pytest.approx(base[i, j])

    # The 4 DC cells are scaled by tau
    assert out[0, 0] == pytest.approx(base[0, 0] * (1 - lam_h * lam_a * rho))
    assert out[0, 1] == pytest.approx(base[0, 1] * (1 + lam_h * rho))
    assert out[1, 0] == pytest.approx(base[1, 0] * (1 + lam_a * rho))
    assert out[1, 1] == pytest.approx(base[1, 1] * (1 - rho))


# --- collapse_1x2: reduce matrix to (p_home, p_draw, p_away) ---


def test_collapse_1x2_sums_to_one():
    from app.models.poisson import collapse_1x2, poisson_score_matrix

    m = poisson_score_matrix(1.5, 1.2)
    p_h, p_d, p_a = collapse_1x2(m)
    assert p_h + p_d + p_a == pytest.approx(1.0)


def test_collapse_1x2_higher_home_lambda_favors_home():
    from app.models.poisson import collapse_1x2, poisson_score_matrix

    m = poisson_score_matrix(lam_home=2.2, lam_away=0.8)
    p_h, p_d, p_a = collapse_1x2(m)
    assert p_h > p_a
    assert p_h > p_d


def test_collapse_1x2_equal_lambdas_near_symmetric():
    from app.models.poisson import collapse_1x2, poisson_score_matrix

    m = poisson_score_matrix(lam_home=1.4, lam_away=1.4)
    p_h, p_d, p_a = collapse_1x2(m)
    assert p_h == pytest.approx(p_a, abs=1e-9)


# --- top_scorelines ---


def test_top_scorelines_returns_n_sorted_desc():
    from app.models.poisson import poisson_score_matrix, top_scorelines

    m = poisson_score_matrix(1.5, 1.2)
    top = top_scorelines(m, n=5)

    assert len(top) == 5
    probs = [p for _, _, p in top]
    assert probs == sorted(probs, reverse=True)


def test_top_scorelines_probs_match_matrix_cells():
    from app.models.poisson import poisson_score_matrix, top_scorelines

    m = poisson_score_matrix(1.5, 1.2)
    top = top_scorelines(m, n=3)

    for h, a, p in top:
        assert m[h, a] == pytest.approx(p)


# --- predict_match: end-to-end orchestration ---


def test_predict_match_probs_sum_to_one():
    from app.models.poisson import predict_match

    r = predict_match(lam_home=1.5, lam_away=1.2, rho=0.1)
    assert r.p_home_win + r.p_draw + r.p_away_win == pytest.approx(1.0)


def test_predict_match_returns_expected_goals_from_lambdas():
    from app.models.poisson import predict_match

    r = predict_match(lam_home=1.8, lam_away=0.9)
    assert r.expected_home_goals == pytest.approx(1.8)
    assert r.expected_away_goals == pytest.approx(0.9)


def test_predict_match_top_scorelines_len_and_order():
    from app.models.poisson import predict_match

    r = predict_match(lam_home=1.5, lam_away=1.2, top_n=5)
    assert len(r.top_scorelines) == 5
    probs = [p for _, _, p in r.top_scorelines]
    assert probs == sorted(probs, reverse=True)


# --- temperature_scale_1x2 ---


def test_temperature_one_is_identity():
    from app.models.poisson import temperature_scale_1x2

    out = temperature_scale_1x2(0.62, 0.22, 0.16, temperature=1.0)
    assert out == pytest.approx((0.62, 0.22, 0.16))


def test_temperature_above_one_flattens_distribution():
    """T > 1 must reduce the max and raise the min — same ordering preserved."""
    from app.models.poisson import temperature_scale_1x2

    p_h, p_d, p_a = 0.70, 0.20, 0.10
    out = temperature_scale_1x2(p_h, p_d, p_a, temperature=1.5)
    assert sum(out) == pytest.approx(1.0)
    assert out[0] < p_h       # max shrinks
    assert out[2] > p_a       # min grows
    # Ordering preserved
    assert out[0] > out[1] > out[2]


def test_temperature_below_one_sharpens_distribution():
    from app.models.poisson import temperature_scale_1x2

    p_h, p_d, p_a = 0.50, 0.30, 0.20
    out = temperature_scale_1x2(p_h, p_d, p_a, temperature=0.5)
    assert sum(out) == pytest.approx(1.0)
    assert out[0] > p_h
    assert out[2] < p_a


def test_temperature_always_normalizes():
    from app.models.poisson import temperature_scale_1x2

    for t in (0.8, 1.0, 1.2, 1.8, 3.0):
        out = temperature_scale_1x2(0.55, 0.25, 0.20, temperature=t)
        assert sum(out) == pytest.approx(1.0)


def test_predict_match_temperature_softens_winner_prob():
    from app.models.poisson import predict_match

    raw = predict_match(lam_home=2.0, lam_away=0.8, rho=-0.15, temperature=1.0)
    soft = predict_match(lam_home=2.0, lam_away=0.8, rho=-0.15, temperature=1.4)

    assert soft.p_home_win < raw.p_home_win
    assert soft.p_home_win + soft.p_draw + soft.p_away_win == pytest.approx(1.0)


# --- live_probabilities (in-play recompute) ---


def test_live_probs_at_kickoff_match_full_poisson():
    """At minute 0 with score 0-0 the live probs must equal the pre-match prediction."""
    from app.models.poisson import live_probabilities, predict_match

    lh, la = 1.8, 0.9
    pre = predict_match(lh, la, rho=-0.15, temperature=1.0)
    live = live_probabilities(lh, la, 0, 0, minute=0, rho=-0.15)

    assert live.p_home_win == pytest.approx(pre.p_home_win, abs=0.02)
    assert live.p_draw == pytest.approx(pre.p_draw, abs=0.02)
    assert live.p_away_win == pytest.approx(pre.p_away_win, abs=0.02)


def test_live_probs_at_final_whistle_locked_to_score():
    """At minute 90 the probs collapse to the actual result — no further goals possible."""
    from app.models.poisson import live_probabilities

    # Home leading 1-0 at 90'
    r = live_probabilities(2.0, 1.2, 1, 0, minute=90)
    assert r.p_home_win == pytest.approx(1.0, abs=1e-6)
    assert r.p_draw + r.p_away_win == pytest.approx(0.0, abs=1e-6)

    # Draw 2-2 at 90'
    r = live_probabilities(2.0, 1.2, 2, 2, minute=90)
    assert r.p_draw == pytest.approx(1.0, abs=1e-6)


def test_live_probs_sum_to_one():
    from app.models.poisson import live_probabilities

    for (h, a, minute) in [(0, 0, 15), (1, 0, 30), (1, 1, 60), (0, 2, 75), (3, 1, 85)]:
        r = live_probabilities(1.7, 1.3, h, a, minute=minute)
        assert r.p_home_win + r.p_draw + r.p_away_win == pytest.approx(1.0, abs=1e-6)


def test_live_probs_lead_strengthens_winning_side():
    """Up 1-0 at half time should raise P(home win) above pre-match."""
    from app.models.poisson import live_probabilities

    pre = live_probabilities(1.5, 1.5, 0, 0, minute=0)
    leading = live_probabilities(1.5, 1.5, 1, 0, minute=45)
    assert leading.p_home_win > pre.p_home_win
    assert leading.p_away_win < pre.p_away_win


def test_live_probs_expected_remaining_goals_scale_with_time():
    """Remaining goals distribution should shrink as minutes elapse."""
    from app.models.poisson import live_probabilities

    early = live_probabilities(1.8, 1.2, 0, 0, minute=10)
    late = live_probabilities(1.8, 1.2, 0, 0, minute=80)
    # Later in the game, a 0-0 is more likely to stay 0-0 → draw prob rises
    assert late.p_draw > early.p_draw


def test_predict_match_rho_sign_follows_dc_formula():
    """Sanity-check the DC sign convention used here.

    τ(0,0) = 1 - λ_h·λ_a·ρ and τ(1,1) = 1 - ρ, so positive ρ *shrinks* the two
    main draw cells (0-0 and 1-1) and lifts the 1-goal margin cells. For
    empirical EPL data the fitted ρ is typically **negative** (~-0.1) — that's
    what lifts draws above plain Poisson. Calibrating ρ is tracked in
    docs/environment.md under "open questions".
    """
    from app.models.poisson import predict_match

    plain = predict_match(lam_home=1.3, lam_away=1.3, rho=0.0)
    pos_rho = predict_match(lam_home=1.3, lam_away=1.3, rho=0.1)
    neg_rho = predict_match(lam_home=1.3, lam_away=1.3, rho=-0.1)

    assert pos_rho.p_draw < plain.p_draw
    assert neg_rho.p_draw > plain.p_draw
