"""Qwen-powered 1-sentence narrative line for a finished match.

Called from the FT Telegram notifier. Distinct from llm/recap.py which
produces the longer 2-3 sentence /last-weekend recap — this is a tight
line that lands next to the score in the channel post.
"""

from __future__ import annotations

import os

from app.llm.reasoning import _call_qwen


SYSTEM = (
    "Bạn là bình luận viên bóng đá Việt, viết 1 câu kết trận sôi động, có "
    "nhịp điệu, tối đa 20 từ. Không markdown, không emoji, không chấm câu "
    "giữa câu."
)


def match_recap_line(
    *,
    home_team: str,
    away_team: str,
    home_goals: int,
    away_goals: int,
    pre_pick_side: str | None,        # 'H' | 'D' | 'A' — which way the pre-match model leaned
    pre_pick_conf: float | None,
    hit: bool | None,
    top_scorers_home: list[str],
    top_scorers_away: list[str],
) -> str | None:
    if not os.environ.get("DASHSCOPE_API_KEY"):
        return None

    scorers_line = ""
    if top_scorers_home or top_scorers_away:
        h = ", ".join(top_scorers_home) or "—"
        a = ", ".join(top_scorers_away) or "—"
        scorers_line = f"Ghi bàn {home_team}: {h}. Ghi bàn {away_team}: {a}."

    verdict = ""
    if pre_pick_side and pre_pick_conf is not None and hit is not None:
        side_label = (
            home_team if pre_pick_side == "H"
            else away_team if pre_pick_side == "A"
            else "hòa"
        )
        verdict = (
            f"Trước trận model đoán {side_label} ({round(pre_pick_conf * 100)}%), "
            f"kết quả {'đúng' if hit else 'sai'}."
        )

    prompt = (
        f"Trận đã kết thúc: {home_team} {home_goals}-{away_goals} {away_team}.\n"
        f"{scorers_line}\n"
        f"{verdict}\n\n"
        f"Viết 1 câu tổng kết ngắn (14-20 từ), giọng sôi động, nhấn mạnh điểm "
        f"thú vị nhất của trận — có thể là ngược dòng, thế trận, hiệu suất, "
        f"hoặc dự đoán model. Chỉ trả về câu, không kèm lời dẫn. Không emoji, "
        f"không markdown."
    )

    try:
        text = _call_qwen(
            prompt, "dashscope/qwen-plus-latest",
            system=SYSTEM, max_tokens=90, temperature=0.75,
        )
    except Exception:
        return None

    out = text.strip().strip('"').strip("'").strip("“”‘’")
    if "\n" in out:
        out = out.split("\n", 1)[0].strip()
    if len(out) > 240:
        out = out[:237] + "…"
    return out or None
