"""Qwen-powered post-match recap — explain what the model got right/wrong.

Pairs with pre-match reasoning. Writes to `matches.recap` so the LLM call
happens once per final and the result is reused on /last-weekend and the
match detail page.
"""

from __future__ import annotations

import asyncpg

from app.llm.prompt import SYSTEM, build_recap_prompt
from app.llm.reasoning import _call_qwen


_OUTCOME = {"H": "H", "D": "D", "A": "A"}


def _actual(hg: int, ag: int) -> str:
    return "H" if hg > ag else "A" if hg < ag else "D"


async def generate_recap(
    pool: asyncpg.Pool,
    match_id: int,
    *,
    model: str = "dashscope/qwen-plus",
) -> str | None:
    """Generate recap for a single final match, persist, and return the text.

    Returns None if: match not final, already has recap, no prediction
    available, or the LLM call fails.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            WITH latest AS (
                SELECT DISTINCT ON (p.match_id)
                    p.match_id, p.p_home_win, p.p_draw, p.p_away_win, p.top_scorelines
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            )
            SELECT m.id, m.status, m.home_goals, m.away_goals, m.home_xg, m.away_xg,
                   m.recap,
                   ht.name AS home_name, at.name AS away_name,
                   l.p_home_win, l.p_draw, l.p_away_win, l.top_scorelines
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            LEFT JOIN latest l ON l.match_id = m.id
            WHERE m.id = $1
            """,
            match_id,
        )
    if row is None:
        return None
    if row["status"] != "final" or row["home_goals"] is None:
        return None
    if row["recap"]:
        return row["recap"]
    if row["p_home_win"] is None:
        return None

    probs = {
        "H": float(row["p_home_win"]),
        "D": float(row["p_draw"]),
        "A": float(row["p_away_win"]),
    }
    predicted = max(probs, key=probs.get)
    actual = _actual(int(row["home_goals"]), int(row["away_goals"]))

    import json
    sl = row["top_scorelines"]
    if isinstance(sl, str):
        sl = json.loads(sl)
    top = (int(sl[0]["home"]), int(sl[0]["away"])) if sl else (1, 1)

    prompt = build_recap_prompt(
        home_team=row["home_name"],
        away_team=row["away_name"],
        home_goals=int(row["home_goals"]),
        away_goals=int(row["away_goals"]),
        home_xg=float(row["home_xg"]) if row["home_xg"] is not None else None,
        away_xg=float(row["away_xg"]) if row["away_xg"] is not None else None,
        predicted_outcome=predicted,
        predicted_confidence=probs[predicted],
        top_scoreline=top,
        actual_outcome=actual,
        hit=predicted == actual,
    )

    try:
        text = _call_qwen(prompt, model)
    except Exception:
        return None

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE matches
            SET recap = $2, recap_model = $3, recap_generated_at = NOW()
            WHERE id = $1
            """,
            match_id,
            text,
            model,
        )
    return text
