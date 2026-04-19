"""Walk-forward backtest comparing feature-flag combinations.

For each configured hyperparameter set, iterates every final match in the
DB, trains strengths on prior matches only (no future leakage), predicts,
and scores log-loss + top-1 accuracy. Outputs a markdown comparison table.

This is the honest check on every model feature we've added: does
opponent-adjust actually improve log-loss? Does the Elo ensemble? If
a feature doesn't earn its place in the table, we revert it.

Usage:
    python scripts/compare_configs.py [--season 2024-25] [--league epl]
    python scripts/compare_configs.py --all-seasons --all-leagues
"""

from __future__ import annotations

import argparse
import asyncio
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


@dataclass
class Config:
    name: str
    elo_weight: float
    opponent_adjust: bool
    decay: float = 0.9
    last_n: int = 12
    rho: float = -0.15
    temperature: float = 1.35


CONFIGS: list[Config] = [
    Config(name="baseline",       elo_weight=0.00, opponent_adjust=False, decay=1.0),
    Config(name="decay",          elo_weight=0.00, opponent_adjust=False, decay=0.9),
    Config(name="elo",            elo_weight=0.25, opponent_adjust=False, decay=0.9),
    Config(name="opp-adjust",     elo_weight=0.00, opponent_adjust=True,  decay=0.9),
    Config(name="full-stack",     elo_weight=0.25, opponent_adjust=True,  decay=0.9),
]


def _score(pred_p: tuple[float, float, float], actual: str) -> tuple[float, int]:
    """Return (log_loss, is_correct)."""
    idx = {"H": 0, "D": 1, "A": 2}[actual]
    p = max(pred_p[idx], 1e-12)
    ll = -math.log(p)
    argmax = max(range(3), key=lambda i: pred_p[i])
    correct = 1 if argmax == idx else 0
    return ll, correct


async def _run_config(
    pool: asyncpg.Pool, season: str, league_code: str | None, cfg: Config,
) -> dict:
    """Walk-forward across all matches in (season, league), return aggregate scores."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.id, m.kickoff_time, m.home_goals, m.away_goals, m.league_code,
                   ht.name AS home_name, at.name AS away_name
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.season = $1
              AND m.status = 'final'
              AND m.home_goals IS NOT NULL
              AND m.home_xg IS NOT NULL
              AND ($2::text IS NULL OR m.league_code = $2)
            ORDER BY m.kickoff_time ASC
            """,
            season, league_code,
        )

    if not rows:
        return {"config": cfg.name, "season": season, "league": league_code or "all",
                "n": 0, "accuracy": 0.0, "log_loss": 0.0}

    # Pre-fetch all finished matches for the league to feed strengths /
    # Elo — walk-forward by filtering as_of per match.
    full_df = await queries.fetch_finished_matches_df(pool, league_code=league_code)

    ll_sum = 0.0
    correct = 0
    scored = 0

    for r in rows:
        as_of = r["kickoff_time"]
        history = full_df[full_df["date"] < as_of]
        if history.empty:
            continue

        strengths = compute_team_strengths(
            history, as_of=as_of, last_n=cfg.last_n,
            decay=cfg.decay, opponent_adjust=cfg.opponent_adjust,
        )
        home = strengths.get(r["home_name"])
        away = strengths.get(r["away_name"])
        if home is None or away is None:
            continue

        league_avg = float(pd.concat([history["home_goals"], history["away_goals"]]).mean())
        lam_h, lam_a = match_lambdas(home, away, league_avg_goals=league_avg)

        elo_triple = None
        if cfg.elo_weight > 0:
            ratings = compute_ratings(history)
            eh = ratings.get(r["home_name"])
            ea = ratings.get(r["away_name"])
            if eh is not None and ea is not None:
                t = elo_to_3way(eh, ea)
                elo_triple = (t.p_home_win, t.p_draw, t.p_away_win)

        pred = predict_match(
            lam_h, lam_a,
            rho=cfg.rho, temperature=cfg.temperature,
            elo_probs=elo_triple,
            elo_weight=cfg.elo_weight if elo_triple is not None else 0.0,
        )

        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        actual = "H" if hg > ag else ("A" if ag > hg else "D")
        ll, ok = _score((pred.p_home_win, pred.p_draw, pred.p_away_win), actual)
        ll_sum += ll
        correct += ok
        scored += 1

    return {
        "config": cfg.name,
        "season": season,
        "league": league_code or "all",
        "n": scored,
        "accuracy": (correct / scored) if scored else 0.0,
        "log_loss": (ll_sum / scored) if scored else 0.0,
    }


async def run(seasons: list[str], leagues: list[str | None]) -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=4)
    try:
        results: list[dict] = []
        for season in seasons:
            for league_code in leagues:
                print(f"=== season={season} league={league_code or 'all'} ===")
                for cfg in CONFIGS:
                    r = await _run_config(pool, season, league_code, cfg)
                    results.append(r)
                    print(
                        f"  {cfg.name:<12} n={r['n']:>3} "
                        f"acc={r['accuracy']*100:>5.1f}%  "
                        f"log-loss={r['log_loss']:.4f}"
                    )

        # Aggregate across seasons/leagues per config.
        by_cfg: dict[str, dict] = {}
        for r in results:
            key = r["config"]
            entry = by_cfg.setdefault(key, {"n": 0, "ll_w_sum": 0.0, "correct": 0})
            entry["n"] += r["n"]
            entry["ll_w_sum"] += r["log_loss"] * r["n"]
            entry["correct"] += int(round(r["accuracy"] * r["n"]))

        print()
        print("=== AGGREGATE ===")
        print(f"{'config':<15} {'n':>6}  {'accuracy':>10}  {'log-loss':>10}")
        print("-" * 50)
        baseline_ll = None
        for cfg_name in [c.name for c in CONFIGS]:
            agg = by_cfg.get(cfg_name)
            if not agg or agg["n"] == 0:
                continue
            acc = agg["correct"] / agg["n"]
            ll = agg["ll_w_sum"] / agg["n"]
            if cfg_name == "baseline":
                baseline_ll = ll
            delta = ""
            if baseline_ll is not None and cfg_name != "baseline":
                d = ll - baseline_ll
                delta = f"  ({'+' if d > 0 else ''}{d:.4f})"
            print(f"{cfg_name:<15} {agg['n']:>6}  {acc*100:>9.2f}%  {ll:.4f}{delta}")
    finally:
        await pool.close()


def main() -> None:
    import logging
    logging.disable(logging.CRITICAL)

    p = argparse.ArgumentParser()
    p.add_argument("--season", action="append", default=None,
                   help="Season to include (repeatable). Default: 2024-25.")
    p.add_argument("--league", action="append", default=None,
                   help="League slug to include (repeatable). Default: all top-5.")
    p.add_argument("--all-seasons", action="store_true",
                   help="Include 2019-20 through 2024-25.")
    p.add_argument("--all-leagues", action="store_true",
                   help="Aggregate across every league_code (no filter).")
    args = p.parse_args()

    if args.all_seasons:
        seasons = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]
    else:
        seasons = args.season or ["2024-25"]

    if args.all_leagues:
        leagues: list[str | None] = [None]
    elif args.league:
        from app.leagues import get_league
        leagues = [get_league(l).code for l in args.league]
    else:
        from app.leagues import LEAGUES
        leagues = [lg.code for lg in LEAGUES if lg.slug != "all"][:5]

    asyncio.run(run(seasons, leagues))


if __name__ == "__main__":
    main()
