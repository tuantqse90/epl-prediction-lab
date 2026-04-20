"""Tests for app.models.fatigue — rest + congestion + midweek context.

Sharp bettors fade tired teams. Not much of a team's rating captures:
  - `rest_days`: gap since last match
  - `matches_last_14d`: congestion score (both code + UEFA games if present)
  - `is_midweek`: flag for Tue/Wed/Thu fixtures — European-game overlap
  - `away_rest_diff`: "who's more rested" vs opponent

These feed a context chip on /match/:id and (future) XGBoost retraining.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import pytest


def _df(*rows):
    """Build a small matches DataFrame for fixture-context tests."""
    return pd.DataFrame(rows, columns=["date", "home_team", "away_team"])


def _d(iso):
    return pd.Timestamp(iso)


def test_rest_days_single_team_simple():
    from app.models.fatigue import compute_fixture_context
    df = _df(
        (_d("2026-04-01"), "A", "X"),
        (_d("2026-04-05"), "A", "Y"),
    )
    ctx = compute_fixture_context(df, home="A", away="B", kickoff=_d("2026-04-10"))
    # Home rest: 10 − 5 = 5 days
    assert ctx.rest_days_home == 5
    # Away has no prior → default (7, same as xgb_model._days_rest)
    assert ctx.rest_days_away == 7


def test_congestion_counts_matches_in_last_14_days():
    from app.models.fatigue import compute_fixture_context
    df = _df(
        (_d("2026-03-20"), "A", "X"),  # 26 days ago → out of window
        (_d("2026-04-01"), "A", "Y"),  # 14 days ago → boundary
        (_d("2026-04-05"), "A", "Z"),  # 10 days ago → in
        (_d("2026-04-10"), "A", "W"),  # 5 days ago → in
    )
    ctx = compute_fixture_context(df, home="A", away="B", kickoff=_d("2026-04-15"))
    # Window is (kickoff - 14d, kickoff) strict → 4/1 match excluded (exactly 14d prior),
    # 4/5 + 4/10 included → 2. 3/20 too old.
    assert ctx.congestion_home == 2
    assert ctx.congestion_away == 0  # B has no history


def test_midweek_flag_true_for_tue_wed_thu():
    from app.models.fatigue import compute_fixture_context
    df = _df()
    # 2026-04-15 is a Wednesday
    ctx_wed = compute_fixture_context(df, home="A", away="B", kickoff=_d("2026-04-15 19:30"))
    assert ctx_wed.is_midweek is True
    # 2026-04-18 is Saturday
    ctx_sat = compute_fixture_context(df, home="A", away="B", kickoff=_d("2026-04-18 14:00"))
    assert ctx_sat.is_midweek is False


def test_rest_diff_sign_positive_when_home_more_rested():
    from app.models.fatigue import compute_fixture_context
    df = _df(
        (_d("2026-04-01"), "A", "X"),   # home last played 14d ago
        (_d("2026-04-12"), "B", "Y"),   # away last played 3d ago
    )
    ctx = compute_fixture_context(df, home="A", away="B", kickoff=_d("2026-04-15"))
    assert ctx.rest_days_home == 14
    assert ctx.rest_days_away == 3
    assert ctx.rest_diff == 11


def test_context_handles_team_as_away_in_prior_match():
    """Prior match where the team was AWAY still counts for rest + congestion."""
    from app.models.fatigue import compute_fixture_context
    df = _df(
        (_d("2026-04-10"), "X", "A"),   # A played as AWAY
    )
    ctx = compute_fixture_context(df, home="A", away="B", kickoff=_d("2026-04-15"))
    assert ctx.rest_days_home == 5
    assert ctx.congestion_home == 1
