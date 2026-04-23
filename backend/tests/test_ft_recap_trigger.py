"""Post-match recap must fire at FT, not 9h later in the daily cron."""
from __future__ import annotations

import asyncio

import pytest


class _FakePool:
    """Minimal async context-manager stand-in. `_generate_recaps_on_ft`
    delegates all DB work to the passed selector; the pool itself is
    opaque so we hand the callees the same sentinel."""

    def __repr__(self) -> str:
        return "_FakePool"


def test_dispatcher_calls_generate_for_each_match_up_to_limit():
    from scripts.ingest_live_scores import _generate_recaps_on_ft

    pool = _FakePool()
    match_ids = [101, 102, 103, 104, 105]

    async def select(p):
        assert p is pool
        return list(match_ids)

    called_with: list[int] = []

    async def gen(p, mid):
        assert p is pool
        called_with.append(mid)
        return "ok"

    count = asyncio.run(
        _generate_recaps_on_ft(pool, selector=select, generator=gen, limit=3)
    )
    assert called_with == [101, 102, 103]
    assert count == 3


def test_dispatcher_skips_matches_where_generator_returns_none():
    """Generator returns None on LLM failure; we must not count it."""
    from scripts.ingest_live_scores import _generate_recaps_on_ft

    pool = _FakePool()

    async def select(p):
        return [201, 202]

    async def gen(p, mid):
        return None if mid == 201 else "prose"

    count = asyncio.run(
        _generate_recaps_on_ft(pool, selector=select, generator=gen, limit=10)
    )
    assert count == 1


def test_dispatcher_returns_zero_when_nothing_to_generate():
    from scripts.ingest_live_scores import _generate_recaps_on_ft

    pool = _FakePool()

    async def select(p):
        return []

    async def gen(p, mid):  # pragma: no cover — should never be called
        pytest.fail("generator should not run when selector returns empty")

    count = asyncio.run(
        _generate_recaps_on_ft(pool, selector=select, generator=gen, limit=10)
    )
    assert count == 0
