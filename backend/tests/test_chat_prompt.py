"""TDD tests for the chat Q&A prompt builder.

The system prompt is load-bearing — it's what stops the model from making up
numbers. Lock the hard guardrails here.
"""

from __future__ import annotations


def _ctx():
    return dict(
        home_team="Arsenal",
        away_team="Fulham",
        kickoff="2026-04-26 14:00",
        p_home_win=0.62,
        p_draw=0.22,
        p_away_win=0.16,
        model_reasoning="Arsenal xG cao hơn, sân nhà lợi thế.",
        home_recent="Arsenal 2-0 Brighton; Arsenal 1-1 Liverpool; Everton 0-3 Arsenal",
        away_recent="Fulham 0-1 Chelsea; Fulham 2-2 Brentford; West Ham 1-0 Fulham",
        h2h="Arsenal 2-0 Fulham; Fulham 1-2 Arsenal; Arsenal 3-1 Fulham",
        top_scorers_home="Saka 14g, Havertz 11g, Ødegaard 9g",
        top_scorers_away="Muñiz 8g, Pereira 6g, Wilson 5g",
    )


def test_chat_system_forbids_fabrication():
    from app.llm.chat_prompt import build_chat_system

    s = build_chat_system()
    assert "KHÔNG" in s or "không có số đó" in s.lower()


def test_chat_system_vi_uses_polite_tone():
    from app.llm.chat_prompt import build_chat_system

    s = build_chat_system("vi")
    assert "tôi/bạn" in s or "bạn" in s.lower()


def test_chat_system_en_forbids_fabrication():
    from app.llm.chat_prompt import build_chat_system

    s = build_chat_system("en")
    assert "do NOT invent" in s or "do not invent" in s.lower()


def test_chat_user_includes_match_and_prediction_data():
    from app.llm.chat_prompt import build_chat_user

    u = build_chat_user(**_ctx(), question="Sao mày predict thế?")
    assert "Arsenal" in u
    assert "Fulham" in u
    assert "62%" in u
    assert "Sao mày predict thế?" in u


def test_chat_user_includes_recent_and_h2h():
    from app.llm.chat_prompt import build_chat_user

    u = build_chat_user(**_ctx(), question="Kèo nào đáng?")
    assert "Brighton" in u        # from home_recent
    assert "Brentford" in u        # from away_recent
    assert "Arsenal 2-0 Fulham" in u  # from h2h


def test_chat_user_includes_top_scorers_for_striker_questions():
    """Scorer context lets the model answer 'ai ghi bàn' correctly."""
    from app.llm.chat_prompt import build_chat_user

    u = build_chat_user(**_ctx(), question="Ai ghi bàn?")
    assert "Saka" in u
    assert "Muñiz" in u


def test_suggested_prompts_vi_default():
    from app.llm.chat_prompt import suggested_prompts

    prompts = suggested_prompts(home="Arsenal", away="Fulham")
    assert len(prompts) >= 3
    assert any("Arsenal" in p for p in prompts)
    assert any("Fulham" in p for p in prompts)


def test_suggested_prompts_en_locale():
    from app.llm.chat_prompt import suggested_prompts

    prompts = suggested_prompts(home="Arsenal", away="Fulham", lang="en")
    assert any("Arsenal" in p for p in prompts)
    assert any("upset" in p.lower() or "pull" in p.lower() for p in prompts)
