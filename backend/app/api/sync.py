"""GET /api/sync/:pin and POST /api/sync/:pin — cross-device localStorage sync.

A user picks a 6-digit PIN in their browser; /api/sync stores the
JSON payload keyed on sha256(PIN). Another device types the same PIN
and pulls the payload back. No email, no password, no account.

Collision protection: 10^6 keyspace is small; we rate-limit by IP +
reject non-numeric PINs. The payload has a version to detect clobber
conflicts; clients prefer the larger version on merge.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from time import monotonic

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/sync", tags=["sync"])


def _hash_pin(pin: str) -> str:
    return hashlib.sha256(("pl-sync:" + pin).encode("utf-8")).hexdigest()


def _is_valid_pin(pin: str) -> bool:
    return pin.isdigit() and len(pin) == 6


# Simple per-IP rate limit. Not distributed — fine for a single VPS.
_HIT_COUNTER: dict[str, list[float]] = defaultdict(list)
_WINDOW_SEC = 60.0
_MAX_HITS = 30


def _rate_limit_ok(ip: str) -> bool:
    now = monotonic()
    bucket = _HIT_COUNTER[ip]
    # Drop expired hits
    cutoff = now - _WINDOW_SEC
    bucket[:] = [t for t in bucket if t >= cutoff]
    if len(bucket) >= _MAX_HITS:
        return False
    bucket.append(now)
    return True


class PushPayload(BaseModel):
    payload: dict
    version: int = Field(ge=1)


class PushAck(BaseModel):
    ok: bool
    version: int


class Pull(BaseModel):
    ok: bool
    payload: dict | None
    version: int | None
    updated_at: str | None


@router.get("/{pin}", response_model=Pull)
async def pull(pin: str, request: Request) -> Pull:
    ip = request.client.host if request.client else "?"
    if not _rate_limit_ok(ip):
        raise HTTPException(status_code=429, detail="too many requests")
    if not _is_valid_pin(pin):
        raise HTTPException(status_code=400, detail="pin must be 6 digits")
    pool = request.app.state.pool
    hashed = _hash_pin(pin)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT payload, version, updated_at FROM user_sync WHERE pin = $1",
            hashed,
        )
    if not row:
        return Pull(ok=True, payload=None, version=None, updated_at=None)
    # asyncpg returns JSONB as str or dict depending on codec config; handle both.
    payload = row["payload"]
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {}
    return Pull(
        ok=True,
        payload=payload,
        version=int(row["version"]),
        updated_at=row["updated_at"].isoformat(),
    )


@router.post("/{pin}", response_model=PushAck)
async def push(pin: str, body: PushPayload, request: Request) -> PushAck:
    ip = request.client.host if request.client else "?"
    if not _rate_limit_ok(ip):
        raise HTTPException(status_code=429, detail="too many requests")
    if not _is_valid_pin(pin):
        raise HTTPException(status_code=400, detail="pin must be 6 digits")
    pool = request.app.state.pool
    hashed = _hash_pin(pin)
    payload_json = json.dumps(body.payload)
    async with pool.acquire() as conn:
        new_version = await conn.fetchval(
            """
            INSERT INTO user_sync (pin, payload, version)
            VALUES ($1, $2::jsonb, $3)
            ON CONFLICT (pin) DO UPDATE SET
              payload = EXCLUDED.payload,
              version = GREATEST(user_sync.version + 1, EXCLUDED.version),
              updated_at = NOW()
            RETURNING version
            """,
            hashed, payload_json, body.version,
        )
    return PushAck(ok=True, version=int(new_version))
