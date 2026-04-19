"""GET /api/news — recent football headlines linked to our team/league graph."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.leagues import get_league

router = APIRouter(prefix="/api/news", tags=["news"])


class NewsItem(BaseModel):
    source: str
    url: str
    title: str
    summary: str | None
    published_at: datetime
    teams: list[str]
    league_code: str | None


@router.get("", response_model=list[NewsItem])
async def list_news(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    league: str | None = Query(None, description="league slug or code"),
    team: str | None = Query(None, description="team slug filter"),
) -> list[NewsItem]:
    pool = request.app.state.pool

    league_code: str | None = None
    if league:
        try:
            league_code = get_league(league).code
        except KeyError:
            league_code = None

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT source, url, title, summary, published_at, teams, league_code
            FROM news_items
            WHERE ($1::text IS NULL OR league_code = $1)
              AND ($2::text IS NULL OR $2 = ANY(teams))
            ORDER BY published_at DESC
            LIMIT $3
            """,
            league_code, team, limit,
        )
    return [
        NewsItem(
            source=r["source"],
            url=r["url"],
            title=r["title"],
            summary=r["summary"],
            published_at=r["published_at"],
            teams=list(r["teams"] or []),
            league_code=r["league_code"],
        )
        for r in rows
    ]
