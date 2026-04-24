"""Walk-forward ρ sweep driver.

Reads a YAML-like spec from argv (simple key=value pairs) or a file of
named configs, runs `validate.evaluate` for each, writes scores to
stdout as a CSV line. Minimal; designed for a human to pipe into a
spreadsheet.

Usage:
    python scripts/sweep_config.py --season 2024-25 \\
      --rho " -0.20,-0.15,-0.10,-0.05,0.00" \\
      --last-n 30,50,80,120

Columns: rho, last_n, accuracy, log_loss
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from scripts.validate import evaluate, load_schedule
except Exception:
    evaluate = None
    load_schedule = None


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--season", default="2024-25")
    p.add_argument("--rho", default="-0.20,-0.15,-0.10,-0.05,0.00")
    p.add_argument("--last-n", default="50,100")
    p.add_argument("--warmup", type=int, default=50)
    args = p.parse_args()

    if evaluate is None:
        print("validate module unavailable; skip", file=sys.stderr)
        sys.exit(1)

    rhos = [float(x) for x in args.rho.split(",")]
    last_ns = [int(x) for x in args.last_n.split(",")]
    schedule = load_schedule(args.season)

    w = csv.writer(sys.stdout)
    w.writerow(["rho", "last_n", "accuracy", "log_loss"])
    for rho, ln in product(rhos, last_ns):
        try:
            res = evaluate(
                schedule, rho=rho, last_n=ln,
                warmup=args.warmup,
            )
        except Exception as e:
            print(f"# config rho={rho} last_n={ln} failed: {e}", file=sys.stderr)
            continue
        w.writerow([rho, ln, f"{res['accuracy']:.4f}", f"{res['log_loss']:.4f}"])
        sys.stdout.flush()


if __name__ == "__main__":
    main()
