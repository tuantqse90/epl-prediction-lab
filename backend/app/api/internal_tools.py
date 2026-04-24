"""Admin-gated internal tools — error dashboard, feature flags, page views.

All POST endpoints require X-Admin-Token = ADMIN_TOKEN env. GET /analytics
is OPEN (public-safe — no PII, only path counts).
"""

from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel


router = APIRouter(tags=["internal"])


def _admin_ok(token: str | None) -> bool:
    expected = os.environ.get("ADMIN_TOKEN")
    return bool(expected) and token == expected


# --- errors --------------------------------------------------------------


class ErrorRow(BaseModel):
    ts: datetime
    request_id: str
    method: str | None
    path: str
    query: str | None
    error_class: str
    message: str | None


class ErrorListResponse(BaseModel):
    total: int
    rows: list[ErrorRow]


@router.get("/api/admin/errors", response_model=ErrorListResponse)
async def list_errors(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    window_hours: int = Query(24, ge=1, le=168),
    x_admin_token: str | None = Header(default=None),
) -> ErrorListResponse:
    if not _admin_ok(x_admin_token):
        raise HTTPException(status_code=403, detail="bad admin token")
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ts, request_id, method, path, query, error_class, message
            FROM error_events
            WHERE ts > NOW() - ($1 || ' hours')::INTERVAL
            ORDER BY ts DESC
            LIMIT $2
            """,
            str(window_hours), limit,
        )
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM error_events WHERE ts > NOW() - ($1 || ' hours')::INTERVAL",
            str(window_hours),
        )
    return ErrorListResponse(
        total=int(total or 0),
        rows=[ErrorRow(**dict(r)) for r in rows],
    )


# --- feature flags --------------------------------------------------------


class Flag(BaseModel):
    key: str
    enabled: bool
    rollout_pct: int
    description: str | None


@router.get("/api/flags", response_model=list[Flag])
async def list_flags(request: Request) -> list[Flag]:
    """Public read — client uses this to decide UI branches."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT key, enabled, rollout_pct, description FROM feature_flags ORDER BY key"
        )
    return [Flag(**dict(r)) for r in rows]


class FlagUpdate(BaseModel):
    enabled: bool
    rollout_pct: int = 0
    description: str | None = None


@router.put("/api/admin/flags/{key}", response_model=Flag)
async def set_flag(
    key: str, body: FlagUpdate,
    request: Request,
    x_admin_token: str | None = Header(default=None),
) -> Flag:
    if not _admin_ok(x_admin_token):
        raise HTTPException(status_code=403, detail="bad admin token")
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO feature_flags (key, enabled, rollout_pct, description)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (key) DO UPDATE SET
              enabled = EXCLUDED.enabled,
              rollout_pct = EXCLUDED.rollout_pct,
              description = COALESCE(EXCLUDED.description, feature_flags.description),
              updated_at = NOW()
            RETURNING key, enabled, rollout_pct, description
            """,
            key, body.enabled, body.rollout_pct, body.description,
        )
    return Flag(**dict(row))


# --- analytics -----------------------------------------------------------


class PageViewIn(BaseModel):
    path: str
    referrer: str | None = None
    lang: str | None = None
    session_id: str | None = None


@router.post("/api/analytics/pv")
async def post_pv(
    body: PageViewIn, request: Request,
    cf_ipcountry: str | None = Header(default=None),
) -> dict:
    """Lightweight page-view logger. No IP stored; country only when
    Cloudflare-IPCountry header is present."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO page_views (path, referrer, country, lang, session_id)
            VALUES ($1, $2, $3, $4, $5)
            """,
            body.path[:200],
            (body.referrer or "")[:500] or None,
            cf_ipcountry,
            body.lang,
            (body.session_id or "")[:64] or None,
        )
    return {"ok": True}


class AnalyticsRow(BaseModel):
    path: str
    views: int
    unique_sessions: int


@router.get("/api/admin/analytics", response_model=list[AnalyticsRow])
async def analytics_top_paths(
    request: Request,
    window_hours: int = Query(24, ge=1, le=720),
    limit: int = Query(30, ge=1, le=200),
    x_admin_token: str | None = Header(default=None),
) -> list[AnalyticsRow]:
    if not _admin_ok(x_admin_token):
        raise HTTPException(status_code=403, detail="bad admin token")
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT path,
                   COUNT(*)::int AS views,
                   COUNT(DISTINCT session_id)::int AS unique_sessions
            FROM page_views
            WHERE ts > NOW() - ($1 || ' hours')::INTERVAL
            GROUP BY path
            ORDER BY views DESC
            LIMIT $2
            """,
            str(window_hours), limit,
        )
    return [AnalyticsRow(**dict(r)) for r in rows]
