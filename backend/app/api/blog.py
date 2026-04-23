"""GET /api/blog — auto-generated weekly blog posts (DB-backed).

Frontend /blog reads file-based posts from content/blog/*.md PLUS these
weekly auto posts via this endpoint. Keyed on slug.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel


router = APIRouter(prefix="/api/blog", tags=["blog"])


class BlogPost(BaseModel):
    slug: str
    title: str
    excerpt: str
    body_md: str
    tags: list[str]
    lang: str
    generated_at: datetime
    model: str | None


@router.get("", response_model=list[BlogPost])
async def list_auto_posts(request: Request, limit: int = 20, lang: str = "en") -> list[BlogPost]:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT slug, title, excerpt, body_md, tags, lang, generated_at, model
            FROM auto_blog_posts
            WHERE lang = $1
            ORDER BY generated_at DESC
            LIMIT $2
            """,
            lang, limit,
        )
    return [BlogPost(**dict(r)) for r in rows]


@router.get("/{slug}", response_model=BlogPost | None)
async def get_auto_post(slug: str, request: Request) -> BlogPost | None:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT slug, title, excerpt, body_md, tags, lang, generated_at, model
            FROM auto_blog_posts WHERE slug = $1
            """,
            slug,
        )
    return BlogPost(**dict(row)) if row else None
