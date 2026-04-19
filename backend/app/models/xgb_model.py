"""XGBoost 3-way outcome classifier — the third leg of the ensemble.

Uses the same leak-safe walk-forward construction as the Poisson + Elo
path: every feature (strengths, Elo, form) is computed from matches
strictly before each target match's kickoff.

Features (21 total):
  attack/defense coefficients per side (overall + home/away) ................ 12
  Elo rating per side + diff ................................................ 3
  days-rest per side + diff ................................................. 3
  league-average goals (raw) ................................................ 1
  home advantage constant ................................................... 1
  is-derby (same city heuristic via team-name prefix)  ...................... 1

Target: {0: home win, 1: draw, 2: away win}. Softmax probs blend into the
Poisson 1X2 at predict-time via `ensemble_weight_xgb` in predict/service.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.models.elo import compute_ratings
from app.models.features import compute_team_strengths


MODEL_PATH = Path(os.environ.get("XGB_MODEL_PATH", "/tmp/football-predict-xgb.json"))

FEATURE_NAMES = [
    "home_att", "home_def", "home_att_home", "home_def_home",
    "away_att", "away_def", "away_att_away", "away_def_away",
    "home_att_away", "home_def_away",
    "away_att_home", "away_def_home",
    "elo_home", "elo_away", "elo_diff",
    "days_rest_home", "days_rest_away", "days_rest_diff",
    "league_avg",
    "home_adv_const",
    "is_derby",
]


@dataclass
class FeatureRow:
    features: list[float]
    target: int       # 0=H, 1=D, 2=A


def _safe(value: float | None, default: float = 1.0) -> float:
    if value is None or not math.isfinite(value):
        return default
    return float(value)


def _days_rest(history: pd.DataFrame, team: str, as_of: pd.Timestamp) -> float:
    """Days since team's most recent prior match. Capped at 14 to reduce tail effect."""
    mask = (
        ((history["home_team"] == team) | (history["away_team"] == team))
        & (history["date"] < as_of)
    )
    prior = history.loc[mask, "date"]
    if prior.empty:
        return 7.0
    delta = (as_of - prior.max()).days
    return float(min(14, max(0, delta)))


def _is_derby(home: str, away: str) -> float:
    """Crude city-prefix derby flag. Manchester / London / Milan / Madrid etc."""
    CITY_TOKENS = [
        "Manchester", "Liverpool", "London",
        "Madrid", "Barcelona", "Sevilla", "Bilbao", "Sociedad",
        "Milan", "Roma", "Lazio", "Inter",
        "Munich", "Leverkusen", "Berlin",
        "Paris", "Saint",
    ]
    for tok in CITY_TOKENS:
        if tok in home and tok in away:
            return 1.0
    return 0.0


def build_feature_row(
    history: pd.DataFrame,
    home_team: str,
    away_team: str,
    as_of: pd.Timestamp,
    league_avg: float,
) -> list[float] | None:
    """Compute all 21 features for a single target match, or None if insufficient history."""
    if history.empty:
        return None
    strengths = compute_team_strengths(
        history, as_of=as_of, last_n=12, decay=0.9, opponent_adjust=True,
    )
    home = strengths.get(home_team)
    away = strengths.get(away_team)
    if home is None or away is None:
        return None

    ratings = compute_ratings(history)
    elo_h = ratings.get(home_team, 1500.0)
    elo_a = ratings.get(away_team, 1500.0)

    rest_h = _days_rest(history, home_team, as_of)
    rest_a = _days_rest(history, away_team, as_of)

    return [
        home.attack, home.defense,
        _safe(home.attack_home, home.attack), _safe(home.defense_home, home.defense),
        away.attack, away.defense,
        _safe(away.attack_away, away.attack), _safe(away.defense_away, away.defense),
        _safe(home.attack_away, home.attack), _safe(home.defense_away, home.defense),
        _safe(away.attack_home, away.attack), _safe(away.defense_home, away.defense),
        elo_h, elo_a, elo_h - elo_a,
        rest_h, rest_a, rest_h - rest_a,
        league_avg,
        1.3,  # static home-advantage param used in match_lambdas
        _is_derby(home_team, away_team),
    ]


def save_model(model: Any, path: Path = MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Use booster's native save_model for JSON — version-stable across xgboost.
    model.save_model(str(path))


def load_model(path: Path = MODEL_PATH) -> Any | None:
    if not path.exists():
        return None
    try:
        import xgboost as xgb
        booster = xgb.Booster()
        booster.load_model(str(path))
        return booster
    except Exception:
        return None


def predict_probs(
    model: Any, features: list[float],
) -> tuple[float, float, float] | None:
    """Return (p_home, p_draw, p_away) from the trained booster."""
    try:
        import xgboost as xgb
        arr = np.array([features], dtype=np.float32)
        dm = xgb.DMatrix(arr, feature_names=FEATURE_NAMES)
        out = model.predict(dm)  # shape (1, 3) for softprob
        probs = out[0]
        total = float(probs[0] + probs[1] + probs[2])
        if total <= 0:
            return None
        return (float(probs[0] / total), float(probs[1] / total), float(probs[2] / total))
    except Exception:
        return None
