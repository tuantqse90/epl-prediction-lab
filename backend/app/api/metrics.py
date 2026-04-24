"""GET /metrics — Prometheus text format.

Bare-bones gauges for what matters:
  pl_matches_live         — current live-status count
  pl_predictions_total    — prediction rows
  pl_error_events_1h      — error count last hour
  pl_page_views_1h        — page-view count last hour
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse


router = APIRouter(tags=["ops"])


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics(request: Request) -> str:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        counts = await conn.fetchrow(
            """
            SELECT
              (SELECT COUNT(*) FROM matches WHERE status = 'live')         AS matches_live,
              (SELECT COUNT(*) FROM predictions)                            AS predictions_total,
              (SELECT COUNT(*) FROM error_events WHERE ts > NOW() - INTERVAL '1 hour') AS errors_1h,
              (SELECT COUNT(*) FROM page_views   WHERE ts > NOW() - INTERVAL '1 hour') AS pv_1h,
              (SELECT COUNT(*) FROM api_keys WHERE revoked_at IS NULL)     AS api_keys_active
            """,
        )
    return "\n".join([
        "# HELP pl_matches_live Current live matches",
        "# TYPE pl_matches_live gauge",
        f"pl_matches_live {int(counts['matches_live'] or 0)}",
        "# HELP pl_predictions_total Total stored predictions",
        "# TYPE pl_predictions_total counter",
        f"pl_predictions_total {int(counts['predictions_total'] or 0)}",
        "# HELP pl_error_events_1h Request errors in the last 1h",
        "# TYPE pl_error_events_1h gauge",
        f"pl_error_events_1h {int(counts['errors_1h'] or 0)}",
        "# HELP pl_page_views_1h Page views in the last 1h",
        "# TYPE pl_page_views_1h gauge",
        f"pl_page_views_1h {int(counts['pv_1h'] or 0)}",
        "# HELP pl_api_keys_active Live API keys",
        "# TYPE pl_api_keys_active gauge",
        f"pl_api_keys_active {int(counts['api_keys_active'] or 0)}",
        "",
    ])
