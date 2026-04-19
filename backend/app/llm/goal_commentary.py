"""Qwen-powered 1-sentence goal commentary.

Designed to be called on the /fixtures/events enrichment path for
instant goal notifications. Adds ~400-900ms to the enrichment cycle but
brings the Telegram post from bare-facts to a commentator's voice.

Falls back gracefully — returns None when the LLM call fails so callers
can skip adding a commentary line rather than blocking the enrichment.
"""

from __future__ import annotations

import os

from app.llm.reasoning import _call_qwen


SYSTEM = (
    "Bạn là một bình luận viên bóng đá. Viết bình luận ngắn, có cảm xúc, "
    "bằng tiếng Việt. Dùng giọng sôi động, không khoa trương. Tuyệt đối "
    "không dùng ký tự markdown. Tối đa 18 từ, 1 câu."
)


def build_prompt(
    *,
    home_team: str,
    away_team: str,
    home_goals: int,
    away_goals: int,
    scorer: str,
    assist: str | None,
    minute: int,
    league: str | None,
    is_own_goal: bool,
    is_penalty: bool,
) -> str:
    context_bits: list[str] = [f"Phút {minute}"]
    if league:
        context_bits.append(league)
    context_bits.append(f"{home_team} {home_goals}-{away_goals} {away_team}")

    flags: list[str] = []
    if is_own_goal:
        flags.append("phản lưới nhà")
    if is_penalty:
        flags.append("phạt đền")
    flag_line = f" ({'; '.join(flags)})" if flags else ""

    assist_line = f"Kiến tạo: {assist}." if assist and not is_own_goal else ""

    return (
        f"{' · '.join(context_bits)}\n"
        f"Cầu thủ ghi bàn: {scorer}{flag_line}.\n"
        f"{assist_line}\n"
        f"Viết 1 câu bình luận ngắn (14-18 từ) về pha ghi bàn này. "
        f"Giọng bình luận viên, có cảm xúc. Không dùng markdown, không emoji. "
        f"Chỉ trả về câu bình luận, không kèm lời dẫn."
    )


def goal_commentary(
    *,
    home_team: str,
    away_team: str,
    home_goals: int,
    away_goals: int,
    scorer: str,
    assist: str | None,
    minute: int,
    league: str | None = None,
    is_own_goal: bool = False,
    is_penalty: bool = False,
) -> str | None:
    if not os.environ.get("DASHSCOPE_API_KEY"):
        return None
    try:
        prompt = build_prompt(
            home_team=home_team, away_team=away_team,
            home_goals=home_goals, away_goals=away_goals,
            scorer=scorer, assist=assist, minute=minute, league=league,
            is_own_goal=is_own_goal, is_penalty=is_penalty,
        )
        text = _call_qwen(
            prompt, "dashscope/qwen-turbo",
            system=SYSTEM, max_tokens=80, temperature=0.7,
        )
    except Exception:
        return None
    # Trim leading/trailing whitespace + surrounding quotes if the LLM
    # wrapped the line. Keep the inline content as-is otherwise.
    out = text.strip().strip('"').strip("'").strip("“”‘’")
    # Guard against multi-line answers — keep only the first sentence.
    if "\n" in out:
        out = out.split("\n", 1)[0].strip()
    # Cap length defensively — Qwen usually respects the 18-word cap but
    # occasional runaway blobs would blow out the Telegram message.
    if len(out) > 220:
        out = out[:217] + "…"
    return out or None
