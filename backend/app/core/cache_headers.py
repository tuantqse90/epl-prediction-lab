"""Set `Cache-Control` headers on read-only GET endpoints so Cloudflare
can cache at the edge. Saves ~80% of cold origin hits for public routes
(list, stats, stories) — numbers change slowly.

Rules (first match wins). Path is request.url.path; method must be GET.

- Live / personal / write paths → always no-store (never cached)
- Stable lookups (story body, historical stats) → 1 h
- Digest-style aggregations (stats, tables, stories) → 5 min
- Live-ish lists (matches, live odds, injuries) → 1 min
- Everything else → pass-through (no header added; respects whatever
  the route set)

Origin-side (`s-maxage`) decouples the edge TTL from the browser's
`max-age`. We keep `max-age=0` so the user's browser always revalidates
— only Cloudflare + Caddy hold the copy.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

from starlette.types import ASGIApp, Receive, Scope, Send


# Always no-store — anything user-scoped or write-capable.
_NEVER_CACHE = [
    re.compile(r"^/api/health"),
    re.compile(r"^/api/admin/"),
    re.compile(r"^/api/keys"),
    re.compile(r"^/api/billing/"),
    re.compile(r"^/api/push/"),
    re.compile(r"^/api/chat"),
    re.compile(r"^/api/sync/"),
    re.compile(r"^/api/email/"),
    re.compile(r"^/api/tipster-signup"),
    re.compile(r"^/api/telegram/"),
    re.compile(r"^/api/discord/"),
    re.compile(r"^/api/metrics/"),
    re.compile(r"^/api/ops/"),
    re.compile(r"^/api/internal-tools/"),
    # Live data — fresh every request.
    re.compile(r"^/api/matches/\d+/live"),
    re.compile(r"^/api/matches/\d+/halftime"),
    re.compile(r"^/api/matches/\d+/ci"),
]

# Stable once written — story body, historical season data, FAQ-like.
_LONG = [
    re.compile(r"^/api/matches/\d+/story$"),
    re.compile(r"^/api/stats/history"),
    re.compile(r"^/api/stats/since-upgrade"),
]

# Digest-style aggregations — recompute every few min at most.
_MEDIUM = [
    re.compile(r"^/api/stats/"),
    re.compile(r"^/api/table"),
    re.compile(r"^/api/title-race"),
    re.compile(r"^/api/top-scorer-race"),
    re.compile(r"^/api/power-rankings"),
    re.compile(r"^/api/bracket"),
    re.compile(r"^/api/calibration"),
    re.compile(r"^/api/equity-curve"),
    re.compile(r"^/api/clv-by-market"),
]

# Fresh-ish but still safely cached for ~60s.
_SHORT = [
    re.compile(r"^/api/matches$"),
    re.compile(r"^/api/matches/\d+$"),
    re.compile(r"^/api/matches/\d+/h2h"),
    re.compile(r"^/api/matches/\d+/injuries"),
    re.compile(r"^/api/matches/\d+/lineups"),
    re.compile(r"^/api/matches/\d+/scorers"),
    re.compile(r"^/api/matches/\d+/markets"),
    re.compile(r"^/api/matches/\d+/markets-edge"),
    re.compile(r"^/api/matches/\d+/referee"),
    re.compile(r"^/api/matches/\d+/injury-impact"),
    re.compile(r"^/api/matches/\d+/fatigue"),
    re.compile(r"^/api/matches/\d+/lineup-strength"),
    re.compile(r"^/api/matches/\d+/weather"),
    re.compile(r"^/api/players/"),
    re.compile(r"^/api/teams/"),
    re.compile(r"^/api/news"),
    re.compile(r"^/api/fpl/"),
    re.compile(r"^/api/arbitrage"),
    re.compile(r"^/api/middles"),
    re.compile(r"^/api/line-movement"),
    re.compile(r"^/api/live-edge"),
    re.compile(r"^/api/manager/"),
    re.compile(r"^/api/by-team/"),
    re.compile(r"^/api/blog/"),
    re.compile(r"^/api/tipsters"),
    re.compile(r"^/api/search"),
    re.compile(r"^/api/compare"),
    re.compile(r"^/api/match-of-week"),
    re.compile(r"^/api/predictions/"),
    re.compile(r"^/api/player-analytics"),
]


def _bucket(path: str) -> str | None:
    if any(rx.match(path) for rx in _NEVER_CACHE):
        return "no-store"
    if any(rx.match(path) for rx in _LONG):
        # Stable — 1 h origin, 10 min stale-while-revalidate.
        return "public, max-age=0, s-maxage=3600, stale-while-revalidate=600"
    if any(rx.match(path) for rx in _MEDIUM):
        return "public, max-age=0, s-maxage=300, stale-while-revalidate=600"
    if any(rx.match(path) for rx in _SHORT):
        return "public, max-age=0, s-maxage=60, stale-while-revalidate=300"
    return None


class EdgeCacheMiddleware:
    """ASGI middleware — mutates `Cache-Control` on outgoing GET responses.
    Skips if the route already set `Cache-Control` explicitly (some routes
    want no-store for personal data even on matching paths).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") != "GET":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        policy = _bucket(path)
        if policy is None:
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                has_cc = any(h[0].lower() == b"cache-control" for h in headers)
                status = message.get("status", 200)
                # Only stamp 200/304; error responses shouldn't cache.
                if not has_cc and status in (200, 304):
                    headers.append((b"cache-control", policy.encode("latin-1")))
                    # Cloudflare-specific — respects s-maxage via CDN-Cache-Control
                    # if the browser disrespects our upstream max-age=0.
                    if policy != "no-store":
                        headers.append((b"cdn-cache-control", policy.encode("latin-1")))
                    message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
