"""TDD tests for the Qwen reasoning prompt builder.

The LLM call itself is glue, but the prompt is load-bearing — any drift in
wording or missing data is a silent regression. Lock the essentials here.
"""

from __future__ import annotations

import pytest


def _ctx():
    return dict(
        home_team="Arsenal",
        away_team="Fulham",
        p_home_win=0.62,
        p_draw=0.22,
        p_away_win=0.16,
        top_scoreline=(2, 1),
        home_xg_avg=1.9,
        home_xga_avg=0.9,
        away_xg_avg=1.1,
        away_xga_avg=1.4,
        h2h_summary="Arsenal 2-0 Fulham; Fulham 1-2 Arsenal; Arsenal 3-1 Fulham",
    )


def test_prompt_contains_both_team_names():
    from app.llm.prompt import build_reasoning_prompt

    out = build_reasoning_prompt(**_ctx())
    assert "Arsenal" in out
    assert "Fulham" in out


def test_prompt_includes_all_three_probabilities_as_percentages():
    from app.llm.prompt import build_reasoning_prompt

    out = build_reasoning_prompt(**_ctx())
    assert "62%" in out
    assert "22%" in out
    assert "16%" in out


def test_prompt_includes_top_scoreline():
    from app.llm.prompt import build_reasoning_prompt

    out = build_reasoning_prompt(**_ctx())
    assert "2-1" in out


def test_prompt_includes_xg_stats():
    from app.llm.prompt import build_reasoning_prompt

    out = build_reasoning_prompt(**_ctx())
    assert "1.9" in out  # home xG avg
    assert "0.9" in out  # home xGA avg
    assert "1.1" in out  # away xG avg
    assert "1.4" in out  # away xGA avg


def test_prompt_enforces_vietnamese_peer_tone():
    """Guardrails: instructs the model to use peer tone, max 3 sentences, no fabrication."""
    from app.llm.prompt import build_reasoning_prompt

    out = build_reasoning_prompt(**_ctx())
    assert "anh em" in out.lower()
    assert "3 câu" in out or "tối đa" in out.lower()
