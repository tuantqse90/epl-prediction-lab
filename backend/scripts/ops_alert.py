"""Ops health monitor → Telegram DM.

Fires when any of:
  - API-Football quota used > 85% of the daily cap
  - live_updated_at on any currently-live match older than 5 minutes
    (suggests the 10-s timer stalled)
  - last prediction insert older than 25 hours (daily cron didn't run)

Idempotent: rate-limited with a crude per-alert-kind cooldown via the
filesystem at /tmp/ops-alert-<kind>.ts so rerunning the script every 15m
doesn't spam the channel.

Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, API_FOOTBALL_KEY

Usage:
    python scripts/ops_alert.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings


COOLDOWN_SEC = 3600  # don't re-alert the same kind within 1 hour


def _cooldown_path(kind: str) -> Path:
    return Path(f"/tmp/football-predict-alert-{kind}.ts")


def _should_fire(kind: str) -> bool:
    p = _cooldown_path(kind)
    if not p.exists():
        return True
    try:
        ts = float(p.read_text().strip())
    except (ValueError, OSError):
        return True
    return (time.time() - ts) > COOLDOWN_SEC


def _mark_fired(kind: str) -> None:
    try:
        _cooldown_path(kind).write_text(str(time.time()))
    except OSError:
        pass


def _telegram(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=10):
        pass


def _check_quota() -> tuple[str, str] | None:
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        return None
    req = urllib.request.Request(
        "https://v3.football.api-sports.io/status",
        headers={"x-apisports-key": key},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read())
    except Exception:
        return None
    info = (body.get("response") or {}).get("requests") or {}
    used = info.get("current")
    limit = info.get("limit_day")
    if used is None or not limit:
        return None
    if used / limit >= 0.85:
        return (
            "quota",
            f"⚠️ *API-Football quota* · used {used} / {limit} "
            f"({round(100 * used / limit)}%) today",
        )
    return None


async def _check_live_staleness(pool: asyncpg.Pool) -> tuple[str, str] | None:
    row = await pool.fetchrow(
        """
        SELECT COUNT(*) AS n,
               MAX(NOW() - live_updated_at) AS worst
        FROM matches
        WHERE status = 'live'
          AND live_updated_at < NOW() - INTERVAL '5 minutes'
        """,
    )
    if not row or not row["n"]:
        return None
    return (
        "live-stale",
        f"⏱ *Live polling stalled* · {row['n']} live match(es), "
        f"oldest update {row['worst']} ago",
    )


async def _check_daily_predict(pool: asyncpg.Pool) -> tuple[str, str] | None:
    row = await pool.fetchrow(
        "SELECT MAX(created_at) AS ts FROM predictions"
    )
    if not row or row["ts"] is None:
        return None
    # Compare in SQL timezone-aware; asyncpg returns datetime with tz info
    stale = await pool.fetchval(
        "SELECT MAX(created_at) < NOW() - INTERVAL '25 hours' FROM predictions"
    )
    if not stale:
        return None
    return (
        "predict-stale",
        f"📉 *Daily predict cron missed* · last prediction {row['ts'].isoformat()}",
    )


async def run() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[ops-alert] no telegram token/chat id; skipping")
        return

    alerts: list[tuple[str, str]] = []
    q = _check_quota()
    if q:
        alerts.append(q)

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        ls = await _check_live_staleness(pool)
        if ls:
            alerts.append(ls)
        pr = await _check_daily_predict(pool)
        if pr:
            alerts.append(pr)
    finally:
        await pool.close()

    for kind, text in alerts:
        if _should_fire(kind):
            try:
                _telegram(token, chat_id, text)
                _mark_fired(kind)
                print(f"[ops-alert] fired: {kind}")
            except Exception as e:
                print(f"[ops-alert] send failed ({kind}): {e}")
        else:
            print(f"[ops-alert] cooldown active: {kind}")

    if not alerts:
        print("[ops-alert] all clear")


if __name__ == "__main__":
    asyncio.run(run())
