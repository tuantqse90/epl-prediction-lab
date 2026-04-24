"""Qwen-powered 1-sentence narrative hooks for pre-match / mid-game /
halftime notifications. Sibling to goal_commentary + match_recap_line.

Each function returns a single short Vietnamese sentence or None
(on LLM outage / over-length output). Callers append it when non-None.

Model: qwen-plus-latest (paid tier, ~$0.002/1k input tokens).
"""

from __future__ import annotations

from app.llm.reasoning import _call_qwen


PRE_MATCH_SYSTEM = (
    "Bạn là BLV bóng đá viết caption pre-match. Giọng năng động, "
    "không khoa trương. Tiếng Việt. Tuyệt đối không markdown. "
    "Tối đa 22 từ, 1 câu."
)

MIDWAY_SYSTEM = (
    "Bạn là BLV bóng đá bình luận giữa trận. Giọng trung tính, "
    "bám số liệu. Tiếng Việt. Không markdown. Tối đa 24 từ, 1 câu."
)

HALFTIME_SYSTEM = (
    "Bạn là BLV bóng đá tổng kết hiệp 1. Giọng sắc nét, có chính kiến. "
    "Tiếng Việt. Không markdown. Tối đa 22 từ, 1 câu."
)


def _safe(text: str | None, max_words: int) -> str | None:
    """Strip markdown leaks + hard cap word count. Return None if empty."""
    if not text:
        return None
    t = text.strip().replace("*", "").replace("_", "").replace("`", "")
    # Keep just the first sentence.
    for sep in (". ", "! ", "? ", "\n"):
        if sep in t:
            t = t.split(sep, 1)[0] + ("." if sep == ". " else "")
            break
    words = t.split()
    if len(words) > max_words:
        t = " ".join(words[:max_words]).rstrip(",") + "…"
    return t or None


def pre_match_hook(
    *,
    home_team: str,
    away_team: str,
    league: str | None,
    pick_side_label: str | None,
    pick_confidence: float | None,
    top_scoreline: tuple[int, int] | None,
    model: str = "dashscope/qwen-plus-latest",
) -> str | None:
    """One-sentence hype line for the 30-min-before-KO post."""
    parts = [f"Trận: {home_team} vs {away_team}"]
    if league:
        parts.append(f"Giải: {league}")
    if pick_side_label and pick_confidence:
        parts.append(
            f"Model nghiêng về {pick_side_label} với {int(pick_confidence * 100)}% tin cậy"
        )
    if top_scoreline:
        parts.append(f"Tỷ số dự đoán: {top_scoreline[0]}-{top_scoreline[1]}")
    prompt = (
        "\n".join(parts)
        + "\n\nViết 1 câu caption pre-match cho post Telegram, "
          "ngắn gọn, năng động. Không nhắc lại số liệu chi tiết — "
          "chỉ tạo không khí."
    )
    try:
        out = _call_qwen(
            prompt, model, system=PRE_MATCH_SYSTEM,
            max_tokens=120, temperature=0.7,
        )
    except Exception:
        return None
    return _safe(out, max_words=22)


def midway_hook(
    *,
    home_team: str,
    away_team: str,
    home_goals: int,
    away_goals: int,
    minute: int,
    home_xg: float | None,
    away_xg: float | None,
    home_shots: int | None,
    away_shots: int | None,
    home_possession: int | None,
    model: str = "dashscope/qwen-plus-latest",
) -> str | None:
    """One-sentence narrative for the phút-60 check-in."""
    parts = [
        f"Phút {minute} · {home_team} {home_goals}-{away_goals} {away_team}",
    ]
    if home_xg is not None and away_xg is not None:
        parts.append(f"xG: {home_xg:.2f} vs {away_xg:.2f}")
    if home_shots is not None and away_shots is not None:
        parts.append(f"Cú sút: {home_shots} vs {away_shots}")
    if home_possession is not None:
        parts.append(f"Kiểm soát: {home_possession}% / {100 - home_possession}%")
    prompt = (
        "\n".join(parts)
        + "\n\nViết 1 câu bình luận giữa trận: ai đang chiếm ưu thế theo "
          "số liệu, và có điều gì đáng chú ý? Ngắn, trung tính."
    )
    try:
        out = _call_qwen(
            prompt, model, system=MIDWAY_SYSTEM,
            max_tokens=130, temperature=0.5,
        )
    except Exception:
        return None
    return _safe(out, max_words=24)


def halftime_hook(
    *,
    home_team: str,
    away_team: str,
    home_goals: int,
    away_goals: int,
    league: str | None,
    model: str = "dashscope/qwen-plus-latest",
) -> str | None:
    """One-sentence HT take — 'hiệp 1 sôi động / cán cân lệch'."""
    parts = [
        f"Hết hiệp 1: {home_team} {home_goals}-{away_goals} {away_team}",
    ]
    if league:
        parts.append(f"Giải: {league}")
    prompt = (
        "\n".join(parts)
        + "\n\nViết 1 câu tổng kết hiệp 1 ngắn gọn, có chính kiến: "
          "hiệp 1 thế nào, hiệp 2 cần gì?"
    )
    try:
        out = _call_qwen(
            prompt, model, system=HALFTIME_SYSTEM,
            max_tokens=120, temperature=0.6,
        )
    except Exception:
        return None
    return _safe(out, max_words=22)
