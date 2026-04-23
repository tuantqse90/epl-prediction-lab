"""Ops watchdog — catches silent failures the live ingest doesn't notify about.

Runs every 5 min via systemd. Emits one Telegram message per tick when any
checker is non-empty. Idempotent via ops_alerts table so the same issue
doesn't re-spam.

Checkers (each a pure function over rows, testable in isolation):
  1. fixture_drift      — scheduled matches past kickoff by >2h
  2. stale_live         — status=live with no live_updated_at in 5 min
  3. missing_recap      — status=final + recap NULL + kickoff >12h ago
  4. low_quota          — API-Football remaining < 10k
  5. stale_predictions  — scheduled in next 48h with no predictions row

Env:
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (optional — without them we log
    to stdout and only update the DB dedup table)

Usage:
    python scripts/ops_watchdog.py
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import asyncpg


def _records_to_ns(rows) -> list:
    """asyncpg.Record only supports subscript access; pure checkers use
    attribute access so tests can pass SimpleNamespace rows. Normalise."""
    return [SimpleNamespace(**dict(r)) for r in rows]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings


# Tuned to swallow one-off hiccups without being permissive about real drift.
STALE_LIVE_MINUTES = 5
FIXTURE_DRIFT_HOURS = 2
MISSING_RECAP_HOURS = 12
STALE_PREDICTION_WINDOW_HOURS = 48
LOW_QUOTA_THRESHOLD = 10_000
# How long to suppress a re-alert with the same content.
ALERT_COOLDOWN_HOURS = 6


# ---------------------------------------------------------------------------
# Pure checkers
# ---------------------------------------------------------------------------


def _check_fixture_drift(rows, *, now: datetime) -> list[dict]:
    alerts = []
    for r in rows:
        if r.status != "scheduled":
            continue
        age = now - r.kickoff_time
        if age > timedelta(hours=FIXTURE_DRIFT_HOURS):
            alerts.append({
                "match_id": r.id,
                "message": (
                    f"{r.home_name} vs {r.away_name} ({r.league_code}) — "
                    f"scheduled but kickoff was {int(age.total_seconds() // 3600)}h ago"
                ),
            })
    return alerts


def _check_stale_live(rows, *, now: datetime, threshold_minutes: int = STALE_LIVE_MINUTES) -> list[dict]:
    alerts = []
    cutoff = now - timedelta(minutes=threshold_minutes)
    for r in rows:
        if r.status != "live":
            continue
        lu = r.live_updated_at
        if lu is None or lu < cutoff:
            alerts.append({
                "match_id": r.id,
                "message": f"{r.home_name} vs {r.away_name} — live feed stale",
            })
    return alerts


def _check_missing_recap(rows, *, now: datetime) -> list[dict]:
    alerts = []
    cutoff = now - timedelta(hours=MISSING_RECAP_HOURS)
    for r in rows:
        if r.status != "final" or r.recap:
            continue
        if r.kickoff_time < cutoff:
            alerts.append({
                "match_id": r.id,
                "message": f"{r.home_name} vs {r.away_name} — final with no recap",
            })
    return alerts


def _check_low_quota(*, remaining, threshold: int = LOW_QUOTA_THRESHOLD) -> list[dict]:
    if remaining is None:
        return []
    if remaining < threshold:
        return [{"message": f"API-Football quota remaining: {remaining} (threshold {threshold})"}]
    return []


def _check_stale_predictions(rows, *, now: datetime) -> list[dict]:
    alerts = []
    horizon = now + timedelta(hours=STALE_PREDICTION_WINDOW_HOURS)
    for r in rows:
        if r.kickoff_time > horizon:
            continue
        if r.kickoff_time < now:
            continue
        if not r.has_prediction:
            alerts.append({
                "match_id": r.id,
                "message": f"{r.home_name} vs {r.away_name} — no prediction for upcoming match",
            })
    return alerts


def _alert_hash(checker_name: str, alerts: list[dict]) -> str:
    """Stable hash over sorted alert content — two ticks with the same
    offenders produce the same hash so the DB-backed dedup suppresses
    re-posting."""
    canon = sorted(
        [(a.get("match_id"), a.get("message", "")) for a in alerts]
    )
    payload = json.dumps([checker_name, canon], sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# DB queries (thin wrappers — pure logic is in the checkers above)
# ---------------------------------------------------------------------------


async def _load_candidates(pool: asyncpg.Pool):
    """Pull every row any checker could care about in a handful of queries."""
    async with pool.acquire() as conn:
        fixture_rows = await conn.fetch(
            """
            SELECT m.id, m.kickoff_time, m.status, m.live_updated_at,
                   m.home_goals, m.away_goals, m.recap, m.league_code,
                   ht.name AS home_name, at.name AS away_name
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.kickoff_time BETWEEN NOW() - INTERVAL '48 hours'
                                     AND NOW() + INTERVAL '7 days'
            """,
        )
        prediction_rows = await conn.fetch(
            """
            SELECT m.id, m.kickoff_time,
                   ht.name AS home_name, at.name AS away_name,
                   EXISTS (SELECT 1 FROM predictions p WHERE p.match_id = m.id) AS has_prediction
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.status = 'scheduled'
              AND m.kickoff_time BETWEEN NOW() AND NOW() + INTERVAL '48 hours'
            """,
        )
    return _records_to_ns(fixture_rows), _records_to_ns(prediction_rows)


async def _ensure_alert_table(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ops_alerts (
                alert_hash TEXT PRIMARY KEY,
                checker_name TEXT NOT NULL,
                payload JSONB NOT NULL,
                last_sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
        )


async def _should_send(pool: asyncpg.Pool, alert_hash: str) -> bool:
    """True if we haven't posted this exact hash within ALERT_COOLDOWN_HOURS."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT last_sent_at FROM ops_alerts WHERE alert_hash = $1",
            alert_hash,
        )
    if row is None:
        return True
    age = datetime.now(timezone.utc) - row["last_sent_at"]
    return age > timedelta(hours=ALERT_COOLDOWN_HOURS)


async def _record_sent(pool: asyncpg.Pool, alert_hash: str, checker_name: str, alerts: list[dict]) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO ops_alerts (alert_hash, checker_name, payload, last_sent_at)
            VALUES ($1, $2, $3::jsonb, NOW())
            ON CONFLICT (alert_hash) DO UPDATE SET last_sent_at = EXCLUDED.last_sent_at
            """,
            alert_hash, checker_name, json.dumps(alerts),
        )


# ---------------------------------------------------------------------------
# Telegram sink — fire-and-forget
# ---------------------------------------------------------------------------


def _post_telegram(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[watchdog] telegram post failed: {type(e).__name__}: {e}")
        return False


def _format_message(checker_name: str, alerts: list[dict]) -> str:
    title = {
        "fixture_drift": "🛑 Fixture drift",
        "stale_live": "⚠️ Live feed stale",
        "missing_recap": "📝 Missing recap",
        "low_quota": "📉 Low API-Football quota",
        "stale_predictions": "🔮 Missing predictions",
    }.get(checker_name, checker_name)
    lines = [f"*{title}* ({len(alerts)})"]
    for a in alerts[:10]:
        lines.append(f"• {a['message']}")
    if len(alerts) > 10:
        lines.append(f"… +{len(alerts) - 10} more")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Quota reading — pings /status once per tick; cheap (1 quota / 5 min = 288/day)
# ---------------------------------------------------------------------------


def _fetch_quota_remaining(api_key: str) -> int | None:
    url = "https://v3.football.api-sports.io/status"
    req = urllib.request.Request(url, headers={"x-apisports-key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
    except Exception:
        return None
    resp_body = body.get("response") or {}
    req_info = resp_body.get("requests") or {}
    limit = req_info.get("limit_day")
    current = req_info.get("current")
    if limit is None or current is None:
        return None
    return int(limit) - int(current)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def run() -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        await _ensure_alert_table(pool)
        fixture_rows, prediction_rows = await _load_candidates(pool)
        now = datetime.now(timezone.utc)

        results: list[tuple[str, list[dict]]] = [
            ("fixture_drift", _check_fixture_drift(fixture_rows, now=now)),
            ("stale_live", _check_stale_live(fixture_rows, now=now)),
            ("missing_recap", _check_missing_recap(fixture_rows, now=now)),
            ("stale_predictions", _check_stale_predictions(prediction_rows, now=now)),
        ]

        api_key = os.environ.get("API_FOOTBALL_KEY")
        if api_key:
            remaining = _fetch_quota_remaining(api_key)
            results.append(("low_quota", _check_low_quota(remaining=remaining)))

        total = 0
        for name, alerts in results:
            if not alerts:
                continue
            total += len(alerts)
            h = _alert_hash(name, alerts)
            if not await _should_send(pool, h):
                print(f"[watchdog] {name}: {len(alerts)} alerts (suppressed — within cooldown)")
                continue
            message = _format_message(name, alerts)
            posted = _post_telegram(message)
            print(f"[watchdog] {name}: {len(alerts)} alerts (telegram={'ok' if posted else 'no'})")
            print(message)
            await _record_sent(pool, h, name, alerts)

        if total == 0:
            print("[watchdog] all green")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    asyncio.run(run())


if __name__ == "__main__":
    main()
