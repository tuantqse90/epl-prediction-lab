"""GET /api/matches — upcoming fixtures with latest prediction joined."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app import queries
from app.schemas import MatchOut

router = APIRouter(prefix="/api/matches", tags=["matches"])


@router.get("", response_model=list[MatchOut])
async def list_matches(
    request: Request,
    upcoming_only: bool = Query(True, description="Only matches with kickoff in the future"),
    limit: int = Query(20, ge=1, le=200),
    league: str | None = Query(None, description="league slug or code (e.g. epl, laliga)"),
) -> list[MatchOut]:
    from app.leagues import get_league
    league_code = get_league(league).code if league else None
    rows = await queries.list_matches(
        request.app.state.pool,
        upcoming_only=upcoming_only,
        limit=limit,
        league_code=league_code,
    )
    return [MatchOut.model_validate(queries.record_to_match_dict(r)) for r in rows]


@router.get("/{match_id}", response_model=MatchOut)
async def get_match(match_id: int, request: Request) -> MatchOut:
    pool = request.app.state.pool
    row = await queries.get_match(pool, match_id)
    if row is None:
        raise HTTPException(404, f"match {match_id} not found")
    data = queries.record_to_match_dict(row)
    data["events"] = await queries.get_match_events(pool, match_id)
    return MatchOut.model_validate(data)
