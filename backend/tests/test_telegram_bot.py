"""Telegram bot — command parser + pure formatters.

The webhook hits FastAPI with a Telegram Update JSON. We must extract
the command + args and dispatch to a handler. Handlers split into:
  - pure format_*() functions that take already-fetched rows (tested here)
  - async fetch_*() functions that hit the DB (tested via integration later)
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# parse_update
# ---------------------------------------------------------------------------


def test_parse_slash_command_no_args():
    from app.telegram.bot import parse_update

    update = {
        "message": {
            "chat": {"id": 42},
            "text": "/help",
            "entities": [{"type": "bot_command", "offset": 0, "length": 5}],
        }
    }
    result = parse_update(update)
    assert result.chat_id == 42
    assert result.command == "help"
    assert result.args == []


def test_parse_slash_command_with_args():
    from app.telegram.bot import parse_update

    update = {
        "message": {
            "chat": {"id": 100},
            "text": "/pick today",
            "entities": [{"type": "bot_command", "offset": 0, "length": 5}],
        }
    }
    r = parse_update(update)
    assert r.command == "pick"
    assert r.args == ["today"]


def test_parse_command_strips_bot_suffix():
    """In group chats users type /pick@worldcup_predictor_bot — strip it."""
    from app.telegram.bot import parse_update

    update = {
        "message": {
            "chat": {"id": 5},
            "text": "/pick@worldcup_predictor_bot PSG",
            "entities": [{"type": "bot_command", "offset": 0, "length": 28}],
        }
    }
    r = parse_update(update)
    assert r.command == "pick"
    assert r.args == ["PSG"]


def test_parse_non_command_returns_none():
    from app.telegram.bot import parse_update

    update = {"message": {"chat": {"id": 1}, "text": "hello"}}
    assert parse_update(update) is None


def test_parse_callback_query_extracts_chat_id():
    """Inline buttons emit callback_query, not message. We still want chat_id."""
    from app.telegram.bot import parse_update

    update = {
        "callback_query": {
            "message": {"chat": {"id": 99}},
            "data": "/edge",
        }
    }
    r = parse_update(update)
    assert r.chat_id == 99
    assert r.command == "edge"


# ---------------------------------------------------------------------------
# format_help
# ---------------------------------------------------------------------------


def test_format_help_lists_all_commands():
    from app.telegram.bot import format_help

    out = format_help()
    # Mandatory commands
    for cmd in ["/pick", "/edge", "/clv", "/roi", "/subscribe", "/help"]:
        assert cmd in out, f"{cmd} missing from /help"


# ---------------------------------------------------------------------------
# format_pick — top upcoming matches by edge
# ---------------------------------------------------------------------------


def test_format_pick_renders_matches():
    from app.telegram.bot import format_pick

    rows = [
        _ns(home_name="ARS", away_name="TOT", league_code="ENG-Premier League",
            kickoff_time="2026-04-25 14:00:00", pick_side="H", pick_conf=0.58,
            best_odds=1.75, edge_pp=4.2),
        _ns(home_name="PSG", away_name="LYO", league_code="FRA-Ligue 1",
            kickoff_time="2026-04-25 19:00:00", pick_side="H", pick_conf=0.62,
            best_odds=1.48, edge_pp=6.8),
    ]
    out = format_pick(rows, window_label="today")
    assert "ARS" in out and "TOT" in out
    assert "PSG" in out and "LYO" in out
    # Confidence percentage rendered
    assert "58" in out or "62" in out


def test_format_pick_empty_window():
    from app.telegram.bot import format_pick

    out = format_pick([], window_label="today")
    assert "no" in out.lower() or "không" in out.lower() or "empty" in out.lower()


# ---------------------------------------------------------------------------
# format_roi — rolling window
# ---------------------------------------------------------------------------


def test_format_roi_positive():
    from app.telegram.bot import format_roi

    out = format_roi(total_bets=49, roi_pct=6.3, pnl=3.1, window="30d")
    assert "49" in out
    assert "6.3" in out or "6.30" in out
    assert "30d" in out


def test_format_roi_zero_bets():
    """No bets in the window → don't divide-by-zero, say "no data"."""
    from app.telegram.bot import format_roi

    out = format_roi(total_bets=0, roi_pct=0.0, pnl=0.0, window="7d")
    assert "0" in out or "no" in out.lower() or "chưa" in out.lower()


def _ns(**kw):
    return SimpleNamespace(**kw)
