"""asyncpg connection pool + FastAPI lifespan helpers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg
from fastapi import FastAPI

from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open one asyncpg pool for the API's lifetime; expose it on `app.state.pool`."""
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    app.state.pool = pool
    try:
        yield
    finally:
        await pool.close()


async def get_pool(app: FastAPI) -> asyncpg.Pool:
    return app.state.pool
