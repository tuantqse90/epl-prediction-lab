"""Joint sweep of `last_n` (strength window) and `rho` (Dixon-Coles) on one season.

Runs entirely off the soccerdata cache — no DB. Prints a 2-D table and the
best combo by mean log-loss. Use the result to update `DEFAULT_LAST_N` and
`DEFAULT_RHO` in `app/core/config.py`.
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
    p.add_argument("--last-ns", default="8,10,12,15")
    p.add_argument("--rhos", default="-0.20,-0.15,-0.10,-0.05,0.00")
    args = p.parse_args()

    last_ns = [int(x) for x in args.last_ns.split(",")]
    rhos = [float(x) for x in args.rhos.split(",")]

    schedule = load_schedule(args.season)
    print(f"> season {args.season} :: {len(schedule)} finished matches")

    header = "last_n | " + " | ".join(f"ρ={r:+.2f}" for r in rhos)
    print(header)
    print("-" * len(header))

    best = {"ll": float("inf"), "acc": 0.0, "ln": None, "rho": None}
    for ln in last_ns:
        row = [f"{ln:>6}"]
        for rho in rhos:
            r = evaluate(schedule, warmup=args.warmup_matches, rho=rho, last_n=ln)
            row.append(f"{r.mean_log_loss:.4f}/{r.accuracy:.0%}")
            if r.mean_log_loss < best["ll"]:
                best = {"ll": r.mean_log_loss, "acc": r.accuracy, "ln": ln, "rho": rho}
        print(" | ".join(row))

    print("-" * len(header))
    print(f"> best :: last_n={best['ln']} ρ={best['rho']:+.2f} "
          f"log-loss={best['ll']:.4f} acc={best['acc']:.1%}")


if __name__ == "__main__":
    main()
