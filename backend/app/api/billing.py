"""Billing — Stripe Checkout + subscription lifecycle.

Inactive by default. Activates when STRIPE_API_KEY is set in env.

Flow:
    1. User hits /pricing → clicks "Upgrade" → POST /api/billing/checkout
       with their email. We create a Stripe Checkout Session + return the
       URL. Success URL forwards to /billing with session_id.
    2. On successful Checkout, Stripe posts a webhook to
       /api/billing/webhook (secret-verified). We:
         - create an api_keys row if one doesn't exist for this email
         - stamp tier='pro' + stripe_customer_id + stripe_subscription_id
         - email the user their raw API key (only once)
    3. /billing page reads by email via pin-style lookup — user types
       their email; we return tier + period_end + key_prefix (never the
       raw key).
    4. Subsequent webhooks (invoice paid, subscription canceled) update
       the row accordingly.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr


router = APIRouter(prefix="/api/billing", tags=["billing"])


SITE = "https://predictor.nullshift.sh"


def _stripe_enabled() -> bool:
    return bool(os.environ.get("STRIPE_API_KEY"))


def _stripe_post(path: str, data: dict) -> dict:
    """Minimal Stripe REST call — form-encoded, returns parsed JSON."""
    key = os.environ["STRIPE_API_KEY"]
    url = f"https://api.stripe.com/v1/{path}"
    body = urllib.parse.urlencode(data, doseq=True).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _hash_key(raw: str) -> str:
    return hashlib.sha256(("pl-api:" + raw).encode("utf-8")).hexdigest()


# -----------------------------------------------------------------------
# Checkout session creation
# -----------------------------------------------------------------------


class CheckoutBody(BaseModel):
    email: EmailStr


class CheckoutAck(BaseModel):
    ok: bool
    checkout_url: str | None = None
    fallback: str | None = None


@router.post("/checkout", response_model=CheckoutAck)
async def checkout(body: CheckoutBody) -> CheckoutAck:
    if not _stripe_enabled():
        # Graceful degradation: no Stripe key → point at Ko-Fi.
        return CheckoutAck(
            ok=True,
            checkout_url=None,
            fallback=os.environ.get("DONATION_URL", "https://ko-fi.com/predictor"),
        )
    price_id = os.environ.get("STRIPE_PRICE_ID")
    if not price_id:
        raise HTTPException(500, "STRIPE_PRICE_ID missing in env")
    data = {
        "mode": "subscription",
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": 1,
        "customer_email": str(body.email),
        "success_url": f"{SITE}/billing?session={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{SITE}/pricing",
        "allow_promotion_codes": "true",
    }
    try:
        resp = _stripe_post("checkout/sessions", data)
    except Exception as e:
        raise HTTPException(502, f"stripe error: {type(e).__name__}: {e}")
    url = resp.get("url")
    if not url:
        raise HTTPException(502, f"stripe returned no url: {resp}")
    return CheckoutAck(ok=True, checkout_url=url)


# -----------------------------------------------------------------------
# Webhook
# -----------------------------------------------------------------------


def _verify_stripe_sig(raw_body: bytes, sig_header: str, secret: str) -> bool:
    """Stripe's scheme: `Stripe-Signature: t=<ts>,v1=<sig>`. We HMAC-SHA256
    the `<ts>.<raw_body>` with the webhook secret and compare to v1."""
    try:
        parts = dict(kv.split("=", 1) for kv in sig_header.split(","))
        ts = parts.get("t")
        v1 = parts.get("v1")
        if not ts or not v1:
            return False
        signed = f"{ts}.".encode("utf-8") + raw_body
        expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, v1)
    except Exception:
        return False


@router.post("/webhook")
async def webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict:
    if not _stripe_enabled():
        raise HTTPException(503, "billing disabled")
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    raw = await request.body()
    if secret:
        if not stripe_signature or not _verify_stripe_sig(raw, stripe_signature, secret):
            raise HTTPException(400, "bad signature")
    try:
        event = json.loads(raw)
    except Exception:
        raise HTTPException(400, "bad json")

    etype = event.get("type") or ""
    obj = (event.get("data") or {}).get("object") or {}
    pool = request.app.state.pool

    async def _upsert_pro(email: str, cust_id: str | None, sub_id: str | None,
                         status: str, period_end_ts: int | None):
        if not email:
            return
        period_end = (
            datetime.fromtimestamp(int(period_end_ts), tz=timezone.utc)
            if period_end_ts else None
        )
        async with pool.acquire() as conn:
            # Upsert by email — one pro row per email.
            existing = await conn.fetchrow(
                "SELECT id FROM api_keys WHERE email = $1 ORDER BY id DESC LIMIT 1", email
            )
            if existing:
                await conn.execute(
                    """
                    UPDATE api_keys
                    SET tier = 'pro',
                        stripe_customer_id = COALESCE($2, stripe_customer_id),
                        stripe_subscription_id = COALESCE($3, stripe_subscription_id),
                        subscription_status = $4,
                        current_period_end = COALESCE($5, current_period_end)
                    WHERE id = $1
                    """,
                    existing["id"], cust_id, sub_id, status, period_end,
                )
            else:
                # Create a new pro key for first-time payers.
                raw_key = "pl_" + secrets.token_urlsafe(30)
                await conn.execute(
                    """
                    INSERT INTO api_keys (
                        key_hash, key_prefix, label, rate_limit, tier,
                        email, stripe_customer_id, stripe_subscription_id,
                        subscription_status, current_period_end
                    ) VALUES ($1, $2, $3, $4, 'pro', $5, $6, $7, $8, $9)
                    """,
                    _hash_key(raw_key), raw_key[:8], f"pro-{email}", 600,
                    email, cust_id, sub_id, status, period_end,
                )
                # TODO: email raw_key to the user once email transport is live.
                print(f"[billing] new pro key minted for {email}: {raw_key}")

    async def _mark_cancelled(sub_id: str):
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE api_keys
                SET subscription_status = 'canceled'
                WHERE stripe_subscription_id = $1
                """,
                sub_id,
            )

    if etype == "checkout.session.completed":
        email = obj.get("customer_email") or (obj.get("customer_details") or {}).get("email")
        cust = obj.get("customer")
        sub = obj.get("subscription")
        await _upsert_pro(email or "", cust, sub, "active", None)
    elif etype in ("customer.subscription.updated", "customer.subscription.created"):
        cust = obj.get("customer")
        sub_id = obj.get("id")
        period_end = obj.get("current_period_end")
        status = obj.get("status")
        # Look up email via the existing row.
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT email FROM api_keys WHERE stripe_customer_id = $1 LIMIT 1", cust
            )
        if row and row["email"]:
            await _upsert_pro(row["email"], cust, sub_id, status or "active", period_end)
    elif etype == "customer.subscription.deleted":
        sub_id = obj.get("id")
        if sub_id:
            await _mark_cancelled(sub_id)

    return {"received": True}


# -----------------------------------------------------------------------
# Email lookup — /billing page uses this
# -----------------------------------------------------------------------


class StatusOut(BaseModel):
    tier: str
    api_key_prefix: str | None
    subscription_status: str | None
    current_period_end: datetime | None
    grandfather_until: datetime | None


@router.get("/status", response_model=StatusOut)
async def billing_status(
    request: Request,
    email: str,
) -> StatusOut:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT tier, key_prefix, subscription_status, current_period_end,
                   grandfather_until
            FROM api_keys
            WHERE email = $1 AND revoked_at IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            email,
        )
    if not row:
        raise HTTPException(404, "no subscription on this email")
    return StatusOut(
        tier=row["tier"],
        api_key_prefix=row["key_prefix"],
        subscription_status=row["subscription_status"],
        current_period_end=row["current_period_end"],
        grandfather_until=row["grandfather_until"],
    )


class CancelBody(BaseModel):
    email: EmailStr


@router.post("/cancel")
async def cancel_subscription(request: Request, body: CancelBody) -> dict:
    """Cancel at period end — we call Stripe to flip cancel_at_period_end."""
    if not _stripe_enabled():
        raise HTTPException(503, "billing disabled")
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT stripe_subscription_id FROM api_keys
            WHERE email = $1 AND revoked_at IS NULL
              AND stripe_subscription_id IS NOT NULL
            ORDER BY id DESC LIMIT 1
            """,
            str(body.email),
        )
    if not row or not row["stripe_subscription_id"]:
        raise HTTPException(404, "no active subscription on this email")
    sub_id = row["stripe_subscription_id"]
    try:
        _stripe_post(
            f"subscriptions/{sub_id}",
            {"cancel_at_period_end": "true"},
        )
    except Exception as e:
        raise HTTPException(502, f"stripe error: {type(e).__name__}: {e}")
    # Webhook will stamp status='canceled' on period_end; meanwhile mark locally.
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE api_keys SET subscription_status = 'canceling' "
            "WHERE stripe_subscription_id = $1",
            sub_id,
        )
    return {"ok": True}
