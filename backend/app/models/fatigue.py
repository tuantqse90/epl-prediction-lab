"""Fixture-context features: rest days, 14-day congestion, midweek flag.

Complements the existing XGBoost `days_rest_*` features. Surfaced on
/match/:id as a chip so users can weight predictions appropriately for
tired teams; ready to drop into a future XGB retrain as additional
columns without reshaping the per-match dataframe.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class FixtureContext:
    rest_days_home: int
    rest_days_away: int
    rest_diff: int              # home − away (positive = home more rested)
    congestion_home: int        # matches played by home in the 14 days before kickoff
    congestion_away: int
    is_midweek: bool            # kickoff falls Tue/Wed/Thu


def _prior_matches(df: pd.DataFrame, team: str, kickoff: pd.Timestamp) -> pd.DataFrame:
    if df.empty:
        return df
    mask = (
        ((df["home_team"] == team) | (df["away_team"] == team))
        & (df["date"] < kickoff)
    )
    return df.loc[mask]


def _rest_days(df: pd.DataFrame, team: str, kickoff: pd.Timestamp, default: int = 7) -> int:
    prior = _prior_matches(df, team, kickoff)
    if prior.empty:
        return default
    last = prior["date"].max()
    delta = (kickoff - last).days
    return max(0, int(delta))


def _congestion(df: pd.DataFrame, team: str, kickoff: pd.Timestamp, window_days: int = 14) -> int:
    """Count matches by `team` in the strict interval (kickoff − window_days, kickoff).

    Strictly past: the kickoff match itself never counts. The lower bound is
    also strict (> kickoff − window_days) so a match exactly 14 days ago
    sits outside the window — matches test expectations and aligns with
    typical sharp-bettor convention of "last 14d meaning the prior two
    match-weeks only"."""
    prior = _prior_matches(df, team, kickoff)
    if prior.empty:
        return 0
    lower = kickoff - pd.Timedelta(days=window_days)
    return int(((prior["date"] > lower) & (prior["date"] < kickoff)).sum())


def compute_fixture_context(
    df: pd.DataFrame,
    home: str,
    away: str,
    kickoff: pd.Timestamp,
) -> FixtureContext:
    rest_h = _rest_days(df, home, kickoff)
    rest_a = _rest_days(df, away, kickoff)
    cong_h = _congestion(df, home, kickoff)
    cong_a = _congestion(df, away, kickoff)
    # pandas weekday: Monday=0 ... Sunday=6. Tue/Wed/Thu = 1/2/3.
    midweek = int(kickoff.weekday()) in (1, 2, 3)
    return FixtureContext(
        rest_days_home=rest_h,
        rest_days_away=rest_a,
        rest_diff=rest_h - rest_a,
        congestion_home=cong_h,
        congestion_away=cong_a,
        is_midweek=bool(midweek),
    )
