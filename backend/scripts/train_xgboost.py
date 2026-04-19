"""Walk-forward feature extraction → XGBoost softprob training.

Pulls every final match with xG, builds the 21-feature row from matches
strictly before kickoff (no future leakage), trains a `multi:softprob`
booster on the (train) portion of rows, evaluates on the remaining
holdout seasons, writes the booster to `XGB_MODEL_PATH`.

Usage:
    python scripts/train_xgboost.py --holdout-season 2024-25
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import math
import sys
from pathlib import Path

import asyncpg
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import queries
from app.core.config import get_settings
from app.models.xgb_model import (
    FEATURE_NAMES,
    MODEL_PATH,
    build_feature_row,
    save_model,
)


def _outcome(hg: int, ag: int) -> int:
    if hg > ag:
        return 0  # home
    if hg < ag:
        return 2  # away
    return 1      # draw


async def _extract(pool: asyncpg.Pool, holdout_season: str) -> tuple[list, list, list, list]:
    """Return (X_train, y_train, X_test, y_test) — test = holdout_season only."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.id, m.kickoff_time, m.season, m.league_code,
                   m.home_goals, m.away_goals,
                   ht.name AS home_name, at.name AS away_name
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.status = 'final'
              AND m.home_goals IS NOT NULL
              AND m.home_xg IS NOT NULL
            ORDER BY m.kickoff_time ASC
            """
        )

    # Group match rows by league so per-league history used for features.
    by_league: dict[str, list] = {}
    for r in rows:
        by_league.setdefault(r["league_code"], []).append(r)

    X_train: list[list[float]] = []
    y_train: list[int] = []
    X_test: list[list[float]] = []
    y_test: list[int] = []

    for league_code, lg_rows in by_league.items():
        df = await queries.fetch_finished_matches_df(pool, league_code=league_code)
        if df.empty:
            continue
        league_avg = float(pd.concat([df["home_goals"], df["away_goals"]]).mean())

        for i, r in enumerate(lg_rows):
            as_of = r["kickoff_time"]
            history = df[df["date"] < as_of]
            if len(history) < 20:  # need enough prior matches for strengths
                continue
            feats = build_feature_row(history, r["home_name"], r["away_name"], as_of, league_avg)
            if feats is None:
                continue
            target = _outcome(int(r["home_goals"]), int(r["away_goals"]))
            if r["season"] == holdout_season:
                X_test.append(feats)
                y_test.append(target)
            else:
                X_train.append(feats)
                y_train.append(target)
            if (i + 1) % 500 == 0:
                print(f"  [{league_code}] {i + 1}/{len(lg_rows)} extracted")

    return X_train, y_train, X_test, y_test


def _train(X_train, y_train, X_test, y_test) -> None:
    import xgboost as xgb

    print(f"[xgb] train={len(X_train)}  holdout={len(X_test)}")
    if not X_train or not X_test:
        print("[xgb] insufficient data — skipping training")
        return

    dtrain = xgb.DMatrix(np.array(X_train, dtype=np.float32),
                        label=np.array(y_train, dtype=np.int32),
                        feature_names=FEATURE_NAMES)
    dtest = xgb.DMatrix(np.array(X_test, dtype=np.float32),
                       label=np.array(y_test, dtype=np.int32),
                       feature_names=FEATURE_NAMES)

    params = {
        "objective": "multi:softprob",
        "num_class": 3,
        "eta": 0.05,
        "max_depth": 5,
        "subsample": 0.85,
        "colsample_bytree": 0.7,
        "min_child_weight": 3,
        "eval_metric": ["mlogloss", "merror"],
        "verbosity": 0,
    }
    booster = xgb.train(
        params,
        dtrain,
        num_boost_round=500,
        evals=[(dtrain, "train"), (dtest, "holdout")],
        early_stopping_rounds=30,
        verbose_eval=20,
    )

    preds = booster.predict(dtest)
    argmax = preds.argmax(axis=1)
    y_arr = np.array(y_test)
    acc = (argmax == y_arr).mean()
    ll = -np.log(np.maximum(preds[np.arange(len(y_arr)), y_arr], 1e-12)).mean()
    print(f"[xgb] holdout accuracy={acc * 100:.2f}%  log-loss={ll:.4f}")

    save_model(booster)
    print(f"[xgb] saved → {MODEL_PATH}")


async def run(holdout_season: str) -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        X_train, y_train, X_test, y_test = await _extract(pool, holdout_season)
    finally:
        await pool.close()
    _train(X_train, y_train, X_test, y_test)


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--holdout-season", default="2024-25")
    args = p.parse_args()
    asyncio.run(run(args.holdout_season))


if __name__ == "__main__":
    main()
