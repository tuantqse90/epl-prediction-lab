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


def build_recap_prompt(
    *,
    home_team: str,
    away_team: str,
    home_goals: int,
    away_goals: int,
    home_xg: float | None,
    away_xg: float | None,
    predicted_outcome: str,
    predicted_confidence: float,
    top_scoreline: tuple[int, int],
    actual_outcome: str,
    hit: bool,
) -> str:
    th, ta = top_scoreline
    outcome_vi = {"H": "chủ nhà thắng", "D": "hòa", "A": "đội khách thắng"}
    pred_phrase = outcome_vi[predicted_outcome]
    actual_phrase = outcome_vi[actual_outcome]
    verdict = "ĐÚNG" if hit else "SAI"
    xg_line = ""
    if home_xg is not None and away_xg is not None:
        xg_line = f"xG thực tế: {home_team} {home_xg:.2f} - {away_xg:.2f} {away_team}\n"
    return (
        f"Trận đã kết thúc: {home_team} {home_goals} - {away_goals} {away_team}\n"
        f"{xg_line}"
        f"Model đoán: {pred_phrase} ({round(predicted_confidence * 100)}%), "
        f"tỷ số {th}-{ta}\n"
        f"Thực tế: {actual_phrase}\n"
        f"Model đoán {verdict}.\n\n"
        f"Viết recap 2-3 câu: (1) model đoán đúng/sai ở đâu, "
        f"(2) xG/tỷ số có khớp với kỳ vọng không, "
        f"(3) 1 yếu tố bất ngờ hoặc khớp mô hình. "
        f"Giọng anh em, không khoa trương, tối đa 3 câu."
    )


STORY_SYSTEM = (
    "Bạn là một cây bút bóng đá. Viết văn mượt, không sáo rỗng. "
    "Dùng số liệu cụ thể, không phóng đại. Tiếng Việt chuẩn, dễ đọc. "
    "400-500 từ, chia 3 đoạn."
)


def build_story_prompt(
    *,
    home_team: str,
    away_team: str,
    home_goals: int,
    away_goals: int,
    home_xg: float | None,
    away_xg: float | None,
    home_shots: int | None,
    away_shots: int | None,
    league_code: str | None,
    predicted_outcome: str,
    predicted_confidence: float,
    top_scoreline: tuple[int, int],
    actual_outcome: str,
    hit: bool,
    h2h_summary: str | None = None,
) -> str:
    outcome_vi = {"H": "chủ nhà thắng", "D": "hòa", "A": "đội khách thắng"}
    th, ta = top_scoreline
    xg_line = (
        f"xG: {home_team} {home_xg:.2f} - {away_xg:.2f} {away_team}"
        if home_xg is not None and away_xg is not None
        else "xG: không có dữ liệu"
    )
    shot_line = (
        f"Dứt điểm: {home_team} {home_shots} - {away_shots} {away_team}"
        if home_shots is not None and away_shots is not None
        else ""
    )
    h2h_line = f"H2H: {h2h_summary}" if h2h_summary else ""
    league_line = f"Giải: {league_code}" if league_code else ""
    verdict = "đoán ĐÚNG" if hit else "đoán SAI"
    return (
        f"Viết một bài narrative 400-500 từ, tiếng Việt, chia 3 đoạn:\n"
        f"- Đoạn 1: bối cảnh + kết quả + ai xứng đáng thắng theo xG\n"
        f"- Đoạn 2: diễn biến chính + bước ngoặt (dựa trên số liệu xG/dứt điểm)\n"
        f"- Đoạn 3: model {verdict} ra sao + 1 take-away sắc bén\n\n"
        f"DỮ LIỆU:\n"
        f"Trận: {home_team} {home_goals}-{away_goals} {away_team}\n"
        f"{league_line}\n"
        f"{xg_line}\n"
        f"{shot_line}\n"
        f"{h2h_line}\n"
        f"Model predict: {outcome_vi[predicted_outcome]} "
        f"({round(predicted_confidence * 100)}%), tỷ số {th}-{ta}\n"
        f"Thực tế: {outcome_vi[actual_outcome]}\n\n"
        f"Không dùng emoji. Không tạo số liệu không có trong dữ liệu trên."
    )
