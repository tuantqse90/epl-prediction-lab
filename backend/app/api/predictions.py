"""POST /api/predictions/:match_id — compute + persist a prediction on demand."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app import queries
from app.core.config import get_settings
from app.llm.reasoning import explain_prediction
from app.predict.service import predict_and_persist
from app.schemas import MatchOut

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.post("/{match_id}", response_model=MatchOut)
async def compute_prediction(
    match_id: int,
    request: Request,
    with_reasoning: bool = True,
) -> MatchOut:
    settings = get_settings()
    pool = request.app.state.pool
    try:
        await predict_and_persist(
            pool,
            match_id,
            rho=settings.default_rho,
            model_version=settings.model_version,
            last_n=settings.default_last_n,
            temperature=settings.default_temperature,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(409, str(e))

    if with_reasoning and settings.dashscope_api_key:
        await explain_prediction(pool, match_id)

    row = await queries.get_match(pool, match_id)
    return MatchOut.model_validate(queries.record_to_match_dict(row))
