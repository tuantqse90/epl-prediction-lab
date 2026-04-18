"""Simulate a flat-stake value-betting strategy on historical predictions + odds.

For each (match, outcome) pair where model_prob - fair_prob >= threshold,
imagine betting 1 unit at the bookmaker's posted odds. Compute PnL + ROI.

Usage:
    python scripts/value_bet_roi.py --season 2024-25
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.ingest.odds import fair_probs


async def run(season: str, thresholds: list[float]) -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        rows = await pool.fetch(
            """
            WITH latest AS (
                SELECT DISTINCT ON (p.match_id)
                    p.match_id, p.p_home_win, p.p_draw, p.p_away_win
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            )
            SELECT m.home_goals, m.away_goals,
                   l.p_home_win, l.p_draw, l.p_away_win,
                   o.odds_home, o.odds_draw, o.odds_away
            FROM matches m
            JOIN latest l ON l.match_id = m.id
            JOIN match_odds o ON o.match_id = m.id
            WHERE m.status = 'final' AND m.season = $1
              AND m.home_goals IS NOT NULL
            """,
            season,
        )
    finally:
        await pool.close()

    print(f"> {season} :: {len(rows)} matches with predictions + odds")
    print(f"{'threshold':>10} | {'bets':>5} | {'PnL':>8} | {'ROI':>6}")
    print("-" * 38)

    for thr in thresholds:
        bets = 0
        pnl = 0.0
        for r in rows:
            f = fair_probs(r["odds_home"], r["odds_draw"], r["odds_away"])
            if not f:
                continue
            probs = {"H": r["p_home_win"], "D": r["p_draw"], "A": r["p_away_win"]}
            odds = {"H": r["odds_home"], "D": r["odds_draw"], "A": r["odds_away"]}
            fair = {"H": f[0], "D": f[1], "A": f[2]}
            hg, ag = r["home_goals"], r["away_goals"]
            outcome = "H" if hg > ag else ("A" if hg < ag else "D")
            for side in "HDA":
                edge = float(probs[side]) - fair[side]
                if edge >= thr:
                    bets += 1
                    pnl += (float(odds[side]) - 1.0) if side == outcome else -1.0
        roi = pnl / bets * 100 if bets else 0.0
        print(f"{thr * 100:>8.0f}pp | {bets:>5} | {pnl:>+7.1f}u | {roi:>+5.1f}%")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--season", default="2024-25")
    p.add_argument("--thresholds", default="0.02,0.05,0.08,0.10,0.15")
    args = p.parse_args()
    thrs = [float(x) for x in args.thresholds.split(",")]
    asyncio.run(run(args.season, thrs))


if __name__ == "__main__":
    main()
