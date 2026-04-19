"""Qwen-powered reasoning — turn a prediction into 2–3 plain-Vietnamese sentences.

Relies on LiteLLM's router so Qwen-Turbo is the default but any fallback chain
configured at deploy time (Qwen-Plus for derbies, Claude Haiku on total outage)
plugs in without touching this file.
"""

from __future__ import annotations

import asyncpg

from app import queries
from app.llm.prompt import SYSTEM, build_reasoning_prompt


_RECENT_N = 5


async def _recent_team_stats(pool: asyncpg.Pool, team_name: str, before, n: int = _RECENT_N) -> dict:
    """Return {xg_for_avg, xg_against_avg} over the last `n` finals before `before`."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.home_xg, m.away_xg, ht.name AS home, at.name AS away
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.status = 'final' AND m.kickoff_time < $2
              AND (ht.name = $1 OR at.name = $1)
              AND m.home_xg IS NOT NULL AND m.away_xg IS NOT NULL
            ORDER BY m.kickoff_time DESC
            LIMIT $3
            """,
            team_name, before, n,
        )
    if not rows:
        return {"xg_for_avg": 1.0, "xg_against_avg": 1.0}
    xg_for = [r["home_xg"] if r["home"] == team_name else r["away_xg"] for r in rows]
    xg_ag = [r["away_xg"] if r["home"] == team_name else r["home_xg"] for r in rows]
    return {
        "xg_for_avg": sum(xg_for) / len(xg_for),
        "xg_against_avg": sum(xg_ag) / len(xg_ag),
    }


async def _h2h_summary(pool: asyncpg.Pool, home: str, away: str, before) -> str:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ht.name AS home, at.name AS away, m.home_goals, m.away_goals
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
        return "không có số H2H trong DB"
    parts = [f"{r['home']} {r['home_goals']}-{r['away_goals']} {r['away']}" for r in rows]
    return "; ".join(parts)


def _call_qwen(prompt: str, model: str, *, system: str | None = None,
               max_tokens: int = 240, temperature: float = 0.5) -> str:
    """Call Qwen via DashScope's OpenAI-compat endpoint.

    LiteLLM's native `dashscope/*` route hits the CN-region endpoint, which
    rejects intl-region keys. Routing through `openai/*` with an explicit
    `api_base` lets us target either region based on where the key is issued
    (default: Singapore/intl). Override via `DASHSCOPE_API_BASE` if needed.
    """
    import os

    from litellm import completion

    bare_model = model.split("/", 1)[1] if "/" in model else model
    api_base = os.environ.get(
        "DASHSCOPE_API_BASE",
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )
    resp = completion(
        model=f"openai/{bare_model}",
        messages=[
            {"role": "system", "content": system or SYSTEM},
            {"role": "user", "content": prompt},
        ],
        api_base=api_base,
        api_key=os.environ["DASHSCOPE_API_KEY"],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp["choices"][0]["message"]["content"].strip()


async def explain_prediction(
    pool: asyncpg.Pool,
    match_id: int,
    *,
    model: str = "dashscope/qwen-turbo",
) -> str | None:
    """Build the Qwen prompt from DB context, call the model, persist reasoning.

    Returns the reasoning text, or None if there is no prediction yet or the
    LLM call fails (we log but don't raise — predictions without reasoning are
    still useful to the UI).
    """
    match = await queries.get_match(pool, match_id)
    if match is None or match["p_home_win"] is None:
        return None

    kickoff = match["kickoff_time"]
    home_name, away_name = match["home_name"], match["away_name"]

    home_stats = await _recent_team_stats(pool, home_name, kickoff)
    away_stats = await _recent_team_stats(pool, away_name, kickoff)
    h2h = await _h2h_summary(pool, home_name, away_name, kickoff)

    # Top scoreline may be stored as JSONB; fetch directly for clarity.
    async with pool.acquire() as conn:
        sc = await conn.fetchrow(
            """
            SELECT id, top_scorelines FROM predictions
            WHERE match_id = $1 ORDER BY created_at DESC LIMIT 1
            """,
            match_id,
        )
    import json
    sl = json.loads(sc["top_scorelines"]) if isinstance(sc["top_scorelines"], str) else sc["top_scorelines"]
    top = (int(sl[0]["home"]), int(sl[0]["away"])) if sl else (1, 1)

    prompt = build_reasoning_prompt(
        home_team=home_name,
        away_team=away_name,
        p_home_win=match["p_home_win"],
        p_draw=match["p_draw"],
        p_away_win=match["p_away_win"],
        top_scoreline=top,
        home_xg_avg=home_stats["xg_for_avg"],
        home_xga_avg=home_stats["xg_against_avg"],
        away_xg_avg=away_stats["xg_for_avg"],
        away_xga_avg=away_stats["xg_against_avg"],
        h2h_summary=h2h,
    )

    try:
        reasoning = _call_qwen(prompt, model)
    except Exception:
        return None

    await queries.update_prediction_reasoning(pool, sc["id"], reasoning, model)
    return reasoning
