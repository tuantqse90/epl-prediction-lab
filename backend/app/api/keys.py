"""Developer API keys + rate-limited gateway + webhook registry.

Admin-only endpoints under /api/admin/keys (need X-Admin-Token).
Public endpoint /api/developer/status shows current key's identity +
remaining quota so integrators can self-debug.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel, HttpUrl


router = APIRouter(tags=["developer"])


def _admin_ok(token: str | None) -> bool:
    expected = os.environ.get("ADMIN_TOKEN")
    return bool(expected) and token == expected


def _hash_key(raw: str) -> str:
    return hashlib.sha256(("pl-api:" + raw).encode("utf-8")).hexdigest()


# ---------------- admin ops ----------------


class IssueBody(BaseModel):
    label: str
    rate_limit: int = 60
    cors_origins: list[str] = []


class IssuedKey(BaseModel):
    id: int
    key: str                     # shown ONCE, at issuance time
    key_prefix: str
    label: str
    rate_limit: int


@router.post("/api/admin/keys", response_model=IssuedKey)
async def issue_key(
    body: IssueBody,
    request: Request,
    x_admin_token: str | None = Header(default=None),
) -> IssuedKey:
    if not _admin_ok(x_admin_token):
        raise HTTPException(status_code=403, detail="bad admin token")
    raw = "pl_" + secrets.token_urlsafe(30)
    prefix = raw[:8]
    hashed = _hash_key(raw)
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO api_keys (key_hash, key_prefix, label, rate_limit, cors_origins)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            hashed, prefix, body.label, body.rate_limit, body.cors_origins,
        )
    return IssuedKey(
        id=int(row["id"]), key=raw, key_prefix=prefix,
        label=body.label, rate_limit=body.rate_limit,
    )


class KeyRow(BaseModel):
    id: int
    key_prefix: str
    label: str | None
    rate_limit: int
    created_at: datetime
    last_used_at: datetime | None
    revoked: bool


@router.get("/api/admin/keys", response_model=list[KeyRow])
async def list_keys(
    request: Request, x_admin_token: str | None = Header(default=None),
) -> list[KeyRow]:
    if not _admin_ok(x_admin_token):
        raise HTTPException(status_code=403, detail="bad admin token")
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, key_prefix, label, rate_limit, created_at, last_used_at, revoked_at
            FROM api_keys ORDER BY id DESC
            """
        )
    return [
        KeyRow(
            id=int(r["id"]), key_prefix=r["key_prefix"], label=r["label"],
            rate_limit=int(r["rate_limit"]),
            created_at=r["created_at"], last_used_at=r["last_used_at"],
            revoked=r["revoked_at"] is not None,
        )
        for r in rows
    ]


@router.post("/api/admin/keys/{key_id}/revoke")
async def revoke_key(
    key_id: int, request: Request,
    x_admin_token: str | None = Header(default=None),
) -> dict:
    if not _admin_ok(x_admin_token):
        raise HTTPException(status_code=403, detail="bad admin token")
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE api_keys SET revoked_at = NOW() WHERE id = $1", key_id
        )
    return {"ok": True}


# ---------------- developer self-status ----------------


# In-process token bucket keyed on key_prefix. Sliding 60-second window.
_RL: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=2000))


async def _resolve_key(auth_header: str | None, pool) -> tuple[int, str, int] | None:
    """Returns (id, prefix, rate_limit) if valid + not revoked, else None."""
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    raw = auth_header.removeprefix("Bearer ").strip()
    hashed = _hash_key(raw)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, key_prefix, rate_limit
            FROM api_keys WHERE key_hash = $1 AND revoked_at IS NULL
            """,
            hashed,
        )
    if not row:
        return None
    return (int(row["id"]), row["key_prefix"], int(row["rate_limit"]))


def _rate_limited(prefix: str, limit_per_min: int) -> bool:
    now = time.monotonic()
    bucket = _RL[prefix]
    cutoff = now - 60.0
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= limit_per_min:
        return True
    bucket.append(now)
    return False


@router.get("/api/developer/status")
async def dev_status(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    pool = request.app.state.pool
    info = await _resolve_key(authorization, pool)
    if info is None:
        return {"ok": False, "reason": "no or invalid bearer token"}
    key_id, prefix, limit = info
    bucket = _RL[prefix]
    used = len(bucket)
    return {
        "ok": True,
        "key_prefix": prefix,
        "rate_limit_per_min": limit,
        "used_last_60s": used,
        "remaining": max(0, limit - used),
    }


# ---------------- webhook register ----------------


class WebhookBody(BaseModel):
    url: HttpUrl
    event_types: list[str] = ["prediction_created", "match_final"]


@router.post("/api/developer/webhooks")
async def register_webhook(
    body: WebhookBody, request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    pool = request.app.state.pool
    info = await _resolve_key(authorization, pool)
    if info is None:
        raise HTTPException(status_code=401, detail="auth required")
    key_id, _, _ = info
    async with pool.acquire() as conn:
        new_id = await conn.fetchval(
            """
            INSERT INTO api_webhooks (key_id, url, event_types)
            VALUES ($1, $2, $3) RETURNING id
            """,
            key_id, str(body.url), body.event_types,
        )
    return {"ok": True, "id": int(new_id)}
