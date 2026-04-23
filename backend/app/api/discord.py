"""Discord webhook management + fan-out.

Users register a Discord webhook URL (created via server settings in
Discord → "Integrations → Webhooks"). We store it, then fan out goal
pings and the daily digest as JSON POSTs.

Endpoints:
    POST /api/discord/register   {url, label?, team_slugs?, daily_digest?, goal_pings?}
    DELETE /api/discord/register?url=...
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, HttpUrl


router = APIRouter(prefix="/api/discord", tags=["discord"])


class RegisterBody(BaseModel):
    url: HttpUrl
    label: str | None = None
    team_slugs: list[str] = Field(default_factory=list)
    daily_digest: bool = True
    goal_pings: bool = True


class RegisterAck(BaseModel):
    ok: bool
    id: int | None = None


@router.post("/register", response_model=RegisterAck)
async def register(body: RegisterBody, request: Request) -> RegisterAck:
    url_str = str(body.url)
    if not url_str.startswith("https://discord.com/api/webhooks/") and not url_str.startswith(
        "https://discordapp.com/api/webhooks/"
    ):
        raise HTTPException(status_code=400, detail="must be a discord.com webhook URL")
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        new_id = await conn.fetchval(
            """
            INSERT INTO discord_webhooks (url, label, team_slugs, daily_digest, goal_pings)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (url) DO UPDATE SET
              label = EXCLUDED.label,
              team_slugs = EXCLUDED.team_slugs,
              daily_digest = EXCLUDED.daily_digest,
              goal_pings = EXCLUDED.goal_pings
            RETURNING id
            """,
            url_str, body.label, body.team_slugs, body.daily_digest, body.goal_pings,
        )
    return RegisterAck(ok=True, id=int(new_id) if new_id else None)


@router.delete("/register", response_model=RegisterAck)
async def unregister(url: str, request: Request) -> RegisterAck:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM discord_webhooks WHERE url = $1", url)
    return RegisterAck(ok=True)


# ---------------------------------------------------------------------------
# Fan-out helper — reused by live-scores + daily digest script
# ---------------------------------------------------------------------------


def _post_discord(url: str, content: str) -> tuple[bool, str | None]:
    body = json.dumps({
        "content": content[:1900],  # Discord limit 2000, leave headroom
        "allowed_mentions": {"parse": []},
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return (resp.status in (200, 204), None)
    except Exception as e:
        return (False, f"{type(e).__name__}: {e}")


async def fan_out_to_discord(
    pool, *, team_slugs: list[str] | None = None, content: str, kind: str = "goal",
) -> int:
    """Post `content` to registered Discord webhooks matching the scope.

    `kind='goal'` — respects `goal_pings=true` + team_slugs overlap (empty
                   team_slugs means "all").
    `kind='digest'` — respects `daily_digest=true`.
    """
    if kind == "goal":
        sql = """
            SELECT id, url, team_slugs FROM discord_webhooks
            WHERE goal_pings = TRUE
              AND (
                cardinality(team_slugs) = 0
                OR team_slugs && $1::text[]
              )
            """
        args = (team_slugs or [],)
    elif kind == "digest":
        sql = "SELECT id, url, team_slugs FROM discord_webhooks WHERE daily_digest = TRUE"
        args = ()
    else:
        return 0

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *args)

    posted = 0
    now = datetime.now(timezone.utc)
    for r in rows:
        ok, err = _post_discord(r["url"], content)
        async with pool.acquire() as conn:
            if ok:
                await conn.execute(
                    "UPDATE discord_webhooks SET last_ok_at = $1, last_error = NULL WHERE id = $2",
                    now, r["id"],
                )
                posted += 1
            else:
                await conn.execute(
                    "UPDATE discord_webhooks SET last_error = $1 WHERE id = $2",
                    err, r["id"],
                )
    return posted
