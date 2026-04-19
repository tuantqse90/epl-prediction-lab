"""Grid-search the ensemble blend weights over walk-forward backtest.

For each match in the evaluation set, compute the three base signals once:
  * Poisson + Dixon-Coles probs (from opponent-adjusted strengths)
  * Elo probs (from goal-weighted Elo ratings)
  * XGBoost probs (from the trained classifier at /tmp/football-predict-xgb.json)

Then score every (elo_weight, xgb_weight) combo in the grid against the
stored predictions. Reuses the compute-once-score-many trick so sweeping
20 configs is the same cost as evaluating one.

Evaluation set: seasons where XGBoost is out-of-sample (default: 2024-25
and 2025-26). XGB was trained on 2019-20 through 2023-24, so scoring it
on earlier seasons would be trivially in-sample.

Usage:
    python scripts/tune_ensemble.py
    python scripts/tune_ensemble.py --seasons 2024-25,2025-26 --elo 0,0.15,0.25,0.35 --xgb 0,0.10,0.15,0.20,0.30
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import asyncpg
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import queries
from app.core.config import get_settings
from app.models.elo import compute_ratings, elo_to_3way
from app.models.features import compute_team_strengths, match_lambdas
from app.models.poisson import predict_match
from app.models.xgb_model import (
    build_feature_row as xgb_build_feature_row,
    load_model as xgb_load_model,
    predict_probs as xgb_predict_probs,
)


DEFAULT_RHO = -0.15
DEFAULT_LAST_N = 12
DEFAULT_DECAY = 0.9
DEFAULT_TEMPERATURE = 1.35


@dataclass
class MatchSample:
    """One row of the 'compute-once' cache."""
    match_id: int
    league_code: str | None
    poisson: tuple[float, float, float]
    elo: tuple[float, float, float] | None
    xgb: tuple[float, float, float] | None
    actual: str


def _actual(hg: int, ag: int) -> str:
    if hg > ag:
        return "H"
    if ag > hg:
        return "A"
    return "D"


def _blend(
    poisson: tuple[float, float, float],
    elo: tuple[float, float, float] | None,
    xgb: tuple[float, float, float] | None,
    elo_weight: float,
    xgb_weight: float,
) -> tuple[float, float, float]:
    """Two sequential convex blends: first Poisson+Elo, then result+XGB."""
    if elo is not None and elo_weight > 0:
        w = max(0.0, min(1.0, elo_weight))
        p = (
            (1 - w) * poisson[0] + w * elo[0],
            (1 - w) * poisson[1] + w * elo[1],
            (1 - w) * poisson[2] + w * elo[2],
        )
    else:
        p = poisson

    if xgb is not None and xgb_weight > 0:
        w = max(0.0, min(1.0, xgb_weight))
        p = (
            (1 - w) * p[0] + w * xgb[0],
            (1 - w) * p[1] + w * xgb[1],
            (1 - w) * p[2] + w * xgb[2],
        )

    s = p[0] + p[1] + p[2]
    if s == 0:
        return (1 / 3, 1 / 3, 1 / 3)
    return (p[0] / s, p[1] / s, p[2] / s)


def _score_config(samples: list[MatchSample], elo_w: float, xgb_w: float) -> dict:
    ll_sum = 0.0
    correct = 0
    for s in samples:
        probs = _blend(s.poisson, s.elo, s.xgb, elo_w, xgb_w)
        idx = {"H": 0, "D": 1, "A": 2}[s.actual]
        ll_sum += -math.log(max(probs[idx], 1e-12))
        if max(range(3), key=lambda i: probs[i]) == idx:
            correct += 1
    n = len(samples)
    return {
        "elo_weight": elo_w,
        "xgb_weight": xgb_w,
        "n": n,
        "accuracy": correct / n if n else 0.0,
        "log_loss": ll_sum / n if n else 0.0,
    }


async def _build_samples(
    pool: asyncpg.Pool,
    seasons: list[str],
) -> list[MatchSample]:
    """Walk-forward over matches in `seasons`, compute base signals once each."""
    xgb_model = xgb_load_model()
    if xgb_model is None:
        print("[tune] WARNING: XGBoost model not found — XGB weight search will be useless")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.id, m.kickoff_time, m.home_goals, m.away_goals, m.league_code,
                   ht.name AS home_name, at.name AS away_name
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.season = ANY($1::text[])
              AND m.status = 'final'
              AND m.home_goals IS NOT NULL
              AND m.home_xg IS NOT NULL
            ORDER BY m.kickoff_time ASC
            """,
            seasons,
        )
    print(f"[tune] evaluation matches: {len(rows)}")

    # Per-league history cached so we don't re-query 3000 times.
    league_to_hist: dict[str | None, pd.DataFrame] = {}

    samples: list[MatchSample] = []
    skipped = 0
    for i, r in enumerate(rows):
        lc = r["league_code"]
        if lc not in league_to_hist:
            league_to_hist[lc] = await queries.fetch_finished_matches_df(pool, league_code=lc)
        hist_all = league_to_hist[lc]
        as_of = r["kickoff_time"]
        history = hist_all[hist_all["date"] < as_of]
        if history.empty:
            skipped += 1
            continue

        strengths = compute_team_strengths(
            history,
            as_of=as_of,
            last_n=DEFAULT_LAST_N,
            decay=DEFAULT_DECAY,
            opponent_adjust=True,
        )
        home = strengths.get(r["home_name"])
        away = strengths.get(r["away_name"])
        if home is None or away is None:
            skipped += 1
            continue

        league_avg = float(pd.concat([history["home_goals"], history["away_goals"]]).mean())
        lam_h, lam_a = match_lambdas(home, away, league_avg_goals=league_avg)
        base = predict_match(
            lam_h, lam_a,
            rho=DEFAULT_RHO,
            temperature=DEFAULT_TEMPERATURE,
        )
        poisson_triple = (base.p_home_win, base.p_draw, base.p_away_win)

        ratings = compute_ratings(history)
        eh = ratings.get(r["home_name"])
        ea = ratings.get(r["away_name"])
        elo_triple = None
        if eh is not None and ea is not None:
            et = elo_to_3way(eh, ea)
            elo_triple = (et.p_home_win, et.p_draw, et.p_away_win)

        xgb_triple = None
        if xgb_model is not None:
            feats = xgb_build_feature_row(
                history,
                home_team=r["home_name"],
                away_team=r["away_name"],
                as_of=as_of,
            )
            if feats is not None:
                xgb_triple = xgb_predict_probs(xgb_model, feats)

        actual = _actual(int(r["home_goals"]), int(r["away_goals"]))
        samples.append(MatchSample(
            match_id=r["id"], league_code=lc,
            poisson=poisson_triple, elo=elo_triple, xgb=xgb_triple,
            actual=actual,
        ))

        if (i + 1) % 200 == 0:
            print(f"[tune]  … {i + 1}/{len(rows)} matches processed")

    print(f"[tune] built {len(samples)} samples (skipped {skipped}).")
    return samples


async def run(seasons: list[str], elo_grid: list[float], xgb_grid: list[float]) -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=4)
    try:
        samples = await _build_samples(pool, seasons)
    finally:
        await pool.close()

    if not samples:
        print("[tune] no samples; abort")
        return

    # Also fingerprint how often each leg is available (non-null).
    has_elo = sum(1 for s in samples if s.elo is not None)
    has_xgb = sum(1 for s in samples if s.xgb is not None)
    print(f"[tune] elo available: {has_elo}/{len(samples)} · xgb available: {has_xgb}/{len(samples)}")

    results = [_score_config(samples, e, x) for e in elo_grid for x in xgb_grid]
    results.sort(key=lambda r: r["log_loss"])

    print()
    print("=== RESULTS (sorted by log-loss ascending) ===")
    print(f"{'elo':>6}  {'xgb':>6}  {'n':>5}  {'accuracy':>10}  {'log-loss':>10}  {'delta vs best':>14}")
    print("-" * 70)
    best_ll = results[0]["log_loss"]
    for r in results:
        delta = r["log_loss"] - best_ll
        delta_str = "  (best)" if delta == 0 else f"  (+{delta:.4f})"
        print(
            f"{r['elo_weight']:>6.2f}  {r['xgb_weight']:>6.2f}  {r['n']:>5}  "
            f"{r['accuracy'] * 100:>9.2f}%  {r['log_loss']:.4f}{delta_str}"
        )

    best = results[0]
    print()
    print(f"[tune] BEST: elo_weight={best['elo_weight']:.2f} xgb_weight={best['xgb_weight']:.2f}")
    print(f"[tune]       log-loss={best['log_loss']:.4f}  acc={best['accuracy'] * 100:.2f}%  n={best['n']}")
    current = next(
        (r for r in results if abs(r["elo_weight"] - 0.25) < 1e-9 and abs(r["xgb_weight"] - 0.15) < 1e-9),
        None,
    )
    if current:
        print(
            f"[tune] current (0.25 / 0.15): log-loss={current['log_loss']:.4f} "
            f"acc={current['accuracy'] * 100:.2f}%"
        )
        print(f"[tune] savings vs current: {current['log_loss'] - best['log_loss']:+.4f} log-loss")


def _parse_list(s: str) -> list[float]:
    return [float(x.strip()) for x in s.split(",") if x.strip()]


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--seasons", default="2024-25,2025-26")
    p.add_argument("--elo", default="0,0.10,0.15,0.20,0.25,0.30,0.35")
    p.add_argument("--xgb", default="0,0.05,0.10,0.15,0.20,0.25,0.30")
    args = p.parse_args()

    seasons = [s.strip() for s in args.seasons.split(",") if s.strip()]
    elo_grid = _parse_list(args.elo)
    xgb_grid = _parse_list(args.xgb)
    print(f"[tune] seasons={seasons}  elo_grid={elo_grid}  xgb_grid={xgb_grid}")
    asyncio.run(run(seasons, elo_grid, xgb_grid))


if __name__ == "__main__":
    main()
