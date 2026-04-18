"""Walk-forward validation of the Poisson + Dixon-Coles engine on real EPL data.

Exposes `evaluate()` for reuse (e.g. ρ calibration) and a CLI entry point.
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.models.features import compute_team_strengths, match_lambdas
from app.models.poisson import predict_match


@dataclass(frozen=True)
class EvalResult:
    scored: int
    accuracy: float
    baseline_home_accuracy: float
    mean_log_loss: float
    league_avg_goals: float


def load_schedule(season: str) -> pd.DataFrame:
    import soccerdata as sd

    us = sd.Understat(leagues=["ENG-Premier League"], seasons=[season])
    df = us.read_schedule().reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    return df[df["is_result"].astype(bool)].sort_values("date").reset_index(drop=True)


def _actual(h: int, a: int) -> str:
    return "H" if h > a else ("A" if h < a else "D")


def _argmax(p_h: float, p_d: float, p_a: float) -> str:
    return max(zip("HDA", (p_h, p_d, p_a)), key=lambda t: t[1])[0]


def evaluate(schedule: pd.DataFrame, warmup: int, rho: float, last_n: int = 10) -> EvalResult:
    """Walk the schedule chronologically, predict each match from prior data, aggregate."""
    league_avg = float(pd.concat([schedule["home_goals"], schedule["away_goals"]]).mean())

    correct = 0
    ll_sum = 0.0
    baseline_h = 0
    scored = 0

    for row in schedule.itertuples(index=False):
        priors = schedule[schedule["date"] < row.date]
        if len(priors) < warmup:
            continue

        strengths = compute_team_strengths(schedule, as_of=row.date, last_n=last_n)
        if row.home_team not in strengths or row.away_team not in strengths:
            continue

        lam_h, lam_a = match_lambdas(
            strengths[row.home_team],
            strengths[row.away_team],
            league_avg_goals=league_avg,
        )
        pred = predict_match(lam_h, lam_a, rho=rho)
        outcome = _actual(int(row.home_goals), int(row.away_goals))
        p_outcome = {"H": pred.p_home_win, "D": pred.p_draw, "A": pred.p_away_win}[outcome]

        scored += 1
        ll_sum += -math.log(max(p_outcome, 1e-12))
        if _argmax(pred.p_home_win, pred.p_draw, pred.p_away_win) == outcome:
            correct += 1
        if outcome == "H":
            baseline_h += 1

    return EvalResult(
        scored=scored,
        accuracy=correct / scored if scored else 0.0,
        baseline_home_accuracy=baseline_h / scored if scored else 0.0,
        mean_log_loss=ll_sum / scored if scored else float("inf"),
        league_avg_goals=league_avg,
    )


def _format(r: EvalResult, rho: float) -> str:
    return (
        f"> scored        :: {r.scored}\n"
        f"> 1X2 accuracy  :: {r.accuracy:.1%}  "
        f"(baseline always-H = {r.baseline_home_accuracy:.1%})\n"
        f"> mean log-loss :: {r.mean_log_loss:.4f}   (uniform = {-math.log(1/3):.4f})\n"
        f"> rho           :: {rho}"
    )


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--season", default="2024-25")
    p.add_argument("--warmup-matches", type=int, default=50)
    p.add_argument("--rho", type=float, default=0.0)
    args = p.parse_args()

    schedule = load_schedule(args.season)
    print(f"> season {args.season} :: {len(schedule)} finished matches")
    r = evaluate(schedule, warmup=args.warmup_matches, rho=args.rho)
    print(f"> league avg goals/team/match :: {r.league_avg_goals:.3f}")
    print("-" * 50)
    print(_format(r, args.rho))


if __name__ == "__main__":
    main()
