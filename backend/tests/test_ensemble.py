import pytest


def test_predict_match_with_elo_zero_weight_matches_poisson_only():
    from app.models.poisson import predict_match

    a = predict_match(1.5, 1.2, rho=-0.15, temperature=1.0)
    b = predict_match(
        1.5, 1.2, rho=-0.15, temperature=1.0,
        elo_probs=(0.1, 0.1, 0.8),    # anything — weight 0 must ignore it
        elo_weight=0.0,
    )
    assert a.p_home_win == pytest.approx(b.p_home_win)
    assert a.p_draw == pytest.approx(b.p_draw)
    assert a.p_away_win == pytest.approx(b.p_away_win)


def test_predict_match_ensemble_sums_to_one():
    from app.models.poisson import predict_match

    p = predict_match(
        1.5, 1.2, rho=-0.15,
        elo_probs=(0.4, 0.3, 0.3), elo_weight=0.5,
    )
    assert p.p_home_win + p.p_draw + p.p_away_win == pytest.approx(1.0)


def test_ensemble_pulls_toward_elo_when_weight_high():
    from app.models.poisson import predict_match

    strong_poisson = predict_match(2.2, 0.9, rho=-0.15)  # heavy home favourite
    # Elo disagrees: says coin-flip
    blended = predict_match(
        2.2, 0.9, rho=-0.15,
        elo_probs=(0.4, 0.25, 0.35), elo_weight=0.5,
    )
    # Blended home-win prob must sit between Poisson (high) and Elo (0.4)
    assert 0.4 < blended.p_home_win < strong_poisson.p_home_win
