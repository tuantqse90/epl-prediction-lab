"""GET /api/players/:slug/radar — 6-axis radar chart data for a player.

Frontend renders as polygon. Axes are normalised per position against a
season-long baseline so cross-position comparison is meaningful."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.models.player_radar import build_radar


router = APIRouter(prefix="/api/players", tags=["players"])


class Radar(BaseModel):
    player_name: str
    position: str
    team_slug: str
    season: str
    axes: dict[str, float]      # axis name → [0, 1]
    raw: dict[str, float]


def _slug_to_name(slug: str) -> str:
    return slug.replace("-", " ")


@router.get("/{slug}/radar", response_model=Radar)
async def player_radar(
    slug: str, request: Request,
    season: str = Query("2025-26"),
) -> Radar:
    pool = request.app.state.pool
    # slug is a URL-friendly lower kebab. We match by lower(name) that
    # normalises punctuation, like the /players detail page already does.
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT ps.player_name, ps.position, ps.games, ps.goals,
                   ps.assists, ps.xg, ps.xa, ps.key_passes, t.slug AS team_slug
            FROM player_season_stats ps
            JOIN teams t ON t.id = ps.team_id
            WHERE ps.season = $1
              AND regexp_replace(lower(ps.player_name), '[^a-z0-9]+', '-', 'g') = $2
            ORDER BY ps.games DESC
            LIMIT 1
            """,
            season, slug,
        )
    if not row:
        raise HTTPException(status_code=404, detail="player not found")

    r = build_radar(
        position=row["position"] or "MF",
        goals=int(row["goals"] or 0),
        xg=float(row["xg"] or 0),
        assists=int(row["assists"] or 0),
        xa=float(row["xa"] or 0),
        key_passes=int(row["key_passes"] or 0),
        games=int(row["games"] or 0),
    )
    return Radar(
        player_name=row["player_name"],
        position=row["position"] or "MF",
        team_slug=row["team_slug"],
        season=season,
        axes={
            "goals_p90": r.goals_p90,
            "xg_p90": r.xg_p90,
            "assists_p90": r.assists_p90,
            "xa_p90": r.xa_p90,
            "key_passes_p90": r.key_passes_p90,
            "g_minus_xg": r.g_minus_xg,
        },
        raw={
            "games": float(row["games"] or 0),
            "goals": float(row["goals"] or 0),
            "xg": float(row["xg"] or 0),
            "assists": float(row["assists"] or 0),
            "xa": float(row["xa"] or 0),
            "key_passes": float(row["key_passes"] or 0),
        },
    )
