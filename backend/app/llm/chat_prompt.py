"""Prompt builders for the conversational Q&A layer.

System prompt sets the guardrails (no fabrication, peer-tone Vietnamese);
user prompt injects the RAG context the model must ground its reply in.
"""

from __future__ import annotations


_SYSTEM_VI = (
    "Bạn là AI analyst của EPL Lab. Trả lời bằng tiếng Việt lịch sự, gần gũi, "
    "xưng \"tôi/bạn\". Chỉ dựa vào phần DATA phía dưới — KHÔNG được bịa số. "
    "Nếu không có trong data, trả lời \"tôi không có số đó\". "
    "Trả lời ngắn gọn tối đa 4 câu, trực tiếp, không khoa trương."
)

_SYSTEM_EN = (
    "You are the EPL Lab match analyst. Answer in clear, friendly English. "
    "Base every statement on the DATA block below — do NOT invent numbers. "
    "If the data doesn't contain what the user asks, say so plainly. "
    "Keep answers to four sentences max, direct, no hype."
)


def build_chat_system(lang: str = "vi") -> str:
    return _SYSTEM_EN if lang == "en" else _SYSTEM_VI


def build_chat_user(
    *,
    home_team: str,
    away_team: str,
    kickoff: str,
    p_home_win: float,
    p_draw: float,
    p_away_win: float,
    model_reasoning: str,
    home_recent: str,
    away_recent: str,
    h2h: str,
    top_scorers_home: str,
    top_scorers_away: str,
    question: str,
    lang: str = "vi",
) -> str:
    user_label = "Câu hỏi của user" if lang != "en" else "User question"
    return (
        f"===== DATA =====\n"
        f"Match: {home_team} vs {away_team}, {kickoff}\n"
        f"Prediction: H {round(p_home_win * 100)}% / "
        f"D {round(p_draw * 100)}% / A {round(p_away_win * 100)}%\n"
        f"Model reasoning: {model_reasoning or '(no reasoning yet)'}\n\n"
        f"{home_team} last 5:\n{home_recent}\n\n"
        f"{away_team} last 5:\n{away_recent}\n\n"
        f"H2H last 3:\n{h2h}\n\n"
        f"Top scorers ({home_team}): {top_scorers_home}\n"
        f"Top scorers ({away_team}): {top_scorers_away}\n"
        f"===== END DATA =====\n\n"
        f"{user_label}: {question}"
    )


def suggested_prompts(*, home: str, away: str, lang: str = "vi") -> list[str]:
    if lang == "en":
        return [
            "Why did the model predict this?",
            f"Who scores for {home}?",
            "Which side is the value bet?",
            f"Can {away} pull an upset?",
        ]
    return [
        "Vì sao mô hình dự đoán như vậy?",
        f"Ai sẽ ghi bàn cho {home}?",
        "Bên nào có giá trị cược?",
        f"{away} có cơ hội lật ngược không?",
    ]
