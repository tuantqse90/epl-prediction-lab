"""Goal-difference-weighted Elo for football.

Standard Elo chess formula with two football-specific tweaks:
  1. Goal-difference bonus — a 4-0 win shifts more rating than a 1-0.
  2. Home-field advantage — when computing expected scores, we add HFA
     rating points to the home side, matching the ~3% home edge seen in
     top-5 leagues.

No draws in pure Elo math, so 3-way conversion adds an empirical draw
band: matches where the expected-score gap is small get a higher share
of their probability mass pushed into the draw bucket.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


K = 20.0                # base K-factor
HFA_ELO = 70.0          # home rating bonus, ~3% favourite swing
DEFAULT_ELO = 1500.0
# How much of the 'no-draw' probability is redistributed into the draw
# bucket, peaked when two teams are evenly matched.
DRAW_PEAK = 0.28


@dataclass(frozen=True)
class EloResult:
    home_new: float
    away_new: float


@dataclass(frozen=True)
class Elo3Way:
    p_home_win: float
    p_draw: float
    p_away_win: float


def expected_score(home_elo: float, away_elo: float) -> float:
    """Chess-style expected score for home team (0..1). Applies HFA."""
    diff = (home_elo + HFA_ELO) - away_elo
    return 1.0 / (1.0 + 10.0 ** (-diff / 400.0))


def _goal_multiplier(diff: int) -> float:
    """Scale K by absolute goal difference (clubelo-style)."""
    abs_diff = abs(diff)
    if abs_diff <= 1:
        return 1.0
    if abs_diff == 2:
        return 1.5
    return (11.0 + abs_diff) / 8.0


def update_ratings(
    home_elo: float, away_elo: float, home_goals: int, away_goals: int,
) -> EloResult:
    exp_h = expected_score(home_elo, away_elo)
    if home_goals > away_goals:
        score_h = 1.0
    elif home_goals < away_goals:
        score_h = 0.0
    else:
        score_h = 0.5
    mult = _goal_multiplier(home_goals - away_goals)
    delta = K * mult * (score_h - exp_h)
    return EloResult(home_new=home_elo + delta, away_new=away_elo - delta)


def elo_to_3way(home_elo: float, away_elo: float) -> Elo3Way:
    """Convert two Elos to a 3-way distribution.

    Logic: use the chess expected_score as a naive home-win-or-draw
    estimate, then split into home-win / draw / away-win by carving out a
    draw share that peaks when the two sides look evenly matched.
    """
    exp_h = expected_score(home_elo, away_elo)
    # Closeness factor: 1.0 when exp_h ≈ 0.5, 0.0 when one side dominates.
    closeness = 1.0 - abs(2.0 * exp_h - 1.0)
    p_draw = DRAW_PEAK * closeness
    remainder = 1.0 - p_draw
    # Redistribute remainder proportional to naive expected scores.
    p_home = remainder * exp_h
    p_away = remainder * (1.0 - exp_h)
    return Elo3Way(p_home_win=p_home, p_draw=p_draw, p_away_win=p_away)


def compute_ratings(matches: pd.DataFrame) -> dict[str, float]:
    """Walk `matches` chronologically and return final rating per team.

    Expects columns: date, home_team, away_team, home_goals, away_goals,
    is_result. Rows where is_result is False or either goals-column is
    null are skipped.
    """
    if matches.empty:
        return {}

    df = matches.copy()
    df = df[df["is_result"].astype(bool)]
    df = df.dropna(subset=["home_goals", "away_goals"])
    if df.empty:
        return {}

    df = df.sort_values("date")
    ratings: dict[str, float] = {}
    for row in df.itertuples(index=False):
        home = row.home_team
        away = row.away_team
        h = ratings.get(home, DEFAULT_ELO)
        a = ratings.get(away, DEFAULT_ELO)
        res = update_ratings(h, a, int(row.home_goals), int(row.away_goals))
        ratings[home] = res.home_new
        ratings[away] = res.away_new
    return ratings
