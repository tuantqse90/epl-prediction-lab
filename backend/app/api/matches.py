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
) -> list[MatchOut]:
    rows = await queries.list_matches(
        request.app.state.pool, upcoming_only=upcoming_only, limit=limit
    )
    return [MatchOut.model_validate(queries.record_to_match_dict(r)) for r in rows]


@router.get("/{match_id}", response_model=MatchOut)
async def get_match(match_id: int, request: Request) -> MatchOut:
    row = await queries.get_match(request.app.state.pool, match_id)
    if row is None:
        raise HTTPException(404, f"match {match_id} not found")
    return MatchOut.model_validate(queries.record_to_match_dict(row))
