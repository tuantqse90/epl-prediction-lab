"""GET /api/ops/status — public health snapshot for the /ops page.

Reuses the watchdog checkers so the UI and the Telegram alerts agree on
what "broken" means. Read-only — does not write to ops_alerts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel

from scripts.ops_watchdog import (
    _check_fixture_drift,
    _check_missing_recap,
    _check_stale_live,
    _check_stale_predictions,
    _load_candidates,
)


router = APIRouter(prefix="/api/ops", tags=["ops"])


class CheckerStatus(BaseModel):
    name: str
    ok: bool
    count: int
    alerts: list[dict]


class OpsStatus(BaseModel):
    checked_at: datetime
    overall_ok: bool
    checkers: list[CheckerStatus]


@router.get("/status", response_model=OpsStatus)
async def ops_status(request: Request) -> OpsStatus:
    pool = request.app.state.pool
    fixture_rows, prediction_rows = await _load_candidates(pool)
    now = datetime.now(timezone.utc)

    results = [
        ("fixture_drift", _check_fixture_drift(fixture_rows, now=now)),
        ("stale_live", _check_stale_live(fixture_rows, now=now)),
        ("missing_recap", _check_missing_recap(fixture_rows, now=now)),
        ("stale_predictions", _check_stale_predictions(prediction_rows, now=now)),
    ]

    checkers = [
        CheckerStatus(
            name=name,
            ok=len(alerts) == 0,
            count=len(alerts),
            alerts=alerts[:20],
        )
        for name, alerts in results
    ]
    return OpsStatus(
        checked_at=now,
        overall_ok=all(c.ok for c in checkers),
        checkers=checkers,
    )
