"""GET /api/admin/status — operational visibility.

Solo app, no auth. Exposes everything useful for debugging without SSH:
API-Football quota usage, per-league match / prediction counts, live match
count, and the latest timestamps on predictions / match_odds / live rows
so you can tell at a glance whether the weekly cron or live timer stalled.
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.leagues import LEAGUES

router = APIRouter(prefix="/api/admin", tags=["admin"])


class QuotaOut(BaseModel):
    used_today: int | None
    limit_day: int | None
    minute_used: int | None = None
    minute_limit: int | None = None
    fetched_at: datetime


class LeagueCounts(BaseModel):
    slug: str
    short: str
    emoji: str
    matches_total: int
    matches_final: int
    matches_scheduled: int
    matches_live: int
    predictions_total: int


class IngestTimestamps(BaseModel):
    last_prediction: datetime | None
    last_odds_capture: datetime | None
    last_live_update: datetime | None
    last_player_stats: datetime | None


class ErrorEvent(BaseModel):
    ts: float
    path: str
    error: str


class AdminStatus(BaseModel):
    quota: QuotaOut | None
    ingest: IngestTimestamps
    leagues: list[LeagueCounts]
    recent_errors_15m: int
    last_errors: list[ErrorEvent]


def _fetch_quota() -> QuotaOut | None:
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        return None
    req = urllib.request.Request(
        "https://v3.football.api-sports.io/status",
        headers={"x-apisports-key": api_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read())
    except Exception:
        return None
    requests_info = (body.get("response") or {}).get("requests") or {}
    # API-Football's status endpoint is oddly shaped — "current" is today's
    # usage count, "limit_day" is the plan ceiling.
    return QuotaOut(
        used_today=requests_info.get("current"),
        limit_day=requests_info.get("limit_day"),
        fetched_at=datetime.utcnow(),
    )


@router.get("/status", response_model=AdminStatus)
async def admin_status(request: Request) -> AdminStatus:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        ts_row = await conn.fetchrow(
            """
            SELECT
                (SELECT MAX(created_at) FROM predictions)                 AS last_prediction,
                (SELECT MAX(captured_at) FROM match_odds)                 AS last_odds_capture,
                (SELECT MAX(live_updated_at) FROM matches)                AS last_live_update,
                (SELECT MAX(updated_at) FROM player_season_stats)         AS last_player_stats
            """
        )
        league_rows = await conn.fetch(
            """
            SELECT
                league_code,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE status = 'final')      AS finalc,
                COUNT(*) FILTER (WHERE status = 'scheduled')  AS scheduledc,
                COUNT(*) FILTER (WHERE status = 'live')       AS livec
            FROM matches
            GROUP BY league_code
            """
        )
        pred_counts = await conn.fetch(
            """
            SELECT m.league_code, COUNT(*) AS preds
            FROM predictions p
            JOIN matches m ON m.id = p.match_id
            GROUP BY m.league_code
            """
        )

    by_code = {r["league_code"]: r for r in league_rows}
    preds_by_code = {r["league_code"]: int(r["preds"]) for r in pred_counts}

    leagues_out: list[LeagueCounts] = []
    for lg in LEAGUES:
        r = by_code.get(lg.code)
        leagues_out.append(
            LeagueCounts(
                slug=lg.slug,
                short=lg.short,
                emoji=lg.emoji,
                matches_total=int(r["total"]) if r else 0,
                matches_final=int(r["finalc"]) if r else 0,
                matches_scheduled=int(r["scheduledc"]) if r else 0,
                matches_live=int(r["livec"]) if r else 0,
                predictions_total=preds_by_code.get(lg.code, 0),
            )
        )

    from app.core.error_log import recent_errors

    errs = recent_errors(window_sec=900)
    return AdminStatus(
        quota=_fetch_quota(),
        ingest=IngestTimestamps(
            last_prediction=ts_row["last_prediction"],
            last_odds_capture=ts_row["last_odds_capture"],
            last_live_update=ts_row["last_live_update"],
            last_player_stats=ts_row["last_player_stats"],
        ),
        leagues=leagues_out,
        recent_errors_15m=len(errs),
        last_errors=[ErrorEvent(**e) for e in errs[-10:]],
    )
