"""Web Push subscription management + dispatcher.

VAPID keys are read from env (VAPID_PUBLIC_KEY + VAPID_PRIVATE_KEY, both
base64-url-safe). Generate once with:

    from py_vapid import Vapid
    v = Vapid(); v.generate_keys()
    print(v.private_pem().decode(), v.public_key.encode_point().hex())

Dispatch is called from ingest_live_scores goal-alert path; delivery is
best-effort per row and silently drops 410 Gone subscriptions.
"""

from __future__ import annotations

import json
import logging
import os

import asyncpg
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/push", tags=["push"])

log = logging.getLogger("push")


class Subscription(BaseModel):
    endpoint: str
    keys: dict[str, str]    # {"p256dh": "...", "auth": "..."}
    teams: list[str] = []
    user_agent: str | None = None


@router.get("/config")
async def config() -> dict[str, str | None]:
    return {"public_key": os.environ.get("VAPID_PUBLIC_KEY")}


@router.post("/subscribe")
async def subscribe(sub: Subscription, request: Request) -> dict[str, bool]:
    pool = request.app.state.pool
    p256dh = sub.keys.get("p256dh")
    auth = sub.keys.get("auth")
    if not p256dh or not auth:
        raise HTTPException(400, "missing p256dh or auth key")
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO push_subscriptions (endpoint, p256dh, auth, teams, user_agent)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (endpoint) DO UPDATE SET
                p256dh = EXCLUDED.p256dh,
                auth   = EXCLUDED.auth,
                teams  = EXCLUDED.teams,
                user_agent = EXCLUDED.user_agent
            """,
            sub.endpoint, p256dh, auth, sub.teams, sub.user_agent,
        )
    return {"ok": True}


@router.post("/unsubscribe")
async def unsubscribe(body: dict, request: Request) -> dict[str, bool]:
    endpoint = body.get("endpoint")
    if not endpoint:
        raise HTTPException(400, "missing endpoint")
    pool = request.app.state.pool
    await pool.execute("DELETE FROM push_subscriptions WHERE endpoint = $1", endpoint)
    return {"ok": True}


async def dispatch_goal(pool: asyncpg.Pool, team_slugs: list[str], payload: dict) -> int:
    """Best-effort push delivery to everyone who follows any of `team_slugs`."""
    priv = os.environ.get("VAPID_PRIVATE_KEY")
    claim_sub = os.environ.get("VAPID_SUBJECT", "mailto:ops@nullshift.sh")
    if not priv or not team_slugs:
        return 0

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        log.warning("pywebpush not installed; skipping push dispatch")
        return 0

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, endpoint, p256dh, auth
            FROM push_subscriptions
            WHERE teams && $1::text[]
            """,
            team_slugs,
        )

    sent = 0
    for r in rows:
        try:
            webpush(
                subscription_info={
                    "endpoint": r["endpoint"],
                    "keys": {"p256dh": r["p256dh"], "auth": r["auth"]},
                },
                data=json.dumps(payload),
                vapid_private_key=priv,
                vapid_claims={"sub": claim_sub},
            )
            sent += 1
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE push_subscriptions SET last_success_at = NOW() WHERE id = $1",
                    r["id"],
                )
        except WebPushException as e:
            status = getattr(e.response, "status_code", 0) if e.response else 0
            if status in (404, 410):
                async with pool.acquire() as conn:
                    await conn.execute(
                        "DELETE FROM push_subscriptions WHERE id = $1", r["id"],
                    )
            else:
                log.warning("push send failed: %s", e)
        except Exception as e:
            log.warning("push send error: %s", e)
    return sent
