"""Bootstrap confidence intervals for 1X2 probabilities.

Given a team's recent-match history, the per-team `attack`/`defense` we fit
has estimate error — a team with 5 matches of history is far less certain
than one with 25. Bootstrap quantifies that: resample each team's recent
matches WITH replacement `n_samples` times, refit strengths each time, run
the Poisson engine, and take the 16th/84th percentile across samples to
approximate a 1-sigma interval.

Caveat: we bootstrap the xG history but NOT the λ → P mapping itself, so
the CI reflects team-strength uncertainty, not Dixon-Coles tuning noise.
That's fine — tuning noise is negligible compared to sample noise.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.models.features import compute_team_strengths, match_lambdas
from app.models.poisson import predict_match


@dataclass(frozen=True)
class CI1X2:
    p_home_low: float
    p_home_high: float
    p_draw_low: float
    p_draw_high: float
    p_away_low: float
    p_away_high: float
    n_samples: int


def bootstrap_1x2_ci(
    schedule: pd.DataFrame,
    home_team: str,
    away_team: str,
    *,
    as_of: pd.Timestamp,
    league_avg_goals: float,
    rho: float = -0.15,
    n_samples: int = 30,
    last_n: int | None = 12,
    temperature: float = 1.35,
    seed: int | None = None,
) -> CI1X2:
    """Return 1-sigma (16/84 pct) CI on (p_home, p_draw, p_away)."""
    rng = np.random.default_rng(seed)

    done = schedule.loc[
        (schedule["date"] < as_of) & schedule["is_result"].astype(bool)
    ].copy()
    if done.empty:
        return CI1X2(0, 0, 0, 0, 0, 0, n_samples=0)

    p_homes: list[float] = []
    p_draws: list[float] = []
    p_aways: list[float] = []

    n = len(done)
    for _ in range(n_samples):
        idx = rng.integers(0, n, size=n)
        sample = done.iloc[idx].reset_index(drop=True)
        # Give bootstrap sample distinct timestamps so decay/last_n work as
        # intended (uniform sampling already preserves recency on average).
        sample["date"] = pd.date_range(
            start=done["date"].min(), end=done["date"].max(), periods=n,
        )
        strengths = compute_team_strengths(
            sample, as_of=as_of, last_n=last_n, decay=0.9, opponent_adjust=True,
        )
        if home_team not in strengths or away_team not in strengths:
            continue
        lam_h, lam_a = match_lambdas(
            strengths[home_team], strengths[away_team],
            league_avg_goals=league_avg_goals,
        )
        if lam_h <= 0 or lam_a <= 0:
            continue
        pred = predict_match(lam_h, lam_a, rho=rho, temperature=temperature)
        p_homes.append(pred.p_home_win)
        p_draws.append(pred.p_draw)
        p_aways.append(pred.p_away_win)

    if not p_homes:
        return CI1X2(0, 0, 0, 0, 0, 0, n_samples=0)

    def _pct(xs: list[float], q: float) -> float:
        return float(np.percentile(np.array(xs), q))

    return CI1X2(
        p_home_low=_pct(p_homes, 16),
        p_home_high=_pct(p_homes, 84),
        p_draw_low=_pct(p_draws, 16),
        p_draw_high=_pct(p_draws, 84),
        p_away_low=_pct(p_aways, 16),
        p_away_high=_pct(p_aways, 84),
        n_samples=len(p_homes),
    )
