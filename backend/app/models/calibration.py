"""Calibration — bin (predicted probability, outcome) pairs by decile
and report hit rate per bin, plus Brier score and log-loss.

A well-calibrated model produces bins where `actual_hit_rate` ≈ bin
center. Reliability diagram plots these points; closer to y = x = better.
"""

from __future__ import annotations

import math
from typing import Iterable


def calibrate(
    preds: Iterable[tuple[float, bool]],
    *,
    n_bins: int = 10,
) -> list[dict]:
    """Return one row per populated bin: bin_low, bin_high, n, mean_predicted,
    actual_hit_rate, predicted_mean_minus_actual."""
    bins_data = [[] for _ in range(n_bins)]
    preds = list(preds)
    for p, hit in preds:
        # Clamp into [0, 1); idx is floor(p * n_bins) capped at n_bins-1.
        idx = min(int(max(0.0, min(0.9999999, p)) * n_bins), n_bins - 1)
        bins_data[idx].append((p, bool(hit)))

    out: list[dict] = []
    width = 1.0 / n_bins
    for i, rows in enumerate(bins_data):
        if not rows:
            continue
        n = len(rows)
        mean_p = sum(p for p, _ in rows) / n
        hit_rate = sum(1 for _, h in rows if h) / n
        out.append({
            "bin_low": round(i * width, 6),
            "bin_high": round((i + 1) * width, 6),
            "n": n,
            "mean_predicted": mean_p,
            "actual_hit_rate": hit_rate,
            "gap": mean_p - hit_rate,
        })
    return out


def brier_score(preds: Iterable[tuple[float, bool]]) -> float:
    preds = list(preds)
    if not preds:
        return 0.0
    return sum((p - (1.0 if h else 0.0)) ** 2 for p, h in preds) / len(preds)


def log_loss(preds: Iterable[tuple[float, bool]], *, eps: float = 1e-6) -> float:
    """Binary log loss. Clips p to [eps, 1-eps] so edge 0/1 predictions
    don't diverge."""
    preds = list(preds)
    if not preds:
        return 0.0
    total = 0.0
    for p, h in preds:
        p = max(eps, min(1 - eps, p))
        if h:
            total -= math.log(p)
        else:
            total -= math.log(1 - p)
    return total / len(preds)


def summarize(preds: Iterable[tuple[float, bool]], *, n_bins: int = 10) -> dict:
    preds = list(preds)
    bins = calibrate(preds, n_bins=n_bins)
    # Reliability = weighted mean squared gap across bins (lower = better)
    total = sum(b["n"] for b in bins) or 1
    reliability = sum((b["gap"] ** 2) * b["n"] for b in bins) / total
    return {
        "total": len(preds),
        "bins": bins,
        "brier": brier_score(preds),
        "log_loss": log_loss(preds),
        "reliability": reliability,
    }
