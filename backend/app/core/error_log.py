"""Structured error logging middleware.

Every uncaught exception on a request path gets emitted as a single JSON
line to stderr so the Docker log driver (and anything downstream —
`docker compose logs`, Loki, ELK) can index it cleanly. We also bump a
counter that the ops-alert cron can read to detect error-rate spikes.

Chosen over Sentry-self-host to keep the dep surface minimal — stderr +
dict counter is enough for a solo app at this scale. Upgrade path to
Sentry is a single handler swap if traffic grows.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
import uuid
from collections import deque
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


# Last 500 error events — window used by ops_alert.py to decide severity.
# Ring buffer of (timestamp, path, error_class). Module-level is fine —
# single-process per container (uvicorn --workers 1 in our compose).
_RECENT: deque[tuple[float, str, str]] = deque(maxlen=500)


def recent_errors(window_sec: int = 900) -> list[dict[str, Any]]:
    """Errors in the last `window_sec` seconds. For the ops dashboard."""
    now = time.time()
    return [
        {"ts": ts, "path": p, "error": e}
        for ts, p, e in _RECENT
        if now - ts <= window_sec
    ]


class ErrorLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex[:12]
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            tb = traceback.format_exc()
            payload = {
                "lvl": "error",
                "ts": time.time(),
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query or ""),
                "error": type(exc).__name__,
                "message": str(exc),
                "traceback": tb,
            }
            # Single-line JSON so downstream log processors don't split it.
            print(json.dumps(payload), file=sys.stderr, flush=True)
            _RECENT.append((time.time(), request.url.path, type(exc).__name__))
            # Re-raise so FastAPI's default handler still returns a 500 +
            # the client sees something sane.
            raise
