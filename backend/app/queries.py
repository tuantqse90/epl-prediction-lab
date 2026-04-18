"""SQL query helpers — thin wrappers over asyncpg.

Query shapes are chosen so the consuming endpoints do no joins or aggregation
in Python; each function returns rows already reduced to what the API needs.
"""

from __future__ import annotations

import json
from typing import Any

import asyncpg
import pandas as pd

from app.models.poisson import MatchPrediction


_MATCH_WITH_LATEST_PREDICTION = """
SELECT
    m.id, m.external_id, m.league_code, m.season, m.matchweek, m.kickoff_time, m.status,
    m.home_goals, m.away_goals, m.home_xg, m.away_xg,
    m.minute, m.live_updated_at,
    ht.slug AS home_slug, ht.name AS home_name, ht.short_name AS home_short,
    at.slug AS away_slug, at.name AS away_name, at.short_name AS away_short,
    lp.p_home_win, lp.p_draw, lp.p_away_win,
    lp.expected_home_goals, lp.expected_away_goals,
    lp.top_scorelines, lp.reasoning, lp.reasoning_model, lp.model_version,
    lp.commitment_hash,
    lo.odds_home, lo.odds_draw, lo.odds_away, lo.source AS odds_source,
    hf.form AS home_form,
    af.form AS away_form
FROM matches m
JOIN teams ht ON ht.id = m.home_team_id
JOIN teams at ON at.id = m.away_team_id
LEFT JOIN LATERAL (
    SELECT *
    FROM predictions
    WHERE match_id = m.id
    ORDER BY created_at DESC
    LIMIT 1
) lp ON TRUE
LEFT JOIN LATERAL (
    SELECT *
    FROM match_odds
    WHERE match_id = m.id
    ORDER BY captured_at DESC
    LIMIT 1
) lo ON TRUE
LEFT JOIN LATERAL (
    SELECT array_agg(result ORDER BY kt DESC) AS form
    FROM (
        SELECT
            m2.kickoff_time AS kt,
            CASE
                WHEN (m2.home_team_id = m.home_team_id AND m2.home_goals > m2.away_goals)
                  OR (m2.away_team_id = m.home_team_id AND m2.away_goals > m2.home_goals) THEN 'W'
                WHEN m2.home_goals = m2.away_goals THEN 'D'
                ELSE 'L'
            END AS result
        FROM matches m2
        WHERE m2.status = 'final'
          AND m2.home_goals IS NOT NULL
          AND m2.kickoff_time < m.kickoff_time
          AND (m2.home_team_id = m.home_team_id OR m2.away_team_id = m.home_team_id)
        ORDER BY m2.kickoff_time DESC
        LIMIT 5
    ) sub
) hf ON TRUE
LEFT JOIN LATERAL (
    SELECT array_agg(result ORDER BY kt DESC) AS form
    FROM (
        SELECT
            m2.kickoff_time AS kt,
            CASE
                WHEN (m2.home_team_id = m.away_team_id AND m2.home_goals > m2.away_goals)
                  OR (m2.away_team_id = m.away_team_id AND m2.away_goals > m2.home_goals) THEN 'W'
                WHEN m2.home_goals = m2.away_goals THEN 'D'
                ELSE 'L'
            END AS result
        FROM matches m2
        WHERE m2.status = 'final'
          AND m2.home_goals IS NOT NULL
          AND m2.kickoff_time < m.kickoff_time
          AND (m2.home_team_id = m.away_team_id OR m2.away_team_id = m.away_team_id)
        ORDER BY m2.kickoff_time DESC
        LIMIT 5
    ) sub
) af ON TRUE
"""


async def list_matches(
    pool: asyncpg.Pool,
    *,
    upcoming_only: bool = True,
    limit: int = 20,
    league_code: str | None = None,
) -> list[asyncpg.Record]:
    conds: list[str] = []
    args: list = []
    if upcoming_only:
        conds.append("(m.status = 'live' OR m.kickoff_time >= NOW())")
    if league_code:
        args.append(league_code)
        conds.append(f"m.league_code = ${len(args)}")
    where = f"WHERE {' AND '.join(conds)}" if conds else ""
    if upcoming_only:
        order = (
            "CASE WHEN m.status = 'live' THEN 0 ELSE 1 END ASC, "
            "m.kickoff_time ASC"
        )
    else:
        order = "m.kickoff_time DESC"
    args.append(limit)
    query = f"{_MATCH_WITH_LATEST_PREDICTION} {where} ORDER BY {order} LIMIT ${len(args)}"
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def get_match_events(pool: asyncpg.Pool, match_id: int) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT minute, extra_minute, team_slug, player_name, assist_name,
                   event_type, event_detail
            FROM match_events
            WHERE match_id = $1
            ORDER BY minute ASC NULLS LAST, extra_minute ASC NULLS LAST, id ASC
            """,
            match_id,
        )
    return [dict(r) for r in rows]


async def get_match(pool: asyncpg.Pool, match_id: int) -> asyncpg.Record | None:
    query = f"{_MATCH_WITH_LATEST_PREDICTION} WHERE m.id = $1"
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, match_id)


async def fetch_finished_matches_df(
    pool: asyncpg.Pool,
    *,
    league_code: str | None = None,
) -> pd.DataFrame:
    """Return finished matches shaped for `compute_team_strengths`.
    Filter by league so Arsenal's strength isn't contaminated by La Liga xG.
    """
    query = """
    SELECT m.kickoff_time AS date,
           ht.name AS home_team, at.name AS away_team,
           m.home_goals, m.away_goals, m.home_xg, m.away_xg
    FROM matches m
    JOIN teams ht ON ht.id = m.home_team_id
    JOIN teams at ON at.id = m.away_team_id
    WHERE m.status = 'final'
      AND m.home_xg IS NOT NULL AND m.away_xg IS NOT NULL
    """
    args: list = []
    if league_code:
        args.append(league_code)
        query += f" AND m.league_code = ${len(args)}"
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
    df = pd.DataFrame([dict(r) for r in rows])
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df["is_result"] = True
    return df


async def insert_prediction(
    pool: asyncpg.Pool,
    match_id: int,
    pred: MatchPrediction,
    model_version: str,
    commitment_hash: str | None = None,
) -> int:
    scorelines_json = json.dumps(
        [{"home": h, "away": a, "prob": p} for h, a, p in pred.top_scorelines]
    )
    confidence = max(pred.p_home_win, pred.p_draw, pred.p_away_win)
    query = """
    INSERT INTO predictions (
        match_id, model_version, p_home_win, p_draw, p_away_win,
        expected_home_goals, expected_away_goals, top_scorelines, confidence,
        commitment_hash
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10)
    RETURNING id
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            query,
            match_id,
            model_version,
            pred.p_home_win,
            pred.p_draw,
            pred.p_away_win,
            pred.expected_home_goals,
            pred.expected_away_goals,
            scorelines_json,
            confidence,
            commitment_hash,
        )
    return row["id"]


async def update_prediction_reasoning(
    pool: asyncpg.Pool,
    prediction_id: int,
    reasoning: str,
    reasoning_model: str,
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE predictions SET reasoning = $2, reasoning_model = $3 WHERE id = $1",
            prediction_id,
            reasoning,
            reasoning_model,
        )


def record_to_match_dict(row: asyncpg.Record) -> dict[str, Any]:
    """Turn the flat SELECT row into the nested shape expected by `MatchOut`."""
    d = dict(row)

    home = {
        "slug": d.pop("home_slug"),
        "name": d.pop("home_name"),
        "short_name": d.pop("home_short"),
        "form": list(d.pop("home_form", None) or []),
    }
    away = {
        "slug": d.pop("away_slug"),
        "name": d.pop("away_name"),
        "short_name": d.pop("away_short"),
        "form": list(d.pop("away_form", None) or []),
    }

    prediction = None
    if d.get("p_home_win") is not None:
        scorelines = d.pop("top_scorelines") or "[]"
        if isinstance(scorelines, str):
            scorelines = json.loads(scorelines)
        prediction = {
            "p_home_win": d.pop("p_home_win"),
            "p_draw": d.pop("p_draw"),
            "p_away_win": d.pop("p_away_win"),
            "expected_home_goals": d.pop("expected_home_goals"),
            "expected_away_goals": d.pop("expected_away_goals"),
            "top_scorelines": scorelines,
            "reasoning": d.pop("reasoning"),
            "reasoning_model": d.pop("reasoning_model"),
            "model_version": d.pop("model_version"),
            "commitment_hash": d.pop("commitment_hash", None),
        }
    for k in (
        "p_home_win", "p_draw", "p_away_win",
        "expected_home_goals", "expected_away_goals",
        "top_scorelines", "reasoning", "reasoning_model", "model_version",
        "commitment_hash", "commitment_tx", "commitment_chain",
    ):
        d.pop(k, None)

    from app.ingest.odds import fair_probs

    odds = None
    oh, od, oa = d.pop("odds_home", None), d.pop("odds_draw", None), d.pop("odds_away", None)
    odds_source = d.pop("odds_source", None)
    if oh and od and oa:
        fair = fair_probs(float(oh), float(od), float(oa))
        if fair:
            odds = {
                "odds_home": float(oh),
                "odds_draw": float(od),
                "odds_away": float(oa),
                "fair_home": fair[0],
                "fair_draw": fair[1],
                "fair_away": fair[2],
                "source": odds_source,
            }
            if prediction:
                eh = prediction["p_home_win"] - fair[0]
                ed = prediction["p_draw"] - fair[1]
                ea = prediction["p_away_win"] - fair[2]
                odds["edge_home"] = eh
                odds["edge_draw"] = ed
                odds["edge_away"] = ea
                best = max([("H", eh), ("D", ed), ("A", ea)], key=lambda t: t[1])
                odds["best_outcome"] = best[0]
                odds["best_edge"] = best[1]

    # Live overlay — recompute probabilities from the current score + minute.
    live = None
    minute = d.pop("minute", None)
    live_updated_at = d.pop("live_updated_at", None)
    if (
        d.get("status") == "live"
        and minute is not None
        and prediction
        and d.get("home_goals") is not None
        and d.get("away_goals") is not None
    ):
        from app.models.poisson import live_probabilities

        lp = live_probabilities(
            prediction["expected_home_goals"],
            prediction["expected_away_goals"],
            int(d["home_goals"]),
            int(d["away_goals"]),
            minute=int(minute),
            rho=-0.15,
        )
        live = {
            "minute": int(minute),
            "live_updated_at": live_updated_at,
            "p_home_win": lp.p_home_win,
            "p_draw": lp.p_draw,
            "p_away_win": lp.p_away_win,
            "expected_remaining_home_goals": lp.expected_remaining_home_goals,
            "expected_remaining_away_goals": lp.expected_remaining_away_goals,
        }

    d["home"] = home
    d["away"] = away
    d["prediction"] = prediction
    d["odds"] = odds
    d["live"] = live
    d.pop("matchweek", None)
    return d
