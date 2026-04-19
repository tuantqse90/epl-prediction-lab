"""Community tipster leaderboard — auth-less.

Flow: FE prompts for a handle once, stores locally. Every pick submits to
/api/tipsters/picks with (handle, match_id, pick, confidence). After a
match settles, log-loss scoring runs on demand when the leaderboard is
queried. Rank ascending (lower = better).
"""

from __future__ import annotations

import math
import re

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/tipsters", tags=["tipsters"])

_HANDLE_RE = re.compile(r"^[a-zA-Z0-9_\-.]{2,24}$")


class PickIn(BaseModel):
    handle: str
    match_id: int
    pick: str = Field(pattern="^(H|D|A)$")
    confidence: float = Field(gt=0, le=1.0)


class LeaderRow(BaseModel):
    rank: int
    handle: str
    picks: int
    settled: int
    correct: int
    accuracy: float
    mean_log_loss: float


@router.post("/picks")
async def submit_pick(pick: PickIn, request: Request) -> dict[str, bool]:
    if not _HANDLE_RE.match(pick.handle):
        raise HTTPException(400, "handle must be 2-24 chars, alnum/._-")
    if pick.pick not in ("H", "D", "A"):
        raise HTTPException(400, "pick must be H / D / A")

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # Refuse picks on already-started or settled matches — cheaters gonna cheat,
        # but the deadline makes the lb honest in aggregate.
        allowed = await conn.fetchval(
            """
            SELECT m.status = 'scheduled' AND m.kickoff_time > NOW()
            FROM matches m WHERE m.id = $1
            """,
            pick.match_id,
        )
        if allowed is None:
            raise HTTPException(404, f"match {pick.match_id} not found")
        if not allowed:
            raise HTTPException(400, "match already started or finished")

        tipster_id = await conn.fetchval(
            """
            INSERT INTO tipsters (handle) VALUES ($1)
            ON CONFLICT (handle) DO UPDATE SET handle = EXCLUDED.handle
            RETURNING id
            """,
            pick.handle,
        )
        await conn.execute(
            """
            INSERT INTO tipster_picks (tipster_id, match_id, pick, confidence)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (tipster_id, match_id) DO UPDATE SET
                pick = EXCLUDED.pick,
                confidence = EXCLUDED.confidence,
                created_at = NOW()
            """,
            tipster_id, pick.match_id, pick.pick, pick.confidence,
        )
    return {"ok": True}


@router.get("/leaderboard", response_model=list[LeaderRow])
async def leaderboard(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    min_picks: int = Query(3, ge=1, le=100),
    limit: int = Query(50, ge=1, le=200),
) -> list[LeaderRow]:
    """Rank tipsters by mean log-loss over matches settled in the last N days."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.handle,
                   tp.pick, tp.confidence,
                   m.home_goals, m.away_goals
            FROM tipster_picks tp
            JOIN tipsters t ON t.id = tp.tipster_id
            JOIN matches m  ON m.id = tp.match_id
            WHERE m.status = 'final'
              AND m.home_goals IS NOT NULL
              AND m.kickoff_time >= NOW() - ($1 || ' days')::INTERVAL
            """,
            str(days),
        )

    by_handle: dict[str, dict] = {}
    for r in rows:
        entry = by_handle.setdefault(r["handle"], {
            "picks": 0, "correct": 0, "ll_sum": 0.0,
        })
        entry["picks"] += 1
        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        actual = "H" if hg > ag else ("A" if ag > hg else "D")
        if actual == r["pick"]:
            entry["correct"] += 1
        # log-loss treats the tipster's stated confidence as the probability on
        # their chosen outcome, with (1 - confidence) spread evenly over the
        # other two — a rough but fair Brier-style scoring.
        c = float(r["confidence"])
        p_outcome = c if r["pick"] == actual else (1.0 - c) / 2.0
        entry["ll_sum"] += -math.log(max(p_outcome, 1e-6))

    lb: list[LeaderRow] = []
    for handle, e in by_handle.items():
        if e["picks"] < min_picks:
            continue
        lb.append(LeaderRow(
            rank=0,
            handle=handle,
            picks=e["picks"],
            settled=e["picks"],
            correct=e["correct"],
            accuracy=e["correct"] / e["picks"],
            mean_log_loss=e["ll_sum"] / e["picks"],
        ))

    lb.sort(key=lambda x: x.mean_log_loss)
    for i, r in enumerate(lb, 1):
        r.rank = i
    return lb[:limit]
