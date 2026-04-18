"""Prompt templates for the Qwen reasoning layer.

Pure string builders — no LLM call, no I/O. Tested in `tests/test_prompt.py`.
Wording here is the single source of truth for model voice and guardrails.
"""

from __future__ import annotations

SYSTEM = (
    "Bạn là một nhà phân tích bóng đá sắc bén, nói chuyện kiểu anh em. "
    "Không khoa trương. Dùng số liệu thật. Tối đa 3 câu."
)


def build_reasoning_prompt(
    *,
    home_team: str,
    away_team: str,
    p_home_win: float,
    p_draw: float,
    p_away_win: float,
    top_scoreline: tuple[int, int],
    home_xg_avg: float,
    home_xga_avg: float,
    away_xg_avg: float,
    away_xga_avg: float,
    h2h_summary: str,
) -> str:
    th, ta = top_scoreline
    return (
        f"Trận đấu: {home_team} vs {away_team}\n"
        f"Dự đoán của model (Poisson + Dixon-Coles):\n"
        f"- Thắng sân nhà ({home_team}): {round(p_home_win * 100)}%\n"
        f"- Hòa: {round(p_draw * 100)}%\n"
        f"- Thua sân nhà ({away_team} thắng): {round(p_away_win * 100)}%\n"
        f"- Tỷ số dự đoán: {th}-{ta}\n\n"
        f"Dữ liệu gần đây (5 trận):\n"
        f"- {home_team}: xG trung bình {home_xg_avg:.1f}, xGA {home_xga_avg:.1f}\n"
        f"- {away_team}: xG trung bình {away_xg_avg:.1f}, xGA {away_xga_avg:.1f}\n\n"
        f"H2H 3 trận gần nhất: {h2h_summary}\n\n"
        f"Giải thích ngắn gọn VÌ SAO model predict như vậy. "
        f"Chỉ rõ 2-3 số liệu quan trọng nhất. Tối đa 3 câu, giọng anh em."
    )
