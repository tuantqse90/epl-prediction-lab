"""FastAPI entry point. Boots the asyncpg pool and mounts the API routers."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin as admin_router
from app.api import arbitrage as arbitrage_router
from app.api import blog as blog_router
from app.api import by_team as by_team_router
from app.api import calibration as calibration_router
from app.api import equity_curve as equity_curve_router
from app.api import line_movement as line_movement_router
from app.api import manager as manager_router
from app.api import chat as chat_router
from app.api import compare as compare_router
from app.api import discord as discord_router
from app.api import email as email_router
from app.api import fpl as fpl_router
from app.api import matches as matches_router
from app.api import news as news_router
from app.api import ops as ops_router
from app.api import players as players_router
from app.api import predictions as predictions_router
from app.api import push as push_router
from app.api import search as search_router
from app.api import stats as stats_router
from app.api import sync as sync_router
from app.api import table as table_router
from app.api import teams as teams_router
from app.api import telegram as telegram_router
from app.api import title_race as title_race_router
from app.api import power_rankings as power_rankings_router
from app.api import top_scorer_race as top_scorer_race_router
from app.api import tipsters as tipsters_router
from app.core.db import lifespan
from app.core.error_log import ErrorLogMiddleware

app = FastAPI(title="EPL Prediction Lab", lifespan=lifespan)

# Error middleware first so 500s from any later middleware still get logged.
app.add_middleware(ErrorLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(matches_router.router)
app.include_router(predictions_router.router)
app.include_router(chat_router.router)
app.include_router(table_router.router)
app.include_router(stats_router.router)
app.include_router(teams_router.router)
app.include_router(admin_router.router)
app.include_router(push_router.router)
app.include_router(fpl_router.router)
app.include_router(search_router.router)
app.include_router(players_router.router)
app.include_router(tipsters_router.router)
app.include_router(news_router.router)
app.include_router(compare_router.router)
app.include_router(ops_router.router)
app.include_router(telegram_router.router)
app.include_router(discord_router.router)
app.include_router(email_router.router)
app.include_router(title_race_router.router)
app.include_router(top_scorer_race_router.router)
app.include_router(power_rankings_router.router)
app.include_router(blog_router.router)
app.include_router(calibration_router.router)
app.include_router(by_team_router.router)
app.include_router(line_movement_router.router)
app.include_router(manager_router.router)
app.include_router(equity_curve_router.router)
app.include_router(sync_router.router)
app.include_router(arbitrage_router.router)


@app.get("/health")
@app.get("/api/health")
async def health() -> dict[str, str]:
    """Liveness probe — used by the GH Actions external watchdog and any
    internal health check. Dual-mounted so it works both in-cluster
    (`/health` direct to the api container) and via Caddy path routing
    on the shared VPS (`/api/*` → api, anything else → web)."""
    pool = app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT 1")
    return {"status": "ok"}
