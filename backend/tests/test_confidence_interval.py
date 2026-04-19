import pandas as pd
import pytest


def _row(date: str, home: str, away: str, hxg: float, axg: float, hg: int, ag: int):
    return {
        "date": pd.Timestamp(date), "home_team": home, "away_team": away,
        "home_xg": hxg, "away_xg": axg, "home_goals": hg, "away_goals": ag,
        "is_result": True,
    }


def test_bootstrap_ci_returns_interval_containing_point_estimate():
    from app.models.ci import bootstrap_1x2_ci
    from app.models.features import compute_team_strengths, match_lambdas
    from app.models.poisson import predict_match

    df = pd.DataFrame([
        _row("2024-01-01", "A", "B", 1.6, 1.0, 2, 1),
        _row("2024-01-08", "A", "C", 1.9, 0.9, 3, 0),
        _row("2024-01-15", "B", "A", 1.1, 1.8, 1, 2),
        _row("2024-01-22", "C", "A", 0.8, 1.7, 0, 1),
        _row("2024-02-01", "B", "C", 1.4, 1.2, 2, 2),
        _row("2024-02-08", "C", "B", 1.3, 1.3, 1, 1),
    ])
    # Align point-estimate hyperparams with the bootstrap internals so the
    # CI is expected to bracket it (modulo bootstrap sampling noise).
    strengths = compute_team_strengths(
        df, as_of=pd.Timestamp("2024-03-01"),
        decay=0.9, opponent_adjust=True,
    )
    lam_h, lam_a = match_lambdas(strengths["A"], strengths["B"], league_avg_goals=1.3)
    pt = predict_match(lam_h, lam_a, rho=-0.15, temperature=1.35)

    ci = bootstrap_1x2_ci(
        df, "A", "B",
        as_of=pd.Timestamp("2024-03-01"),
        league_avg_goals=1.3, rho=-0.15,
        n_samples=25, seed=42,
    )
    # CI should bracket the point estimate within a generous slack — with
    # only 6 historical matches, bootstrap variance is substantial.
    slack = 0.15
    assert ci.p_home_low - slack <= pt.p_home_win <= ci.p_home_high + slack
    assert ci.p_draw_low - slack <= pt.p_draw <= ci.p_draw_high + slack
    assert ci.p_away_low - slack <= pt.p_away_win <= ci.p_away_high + slack


def test_bootstrap_ci_intervals_are_positive_width():
    from app.models.ci import bootstrap_1x2_ci

    df = pd.DataFrame([
        _row("2024-01-01", "A", "B", 1.6, 1.0, 2, 1),
        _row("2024-01-08", "B", "A", 1.0, 1.8, 1, 2),
        _row("2024-01-15", "A", "B", 1.4, 1.2, 1, 1),
        _row("2024-01-22", "B", "A", 1.3, 1.5, 1, 2),
    ])
    ci = bootstrap_1x2_ci(
        df, "A", "B",
        as_of=pd.Timestamp("2024-02-01"),
        league_avg_goals=1.3, rho=-0.15,
        n_samples=20, seed=7,
    )
    # Non-trivial sample should give non-zero-width intervals.
    assert (ci.p_home_high - ci.p_home_low) > 0
