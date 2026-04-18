"""Grid-search ρ on a season and report the minimizer by log-loss.

Usage:
    python scripts/calibrate_rho.py --season 2024-25 --warmup-matches 50
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.validate import evaluate, load_schedule


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--season", default="2024-25")
    p.add_argument("--warmup-matches", type=int, default=50)
    p.add_argument("--rhos", default="-0.30,-0.20,-0.15,-0.10,-0.05,0.00,0.05,0.10")
    args = p.parse_args()

    rhos = [float(x) for x in args.rhos.split(",")]
    schedule = load_schedule(args.season)
    print(f"> season {args.season} :: {len(schedule)} finished matches")
    print(f"{'rho':>7} | {'accuracy':>9} | {'log-loss':>9}")
    print("-" * 34)

    best = (None, float("inf"), None)
    for rho in rhos:
        r = evaluate(schedule, warmup=args.warmup_matches, rho=rho)
        print(f"{rho:>7.3f} | {r.accuracy:>8.1%} | {r.mean_log_loss:>9.4f}")
        if r.mean_log_loss < best[1]:
            best = (rho, r.mean_log_loss, r)

    rho, ll, r = best
    print("-" * 34)
    print(f"> best ρ = {rho:+.3f} :: log-loss {ll:.4f}, accuracy {r.accuracy:.1%}")


if __name__ == "__main__":
    main()
