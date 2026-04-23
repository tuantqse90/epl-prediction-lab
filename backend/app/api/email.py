"""Email digest — opt-in weekly newsletter.

Subscribe flow:
    1. POST /api/email/subscribe {email, lang?, league?}
    2. We send a confirm email with token link.
    3. GET /api/email/confirm?token=... marks confirmed_at.
    4. Weekly cron posts digest to every `confirmed_at IS NOT NULL` row.
    5. GET /api/email/unsubscribe?token=... marks unsubscribed_at (+ fall off list).

Transport: Resend HTTP API (RESEND_API_KEY). If unset, log only.
"""

from __future__ import annotations

import json
import os
import secrets
import urllib.request
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr


router = APIRouter(prefix="/api/email", tags=["email"])


class SubscribeBody(BaseModel):
    email: EmailStr
    lang: Literal["en", "vi", "th", "zh", "ko"] = "en"
    league: str | None = None   # league_code or None = all top-5


class Ack(BaseModel):
    ok: bool


SITE = "https://predictor.nullshift.sh"


def _send_email(to: str, subject: str, html: str) -> tuple[bool, str | None]:
    """POST to Resend's /emails endpoint. Falls back to no-op when unset."""
    api_key = os.environ.get("RESEND_API_KEY")
    from_addr = os.environ.get("EMAIL_FROM", "Prediction Lab <onboarding@resend.dev>")
    if not api_key:
        print(f"[email] no RESEND_API_KEY; would send to {to}: {subject}")
        return (False, "no RESEND_API_KEY")
    body = json.dumps({
        "from": from_addr,
        "to": [to],
        "subject": subject,
        "html": html,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=body, method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return (resp.status in (200, 201), None)
    except Exception as e:
        return (False, f"{type(e).__name__}: {e}")


@router.post("/subscribe", response_model=Ack)
async def subscribe(body: SubscribeBody, request: Request) -> Ack:
    token = secrets.token_urlsafe(24)
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO email_subscriptions (email, token, lang, league_filter)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (email) DO UPDATE SET
              token = EXCLUDED.token,
              lang = EXCLUDED.lang,
              league_filter = EXCLUDED.league_filter,
              confirmed_at = NULL,
              unsubscribed_at = NULL
            """,
            str(body.email), token, body.lang, body.league,
        )
    confirm_url = f"{SITE}/api/email/confirm?token={token}"
    html = (
        f"<p>Welcome to the Prediction Lab weekly digest.</p>"
        f'<p><a href="{confirm_url}">Click to confirm your subscription →</a></p>'
        f"<p>Ignore this email if you didn't sign up.</p>"
    )
    ok, err = _send_email(str(body.email), "Confirm your Prediction Lab subscription", html)
    if not ok and err and err != "no RESEND_API_KEY":
        raise HTTPException(status_code=502, detail=err)
    return Ack(ok=True)


@router.get("/confirm", response_class=HTMLResponse)
async def confirm(token: str, request: Request) -> HTMLResponse:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE email_subscriptions
            SET confirmed_at = NOW(), unsubscribed_at = NULL
            WHERE token = $1 AND unsubscribed_at IS NULL
            RETURNING email
            """,
            token,
        )
    if not row:
        return HTMLResponse("<h1>Invalid or expired link.</h1>", status_code=400)
    return HTMLResponse(
        f"<h1>✓ Subscribed</h1>"
        f"<p>{row['email']} will get the Monday digest.</p>"
        f'<p><a href="{SITE}">← back to the site</a></p>'
    )


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(token: str, request: Request) -> HTMLResponse:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE email_subscriptions SET unsubscribed_at = NOW() WHERE token = $1",
            token,
        )
    return HTMLResponse("<h1>Unsubscribed.</h1><p>You'll stop getting the digest.</p>")


# ---------------------------------------------------------------------------
# Digest composer — reused by the Mon cron
# ---------------------------------------------------------------------------


def render_digest_html(*, top_picks: list[dict], last_week: dict, site: str = SITE) -> str:
    """Pure function — pass pre-fetched rows, produce HTML.

    top_picks[i] = {home, away, pick, conf, odds, edge_pp, league_code, kickoff_time}
    last_week    = {scored, correct, accuracy, pnl, roi_pct}
    """
    def _pct(x: float) -> str:
        return f"{x * 100:.1f}%"

    lw = last_week
    pick_rows = "".join(
        f"<tr>"
        f"<td style='padding:6px 10px'>{p['league_code']}</td>"
        f"<td style='padding:6px 10px'><b>{p['home']}</b> vs <b>{p['away']}</b></td>"
        f"<td style='padding:6px 10px'>{p['pick']} · {int(p['conf']*100)}%</td>"
        f"<td style='padding:6px 10px; text-align:right'>@ {p['odds']:.2f}</td>"
        f"<td style='padding:6px 10px; text-align:right; color:#2ca02c'>+{p['edge_pp']:.1f}%</td>"
        f"</tr>"
        for p in top_picks[:10]
    )
    return f"""
<!doctype html><html><body style="font-family:system-ui,Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#0a0a0a;color:#e8e8e8">
  <h1 style="color:#E0FF32;margin-bottom:4px">Prediction Lab — weekly digest</h1>
  <p style="color:#a0a0a0;margin-top:0">Monday {datetime.now(timezone.utc).strftime('%Y-%m-%d')}</p>

  <h2>Last week</h2>
  <table style="width:100%;border-collapse:collapse">
    <tr>
      <td>Matches graded: {lw.get('scored', 0)}</td>
      <td>Correct: {lw.get('correct', 0)} · {_pct(lw.get('accuracy', 0))}</td>
    </tr>
    <tr>
      <td colspan="2">P&amp;L (flat 1u @ edge ≥ 5%): {lw.get('pnl', 0):+.2f}u · ROI {lw.get('roi_pct', 0):+.1f}%</td>
    </tr>
  </table>

  <h2>This week's top edges</h2>
  <table style="width:100%;border-collapse:collapse;background:#141414;border-radius:6px">
    <thead style="background:#1c1c1c"><tr>
      <th style="padding:8px;text-align:left">League</th>
      <th style="padding:8px;text-align:left">Fixture</th>
      <th style="padding:8px;text-align:left">Pick</th>
      <th style="padding:8px;text-align:right">Odds</th>
      <th style="padding:8px;text-align:right">Edge</th>
    </tr></thead>
    <tbody>
      {pick_rows or '<tr><td colspan=5 style=padding:10px>No edges ≥ 5% this week.</td></tr>'}
    </tbody>
  </table>

  <p style="margin-top:30px"><a href="{site}" style="color:#E0FF32">Open the site →</a></p>
  <hr style="border-color:#222;margin-top:40px"/>
  <p style="color:#777;font-size:12px">
    Forecasting is entertainment-grade. Do your own research before staking.
    · <a href="{site}/api/email/unsubscribe?token={{UNSUB_TOKEN}}" style="color:#777">Unsubscribe</a>
  </p>
</body></html>"""
