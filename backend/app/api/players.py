"""GET /api/players/{slug} — season-by-season stats for a single player.

Slug = slugified player_name (lowercase, non-alnum → dashes). Disambiguation
across players sharing the same slug (rare in top-5) happens on team — we
return all rows matching the slug across seasons, teams grouped.
"""

from __future__ import annotations

import os
import re
import urllib.request

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

router = APIRouter(prefix="/api/players", tags=["players"])


# ── Photo proxy ──────────────────────────────────────────────────────────────
# api-sports.io's player-photo CDN is API-key-gated: anonymous requests get
# 403 even from browsers. Proxying with our server-side key unlocks them and
# lets us set long cache headers so the heavy lifting is done once per player.
_PHOTO_CDN = "https://media.api-sports.io/football/players/{id}.png"


@router.get("/photo/{api_football_id}")
async def player_photo(api_football_id: int) -> Response:
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="API_FOOTBALL_KEY not configured")
    try:
        req = urllib.request.Request(
            _PHOTO_CDN.format(id=api_football_id),
            headers={"x-apisports-key": key, "User-Agent": "football-predict/photo-proxy"},
        )
        with urllib.request.urlopen(req, timeout=10) as upstream:
            body = upstream.read()
            content_type = upstream.headers.get("content-type", "image/png")
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=e.code, detail="upstream photo unavailable") from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"photo fetch failed: {type(e).__name__}") from e

    # Player photos are effectively static — cache aggressively on both the
    # browser and any shared proxy. 30 days with stale-while-revalidate.
    return Response(
        content=body,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=2592000, stale-while-revalidate=86400, immutable",
        },
    )


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class PlayerSeason(BaseModel):
    season: str
    team_slug: str
    team_short: str
    games: int
    goals: int
    assists: int
    xg: float
    xa: float
    npxg: float
    key_passes: int
    position: str | None


class PlayerProfile(BaseModel):
    slug: str
    player_name: str
    photo_url: str | None = None
    seasons: list[PlayerSeason]
    career_goals: int
    career_xg: float
    career_assists: int
    career_games: int


class PlayerBrowseRow(BaseModel):
    """Minimal card row for the /players index browse/search."""
    slug: str
    player_name: str
    team_slug: str
    team_short: str
    team_name: str
    position: str | None
    goals: int
    assists: int
    xg: float
    games: int
    photo_url: str | None = None
    league_code: str | None = None


class PlayerBrowseOut(BaseModel):
    players: list[PlayerBrowseRow]
    total_returned: int
    has_next: bool


@router.get("", response_model=PlayerBrowseOut)
async def list_players(
    request: Request,
    season: str = "2025-26",
    q: str = "",
    league: str | None = None,
    limit: int = 48,
    offset: int = 0,
) -> PlayerBrowseOut:
    """Paginated + searchable player browse backing /players.

    Search is case-insensitive substring match on player_name. Sort by
    goals desc so recognisable players surface first. limit capped at 100,
    offset at 2000 (matches /stats/scorers convention)."""
    from app.leagues import BY_SLUG

    limit = max(1, min(100, limit))
    offset = max(0, min(2000, offset))
    league_code = BY_SLUG[league].code if league and league in BY_SLUG else None

    # Dynamic WHERE pieces with predictable placeholder ordering: season is
    # always $1, then search if present, league if present, then limit+offset.
    where_parts = ["p.season = $1"]
    args: list = [season]
    if q:
        args.append(f"%{q}%")
        where_parts.append(f"p.player_name ILIKE ${len(args)}")
    if league_code:
        args.append(league_code)
        lc_idx = len(args)
        where_parts.append(
            f"EXISTS (SELECT 1 FROM matches m "
            f"WHERE (m.home_team_id = p.team_id OR m.away_team_id = p.team_id) "
            f"AND m.season = $1 AND m.league_code = ${lc_idx})"
        )
    args.append(limit + 1)           # $N for LIMIT — fetch +1 to detect hasNext
    limit_idx = len(args)
    args.append(offset)               # $M for OFFSET
    offset_idx = len(args)

    query = f"""
    SELECT p.player_name, p.position, p.goals, p.assists, p.xg, p.games,
           p.photo_url, p.api_football_player_id,
           t.slug AS team_slug, t.name AS team_name, t.short_name AS team_short,
           (SELECT league_code FROM matches m
            WHERE (m.home_team_id = p.team_id OR m.away_team_id = p.team_id)
              AND m.season = $1
            LIMIT 1) AS league_code
    FROM player_season_stats p
    JOIN teams t ON t.id = p.team_id
    WHERE {' AND '.join(where_parts)}
    ORDER BY p.goals DESC NULLS LAST, p.xg DESC NULLS LAST
    LIMIT ${limit_idx} OFFSET ${offset_idx}
    """

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)

    has_next = len(rows) > limit
    rows = rows[:limit]

    def _slug_for(name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

    out: list[PlayerBrowseRow] = []
    for r in rows:
        af_id = r["api_football_player_id"]
        photo = f"/api/players/photo/{int(af_id)}" if af_id else r["photo_url"]
        out.append(
            PlayerBrowseRow(
                slug=_slug_for(r["player_name"]),
                player_name=r["player_name"],
                team_slug=r["team_slug"],
                team_short=r["team_short"],
                team_name=r["team_name"],
                position=r["position"],
                goals=int(r["goals"] or 0),
                assists=int(r["assists"] or 0),
                xg=round(float(r["xg"] or 0.0), 2),
                games=int(r["games"] or 0),
                photo_url=photo,
                league_code=r["league_code"],
            )
        )
    return PlayerBrowseOut(players=out, total_returned=len(out), has_next=has_next)


@router.get("/{slug}", response_model=PlayerProfile)
async def get_player(slug: str, request: Request) -> PlayerProfile:
    pool = request.app.state.pool
    slug_norm = _slugify(slug)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT p.player_name, p.season, p.games, p.goals, p.assists,
                   p.xg, p.xa, p.npxg, p.key_passes, p.position, p.photo_url,
                   p.api_football_player_id,
                   t.slug AS team_slug, t.short_name AS team_short
            FROM player_season_stats p
            JOIN teams t ON t.id = p.team_id
            WHERE regexp_replace(lower(p.player_name), '[^a-z0-9]+', '-', 'g') LIKE $1
            ORDER BY p.season DESC, t.slug
            """,
            f"%{slug_norm}%",
        )

    if not rows:
        raise HTTPException(404, f"player {slug!r} not found")

    # Pick the most popular name variant as canonical.
    name_counts: dict[str, int] = {}
    for r in rows:
        name_counts[r["player_name"]] = name_counts.get(r["player_name"], 0) + 1
    canonical = max(name_counts, key=name_counts.get)

    seasons = [
        PlayerSeason(
            season=r["season"],
            team_slug=r["team_slug"],
            team_short=r["team_short"],
            games=int(r["games"] or 0),
            goals=int(r["goals"] or 0),
            assists=int(r["assists"] or 0),
            xg=float(r["xg"] or 0.0),
            xa=float(r["xa"] or 0.0),
            npxg=float(r["npxg"] or 0.0),
            key_passes=int(r["key_passes"] or 0),
            position=r["position"],
        )
        for r in rows if r["player_name"] == canonical
    ]

    # Prefer the api-football id (served via our proxy — CDN is key-gated).
    # Fall back to any stored photo_url only if the proxy route is unavailable.
    canonical_rows = [r for r in rows if r["player_name"] == canonical]
    af_id = next(
        (r["api_football_player_id"] for r in canonical_rows if r["api_football_player_id"]),
        None,
    )
    if af_id:
        photo_url: str | None = f"/api/players/photo/{int(af_id)}"
    else:
        photo_url = next(
            (r["photo_url"] for r in canonical_rows if r["photo_url"]),
            None,
        )

    return PlayerProfile(
        slug=_slugify(canonical),
        player_name=canonical,
        photo_url=photo_url,
        seasons=seasons,
        career_goals=sum(s.goals for s in seasons),
        career_xg=round(sum(s.xg for s in seasons), 2),
        career_assists=sum(s.assists for s in seasons),
        career_games=sum(s.games for s in seasons),
    )
