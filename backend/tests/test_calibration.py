"""Calibration curve — bin predictions by confidence, compute actual
hit rate per bin, report Brier score.
"""
from __future__ import annotations

import pytest


def test_perfect_calibration_returns_y_equal_x():
    """If every 0.5 prediction hit 50% of the time, 0.6 hit 60%, etc,
    the bin's actual_rate must equal the bin center."""
    from app.models.calibration import calibrate

    # 10 predictions at 0.3, 3 hit → bin 20-30% has actual = 0.3
    # 10 predictions at 0.5, 5 hit → 40-50% bin... wait, bin convention.
    # Simpler: predictions at 0.55 go into 50-60% bin.
    preds = (
        [(0.55, True)] * 5 + [(0.55, False)] * 5   # 10 at 0.55, hits 50%
      + [(0.75, True)] * 7 + [(0.75, False)] * 3   # 10 at 0.75, hits 70%
    )
    bins = calibrate(preds, n_bins=10)
    # Bin 50-60
    b50 = next(b for b in bins if b["bin_low"] == 0.5)
    assert b50["n"] == 10
    assert b50["mean_predicted"] == pytest.approx(0.55)
    assert b50["actual_hit_rate"] == pytest.approx(0.5)
    # Bin 70-80
    b70 = next(b for b in bins if b["bin_low"] == 0.7)
    assert b70["n"] == 10
    assert b70["actual_hit_rate"] == pytest.approx(0.7)


def test_empty_bins_excluded():
    from app.models.calibration import calibrate

    # Only bin 60-70 populated
    preds = [(0.65, True)] * 3 + [(0.65, False)] * 2
    bins = calibrate(preds, n_bins=10)
    # Only one bin returned
    assert len(bins) == 1
    assert bins[0]["bin_low"] == 0.6


def test_brier_score_for_well_calibrated_preds():
    """Brier = mean((p − outcome)^2). For p=1 always hitting, 0.
    For p=0.5 evenly split, 0.25."""
    from app.models.calibration import brier_score

    # p=1, always hit → Brier 0
    assert brier_score([(1.0, True)] * 10) == pytest.approx(0.0)
    # p=0.5, 50-50 → 0.25
    preds = [(0.5, True)] * 50 + [(0.5, False)] * 50
    assert brier_score(preds) == pytest.approx(0.25)


def test_log_loss_handles_edge_probs():
    """log(0) would diverge; implementation must clip."""
    from app.models.calibration import log_loss

    # p=0 but hit → should be high but finite
    ll = log_loss([(0.001, True)])
    assert ll < 10 and ll > 5  # clipped to some ceiling
    # p=1 and hit → should be near 0
    assert log_loss([(0.999, True)]) < 0.01


def test_overall_summary_consistent():
    """Top-level summary must match manual computations."""
    from app.models.calibration import summarize

    preds = (
        [(0.55, True)] * 5 + [(0.55, False)] * 5     # brier = 0.25 × 10
      + [(0.75, True)] * 7 + [(0.75, False)] * 3     # brier per = .0625 × 7 + .5625 × 3
    )
    s = summarize(preds, n_bins=10)
    assert s["total"] == 20
    assert s["brier"] > 0
    assert s["log_loss"] > 0
    # Reliability = mean over bins of (p - actual)^2; perfectly calibrated = 0.
    # These bins ARE perfectly calibrated → reliability near 0.
    assert s["reliability"] < 0.001
