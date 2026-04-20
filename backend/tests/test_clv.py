"""Pure-function tests for Closing-Line Value (CLV) arithmetic used by
`/api/stats/clv`.

CLV asks: did we take a better price than the market eventually closed at?
Positive = we were ahead of the market. Long-run positive CLV is the single
strongest proxy for sharp selection.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


def test_clv_pct_positive_when_stake_odds_beats_closing():
    from app.ingest.odds import clv_pct

    # Took 2.00, market closed at 1.90 → we locked in a better price.
    assert clv_pct(stake_odds=2.00, closing_odds=1.90) == pytest.approx(0.0526, abs=1e-3)


def test_clv_pct_negative_when_closing_shortens_past_us():
    from app.ingest.odds import clv_pct

    # Took 1.80, market closed at 2.00 → line drifted AWAY from our side.
    assert clv_pct(stake_odds=1.80, closing_odds=2.00) == pytest.approx(-0.10, abs=1e-3)


def test_clv_pct_zero_when_identical():
    from app.ingest.odds import clv_pct

    assert clv_pct(stake_odds=2.50, closing_odds=2.50) == pytest.approx(0.0)


def test_clv_pct_returns_none_on_invalid_input():
    from app.ingest.odds import clv_pct

    assert clv_pct(stake_odds=0, closing_odds=2.0) is None
    assert clv_pct(stake_odds=2.0, closing_odds=0) is None
    assert clv_pct(stake_odds=2.0, closing_odds=None) is None
    assert clv_pct(stake_odds=None, closing_odds=2.0) is None


def test_aggregate_clv_mean_and_beat_rate():
    """Aggregator: given per-bet CLV values, returns mean + % that beat close."""
    from app.api.stats import _aggregate_clv

    clvs = [0.05, -0.02, 0.10, 0.00, -0.01]
    m = _aggregate_clv(clvs)
    assert m["n"] == 5
    assert m["mean_clv"] == pytest.approx(0.024, abs=1e-3)
    assert m["pct_beat_close"] == pytest.approx(2 / 5)  # 0.05 + 0.10 strictly positive


def test_aggregate_clv_handles_empty():
    from app.api.stats import _aggregate_clv

    m = _aggregate_clv([])
    assert m["n"] == 0
    assert m["mean_clv"] == 0.0
    assert m["pct_beat_close"] == 0.0
