"""Tiny in-memory TTL cache.

For read-heavy aggregation endpoints where computing the response costs
more than keeping a 5-min-stale copy costs users. Per-process, resets on
container restart. Store is unbounded by entry count — key cardinality is
tiny (≤ ~30 distinct keys in practice).

Usage:
    _CACHE = TTLCache(ttl_seconds=300)

    async def history(league_code):
        hit = _CACHE.get(("history", league_code))
        if hit is not None:
            return hit
        value = await compute(...)
        _CACHE.set(("history", league_code), value)
        return value
"""

from __future__ import annotations

import time
from typing import Any, Hashable


class TTLCache:
    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl = ttl_seconds
        self._store: dict[Hashable, tuple[float, Any]] = {}

    def get(self, key: Hashable) -> Any | None:
        hit = self._store.get(key)
        if hit is None:
            return None
        ts, value = hit
        if (time.time() - ts) > self.ttl:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: Hashable, value: Any) -> None:
        self._store[key] = (time.time(), value)

    def invalidate(self, key: Hashable | None = None) -> None:
        if key is None:
            self._store.clear()
        else:
            self._store.pop(key, None)
