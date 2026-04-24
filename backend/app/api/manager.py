"""Manager tenure endpoints.

GET /api/teams/:slug/manager                  — current manager + tenure history
GET /api/matches/:id/manager-bounce           — are either side's managers < 30 days in the job?
POST /api/admin/manager                       — insert a tenure entry (admin-authorized via header)
"""

from __future__ import annotations

import os
from datetime import date, datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel


router = APIRouter(tags=["manager"])


class Tenure(BaseModel):
    manager_name: str
    started_at: date
    ended_at: date | None
    days: int
    is_current: bool


class ManagerHistory(BaseModel):
    team_slug: str
    current: Tenure | None
    history: list[Tenure]


def _days_since(d: date) -> int:
    return (datetime.now(timezone.utc).date() - d).days


@router.get("/api/teams/{slug}/manager", response_model=ManagerHistory)
async def team_manager(slug: str, request: Request) -> ManagerHistory:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT manager_name, started_at, ended_at
            FROM manager_tenure
            WHERE team_slug = $1
            ORDER BY started_at DESC
            """,
            slug,
        )
    all_ten = []
    current: Tenure | None = None
    for r in rows:
        ended = r["ended_at"]
        tenure = Tenure(
            manager_name=r["manager_name"],
            started_at=r["started_at"],
            ended_at=ended,
            days=(ended - r["started_at"]).days if ended else _days_since(r["started_at"]),
            is_current=ended is None,
        )
        all_ten.append(tenure)
        if tenure.is_current and current is None:
            current = tenure
    return ManagerHistory(team_slug=slug, current=current, history=all_ten)


class BounceFlag(BaseModel):
    team_slug: str
    manager_name: str
    days_in_charge: int


class MatchBounce(BaseModel):
    match_id: int
    flags: list[BounceFlag]        # empty = both managers stable (>30d)


@router.get("/api/matches/{match_id}/manager-bounce", response_model=MatchBounce)
async def match_bounce(
    match_id: int,
    request: Request,
    threshold_days: int = Query(30, ge=1, le=365),
) -> MatchBounce:
    """Either side with a manager < N days in job → flag the potential
    'new manager bounce'."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        teams = await conn.fetchrow(
            """
            SELECT ht.slug AS home_slug, at.slug AS away_slug
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.id = $1
            """,
            match_id,
        )
        if not teams:
            raise HTTPException(404, "match not found")
        rows = await conn.fetch(
            """
            SELECT team_slug, manager_name, started_at
            FROM manager_tenure
            WHERE team_slug = ANY($1::text[]) AND ended_at IS NULL
            """,
            [teams["home_slug"], teams["away_slug"]],
        )
    flags: list[BounceFlag] = []
    for r in rows:
        days = _days_since(r["started_at"])
        if days <= threshold_days:
            flags.append(BounceFlag(
                team_slug=r["team_slug"],
                manager_name=r["manager_name"],
                days_in_charge=days,
            ))
    return MatchBounce(match_id=match_id, flags=flags)


class AdminManagerBody(BaseModel):
    team_slug: str
    manager_name: str
    started_at: date
    ended_at: date | None = None
    source_url: str | None = None


@router.post("/api/admin/manager")
async def admin_insert_manager(
    body: AdminManagerBody,
    request: Request,
    x_admin_token: str | None = Header(default=None),
):
    """Admin-only: insert a tenure. Close the prior open tenure if any."""
    token = os.environ.get("ADMIN_TOKEN")
    if not token or x_admin_token != token:
        raise HTTPException(status_code=403, detail="bad admin token")
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Close any open tenure for this team one day before new start.
            await conn.execute(
                """
                UPDATE manager_tenure
                SET ended_at = ($1::date - INTERVAL '1 day')::date
                WHERE team_slug = $2 AND ended_at IS NULL
                """,
                body.started_at, body.team_slug,
            )
            await conn.execute(
                """
                INSERT INTO manager_tenure (team_slug, manager_name, started_at, ended_at, source_url)
                VALUES ($1, $2, $3, $4, $5)
                """,
                body.team_slug, body.manager_name, body.started_at, body.ended_at, body.source_url,
            )
    return {"ok": True}
