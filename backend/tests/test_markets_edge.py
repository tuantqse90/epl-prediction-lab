"""Pure tests for the market-edge builder used by /api/matches/:id/markets-edge.

Takes model probs (from the scoreline matrix) + stored book odds from the
match_odds_markets table and returns one row per (market, outcome) with:
- model_prob, fair_odds=1/model_prob
- best_book_odds, source
- edge_pp = (model_prob * best_odds − 1) × 100

Neon-highlighted when edge_pp ≥ threshold.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


def _odds_row(source, market, line, outcome, odds):
    return SimpleNamespace(
        source=source, market_code=market, line=line,
        outcome_code=outcome, odds=odds,
    )


def test_edge_builder_emits_all_known_markets_even_without_book_odds():
    """When no book odds stored, rows still come back with model prob + fair
    odds, so the UI falls back to the manual-comparison view."""
    from app.api.matches import _build_market_edge_rows
    probs = {"over_2_5": 0.50, "btts_yes": 0.52,
             "ah_home_minus_0_5": 0.45, "ah_home_plus_0_5": 0.60}
    rows = _build_market_edge_rows(probs=probs, book_rows=[])
    # One row per key.
    keys = {r["key"] for r in rows}
    assert "over_2_5" in keys
    assert "btts_yes" in keys
    assert "ah_home_minus_0_5" in keys
    # Fair odds = 1/prob
    over = next(r for r in rows if r["key"] == "over_2_5")
    assert over["fair_odds"] == pytest.approx(1 / 0.50)
    assert over["best_book_odds"] is None
    assert over["edge_pp"] is None


def test_edge_builder_picks_best_book_odds_across_sources():
    """Best odds = max across per-book sources (highest price for bettor)."""
    from app.api.matches import _build_market_edge_rows
    probs = {"over_2_5": 0.50}
    book_rows = [
        _odds_row("odds-api:pinnacle", "OU", 2.5, "OVER", 1.95),
        _odds_row("odds-api:bet365",   "OU", 2.5, "OVER", 2.10),
        _odds_row("odds-api:williamhill","OU", 2.5, "OVER", 2.00),
        _odds_row("the-odds-api:avg",  "OU", 2.5, "OVER", 2.00),  # avg — skipped for best
    ]
    rows = _build_market_edge_rows(probs=probs, book_rows=book_rows)
    over = next(r for r in rows if r["key"] == "over_2_5")
    assert over["best_book_odds"] == pytest.approx(2.10)
    # edge = (0.50 * 2.10 − 1) × 100 = +5pp
    assert over["edge_pp"] == pytest.approx(5.0, abs=1e-6)
    assert over["best_source"] == "odds-api:bet365"


def test_edge_builder_marks_negative_edge():
    """Edge can be negative if book price is too low. Returned as-is; UI
    colours it muted/red."""
    from app.api.matches import _build_market_edge_rows
    probs = {"btts_yes": 0.55}
    book_rows = [
        _odds_row("odds-api:bet365", "BTTS", None, "YES", 1.70),  # implied ~58.8%
    ]
    rows = _build_market_edge_rows(probs=probs, book_rows=book_rows)
    btts = next(r for r in rows if r["key"] == "btts_yes")
    # edge = 0.55 * 1.70 − 1 = -0.065 → -6.5pp
    assert btts["edge_pp"] == pytest.approx(-6.5, abs=1e-6)


def test_edge_builder_maps_ah_lines_to_book_rows():
    """AH -0.5 home stored as line=-0.5 outcome=HOME on the book side."""
    from app.api.matches import _build_market_edge_rows
    probs = {"ah_home_minus_0_5": 0.55}
    book_rows = [
        _odds_row("odds-api:pinnacle", "AH", -0.5, "HOME", 1.95),
    ]
    rows = _build_market_edge_rows(probs=probs, book_rows=book_rows)
    ah = next(r for r in rows if r["key"] == "ah_home_minus_0_5")
    assert ah["best_book_odds"] == pytest.approx(1.95)
    assert ah["edge_pp"] == pytest.approx((0.55 * 1.95 - 1) * 100, abs=1e-6)


def test_edge_builder_ignores_unknown_line_or_outcome():
    """Book rows at lines or outcomes we don't price are silently skipped."""
    from app.api.matches import _build_market_edge_rows
    probs = {"over_2_5": 0.50}
    book_rows = [
        _odds_row("odds-api:bet365", "OU", 3.5, "OVER", 3.50),  # wrong line
        _odds_row("odds-api:bet365", "OU", 2.5, "UNDER", 1.85), # wrong outcome for over_2_5
    ]
    rows = _build_market_edge_rows(probs=probs, book_rows=book_rows)
    over = next(r for r in rows if r["key"] == "over_2_5")
    assert over["best_book_odds"] is None  # nothing matched


def test_edge_builder_flags_beyond_threshold():
    from app.api.matches import _build_market_edge_rows
    probs = {"over_2_5": 0.60}
    book_rows = [_odds_row("odds-api:bet365", "OU", 2.5, "OVER", 2.00)]
    rows = _build_market_edge_rows(probs=probs, book_rows=book_rows, edge_threshold_pp=5.0)
    over = next(r for r in rows if r["key"] == "over_2_5")
    # edge = 0.60 * 2.00 − 1 = +20pp → flagged
    assert over["edge_pp"] == pytest.approx(20.0)
    assert over["flagged"] is True


class _RecordLike:
    """Duck-types asyncpg.Record: subscript access only, NO attribute access.
    Regression guard: the real Record rejects `getattr(r, 'col')`."""
    def __init__(self, **kv):
        self._d = dict(kv)
    def __getitem__(self, k):
        return self._d[k]
    def __repr__(self):
        return f"<Record {self._d!r}>"


def test_edge_builder_reads_asyncpg_record_style_rows():
    """Regression: asyncpg.Record doesn't support attr access — getattr
    returns None silently. Builder must fall through to subscript."""
    from app.api.matches import _build_market_edge_rows
    probs = {"over_2_5": 0.50}
    book_rows = [
        _RecordLike(source="odds-api:bet365", market_code="OU",
                    line=2.5, outcome_code="OVER", odds=2.10),
    ]
    rows = _build_market_edge_rows(probs=probs, book_rows=book_rows)
    over = next(r for r in rows if r["key"] == "over_2_5")
    assert over["best_book_odds"] == pytest.approx(2.10)
    assert over["edge_pp"] == pytest.approx(5.0, abs=1e-6)
