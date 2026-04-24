"""Tipster self-signup + leaderboard.

No auth; a tipster picks a slug + 6-digit PIN (same pattern as /sync).
PIN hash is stored; all picks posted under that slug + PIN are scored
via log-loss. Frontend leaderboard ranks by log-loss ascending.
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/tipster-signup", tags=["tipsters"])


def _hash_pin(pin: str) -> str:
    return hashlib.sha256(("pl-tip:" + pin).encode("utf-8")).hexdigest()


class SignupBody(BaseModel):
    slug: str = Field(min_length=3, max_length=32, pattern=r"^[a-z0-9-]+$")
    display_name: str = Field(min_length=1, max_length=80)
    pin: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


@router.post("")
async def signup(body: SignupBody, request: Request) -> dict:
    pool = request.app.state.pool
    hashed = _hash_pin(body.pin)
    async with pool.acquire() as conn:
        # Check slug available
        existing = await conn.fetchval(
            "SELECT id FROM tipsters WHERE slug = $1", body.slug,
        )
        if existing:
            raise HTTPException(400, "slug taken")
        await conn.execute(
            """
            INSERT INTO tipsters (slug, display_name, pin_hash, created_at)
            VALUES ($1, $2, $3, NOW())
            """,
            body.slug, body.display_name, hashed,
        )
    return {"ok": True, "slug": body.slug}


class LeaderboardRow(BaseModel):
    slug: str
    display_name: str
    picks: int
    hits: int
    accuracy: float
    log_loss: float


@router.get("/leaderboard", response_model=list[LeaderboardRow])
async def leaderboard(request: Request) -> list[LeaderboardRow]:
    # Score each pick from the actual match outcome; log-loss uses the
    # tipster's stated confidence. tipster_picks has no hit/log_loss
    # columns — derive in SQL via matches.home_goals/away_goals.
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH graded AS (
                SELECT tp.tipster_id, tp.pick, tp.confidence,
                       CASE
                         WHEN m.home_goals > m.away_goals THEN 'H'
                         WHEN m.home_goals < m.away_goals THEN 'A'
                         ELSE 'D'
                       END AS actual
                FROM tipster_picks tp
                JOIN matches m ON m.id = tp.match_id
                WHERE m.status = 'final' AND m.home_goals IS NOT NULL
            )
            SELECT t.slug,
                   COALESCE(t.display_name, t.slug) AS display_name,
                   COUNT(g.tipster_id)::int AS picks,
                   COUNT(g.tipster_id) FILTER (WHERE g.pick = g.actual)::int AS hits,
                   AVG(
                     -LN(GREATEST(1e-6, LEAST(1 - 1e-6,
                       CASE WHEN g.pick = g.actual THEN g.confidence ELSE 1 - g.confidence END
                     )))
                   )::float AS log_loss
            FROM tipsters t
            LEFT JOIN graded g ON g.tipster_id = t.id
            GROUP BY t.slug, t.display_name
            HAVING COUNT(g.tipster_id) >= 5
            ORDER BY AVG(
              -LN(GREATEST(1e-6, LEAST(1 - 1e-6,
                CASE WHEN g.pick = g.actual THEN g.confidence ELSE 1 - g.confidence END
              )))
            ) ASC NULLS LAST
            LIMIT 50
            """,
        )
    out = []
    for r in rows:
        n = int(r["picks"] or 0)
        out.append(LeaderboardRow(
            slug=r["slug"], display_name=r["display_name"],
            picks=n,
            hits=int(r["hits"] or 0),
            accuracy=(int(r["hits"] or 0) / n) if n > 0 else 0.0,
            log_loss=float(r["log_loss"] or 0.0),
        ))
    return out
