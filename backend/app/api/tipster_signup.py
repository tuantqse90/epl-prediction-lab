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
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.slug, t.display_name,
                   COUNT(tp.id) AS picks,
                   COUNT(tp.id) FILTER (WHERE tp.hit) AS hits,
                   AVG(tp.log_loss)::float AS log_loss
            FROM tipsters t
            LEFT JOIN tipster_picks tp ON tp.tipster_id = t.id AND tp.log_loss IS NOT NULL
            GROUP BY t.slug, t.display_name
            HAVING COUNT(tp.id) >= 5
            ORDER BY AVG(tp.log_loss) ASC NULLS LAST
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
