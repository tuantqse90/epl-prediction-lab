"""Phase 42.1 — Qwen-powered long-form post-match story (400-500 words).

Siblings to `recap.py` (short 2-3 sentence blurb). Persisted to `matches.story`
so the LLM call happens once per final and is reused on /match/:id.

Trigger: called from ingest_live_scores after FT (alongside recap). Also
callable standalone for backfill of old matches.
"""

from __future__ import annotations

import json

import asyncpg

from app.llm.prompt import STORY_SYSTEM, build_story_prompt
from app.llm.reasoning import _call_qwen


def _actual(hg: int, ag: int) -> str:
    return "H" if hg > ag else "A" if hg < ag else "D"


async def _h2h_summary(pool: asyncpg.Pool, home: str, away: str, before) -> str | None:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.home_goals, m.away_goals,
                   ht.name AS home, at.name AS away
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.status = 'final' AND m.kickoff_time < $3
              AND ((ht.name = $1 AND at.name = $2) OR (ht.name = $2 AND at.name = $1))
            ORDER BY m.kickoff_time DESC
            LIMIT 3
            """,
            home, away, before,
        )
    if not rows:
        return None
    parts = [f"{r['home']} {r['home_goals']}-{r['away_goals']} {r['away']}" for r in rows]
    return "; ".join(parts)


async def generate_story(
    pool: asyncpg.Pool,
    match_id: int,
    *,
    model: str = "dashscope/qwen-turbo",
) -> str | None:
    """Generate and persist a 400-500 word narrative for a finished match.

    Returns the text if written, None if skipped (not final / no xG / LLM fail).
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
                   m.home_shots, m.away_shots, m.league_code, m.kickoff_time,
                   m.story,
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
    if row is None or row["status"] != "final" or row["home_goals"] is None:
        return None
    if row["story"]:
        return row["story"]
    if row["p_home_win"] is None:
        return None

    probs = {
        "H": float(row["p_home_win"]),
        "D": float(row["p_draw"]),
        "A": float(row["p_away_win"]),
    }
    predicted = max(probs, key=probs.get)
    actual = _actual(int(row["home_goals"]), int(row["away_goals"]))

    sl = row["top_scorelines"]
    if isinstance(sl, str):
        sl = json.loads(sl)
    top = (int(sl[0]["home"]), int(sl[0]["away"])) if sl else (1, 1)

    h2h = await _h2h_summary(pool, row["home_name"], row["away_name"], row["kickoff_time"])

    prompt = build_story_prompt(
        home_team=row["home_name"],
        away_team=row["away_name"],
        home_goals=int(row["home_goals"]),
        away_goals=int(row["away_goals"]),
        home_xg=float(row["home_xg"]) if row["home_xg"] is not None else None,
        away_xg=float(row["away_xg"]) if row["away_xg"] is not None else None,
        home_shots=int(row["home_shots"]) if row["home_shots"] is not None else None,
        away_shots=int(row["away_shots"]) if row["away_shots"] is not None else None,
        league_code=row["league_code"],
        predicted_outcome=predicted,
        predicted_confidence=probs[predicted],
        top_scoreline=top,
        actual_outcome=actual,
        hit=predicted == actual,
        h2h_summary=h2h,
    )

    try:
        text = _call_qwen(prompt, model, system=STORY_SYSTEM, max_tokens=900, temperature=0.6)
    except Exception:
        return None
    if not text or len(text) < 200:
        return None

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE matches
            SET story = $2, story_model = $3, story_generated_at = NOW()
            WHERE id = $1
            """,
            match_id, text, model,
        )
    return text
