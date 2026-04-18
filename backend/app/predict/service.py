"""Orchestration: DB rows → team strengths → Poisson prediction → persist.

Called on-demand by the API and in bulk by `scripts/predict_upcoming.py`.
"""

from __future__ import annotations

import asyncpg
import pandas as pd

from app import queries
from app.models.features import TeamStrength, compute_team_strengths, match_lambdas
from app.models.poisson import MatchPrediction, predict_match
from app.onchain.commitment import commitment_hash

NEUTRAL = TeamStrength(attack=1.0, defense=1.0)


async def predict_and_persist(
    pool: asyncpg.Pool,
    match_id: int,
    *,
    rho: float,
    model_version: str,
    last_n: int = 12,
    temperature: float = 1.0,
) -> tuple[int, MatchPrediction]:
    """Predict a single match and write a `predictions` row. Returns (prediction_id, result)."""
    match = await queries.get_match(pool, match_id)
    if match is None:
        raise ValueError(f"match {match_id} not found")

    league_code = match["league_code"] if match["league_code"] else None
    df = await queries.fetch_finished_matches_df(pool, league_code=league_code)
    if df.empty:
        raise RuntimeError(
            f"no finished matches with xG for league {league_code!r} — run ingest first"
        )

    strengths = compute_team_strengths(df, as_of=match["kickoff_time"], last_n=last_n)
    home = strengths.get(match["home_name"], NEUTRAL)
    away = strengths.get(match["away_name"], NEUTRAL)

    league_avg = float(pd.concat([df["home_goals"], df["away_goals"]]).mean())
    lam_h, lam_a = match_lambdas(home, away, league_avg_goals=league_avg)

    result = predict_match(lam_h, lam_a, rho=rho, temperature=temperature)
    tagged_version = f"{model_version}:rho={rho}:T={temperature}"
    digest = commitment_hash(
        prediction=result,
        match_id=match_id,
        kickoff_unix=int(match["kickoff_time"].timestamp()),
        model_version=tagged_version,
        rho=rho,
    )
    pred_id = await queries.insert_prediction(
        pool, match_id, result, tagged_version, commitment_hash=digest
    )
    return pred_id, result


async def predict_all_upcoming(
    pool: asyncpg.Pool,
    *,
    rho: float,
    model_version: str,
    horizon_days: int = 14,
    last_n: int = 12,
    temperature: float = 1.0,
    league_code: str | None = None,
) -> list[int]:
    async with pool.acquire() as conn:
        if league_code:
            rows = await conn.fetch(
                """
                SELECT id FROM matches
                WHERE status = 'scheduled'
                  AND league_code = $2
                  AND kickoff_time BETWEEN NOW() AND NOW() + ($1 || ' days')::INTERVAL
                ORDER BY kickoff_time ASC
                """,
                str(horizon_days), league_code,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id FROM matches
                WHERE status = 'scheduled'
                  AND kickoff_time BETWEEN NOW() AND NOW() + ($1 || ' days')::INTERVAL
                ORDER BY kickoff_time ASC
                """,
                str(horizon_days),
            )
    created: list[int] = []
    for r in rows:
        pid, _ = await predict_and_persist(
            pool, r["id"],
            rho=rho, model_version=model_version,
            last_n=last_n, temperature=temperature,
        )
        created.append(pid)
    return created
