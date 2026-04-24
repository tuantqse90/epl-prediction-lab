"""POST /api/chat — streaming Q&A with per-session multi-turn memory.

Session history (`chat_messages` table) is replayed to the LLM on every turn
so follow-up questions retain context. `session_id` is a client-generated UUID
the frontend stashes in localStorage.
"""

from __future__ import annotations

import os
import uuid as uuid_mod
from typing import AsyncIterator

import asyncpg
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.llm.chat_context import build_chat_context
from app.llm.chat_prompt import build_chat_system, build_chat_user, suggested_prompts

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Protect Qwen quota from runaway spam. Counts persisted user messages in the
# trailing hour per session_id — the DB is already the system of record, no
# in-memory state to worry about.
CHAT_RATE_LIMIT_MESSAGES = 20
CHAT_RATE_LIMIT_WINDOW_MINUTES = 60


class ChatRequest(BaseModel):
    match_id: int = Field(..., description="id of the match being discussed")
    question: str = Field(..., min_length=1, max_length=500)
    session_id: str | None = Field(None, description="client UUID for per-device chat memory")
    lang: str = Field("vi", description="ui language: 'vi' or 'en'")


class HistoryMessage(BaseModel):
    role: str
    content: str


async def _stream_qwen(messages: list[dict], model: str) -> AsyncIterator[str]:
    from litellm import acompletion

    api_base = os.environ.get(
        "DASHSCOPE_API_BASE",
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )
    resp = await acompletion(
        model=f"openai/{model}",
        api_base=api_base,
        api_key=os.environ["DASHSCOPE_API_KEY"],
        messages=messages,
        temperature=0.5,
        max_tokens=360,
        stream=True,
    )
    async for chunk in resp:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


async def _persist(
    pool: asyncpg.Pool, session_id: uuid_mod.UUID, match_id: int, role: str, content: str,
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO chat_messages (session_id, match_id, role, content) "
            "VALUES ($1, $2, $3, $4)",
            session_id, match_id, role, content,
        )


async def _count_recent_user_messages(
    pool: asyncpg.Pool, session_id: uuid_mod.UUID, window_minutes: int,
) -> int:
    async with pool.acquire() as conn:
        n = await conn.fetchval(
            """
            SELECT COUNT(*) FROM chat_messages
            WHERE session_id = $1 AND role = 'user'
              AND created_at >= NOW() - ($2 || ' minutes')::INTERVAL
            """,
            session_id, str(window_minutes),
        )
    return int(n or 0)


async def _fetch_history(
    pool: asyncpg.Pool, session_id: uuid_mod.UUID, match_id: int, limit: int = 10,
) -> list[HistoryMessage]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT role, content FROM chat_messages
            WHERE session_id = $1 AND match_id = $2
            ORDER BY created_at ASC
            LIMIT $3
            """,
            session_id, match_id, limit,
        )
    return [HistoryMessage(role=r["role"], content=r["content"]) for r in rows]


def _parse_session_id(raw: str | None) -> uuid_mod.UUID | None:
    if not raw:
        return None
    try:
        return uuid_mod.UUID(raw)
    except ValueError:
        return None


@router.post("")
async def chat(req: ChatRequest, request: Request) -> StreamingResponse:
    pool = request.app.state.pool
    try:
        ctx = await build_chat_context(pool, req.match_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

    session_id = _parse_session_id(req.session_id) or uuid_mod.uuid4()
    lang = "en" if req.lang == "en" else "vi"

    used = await _count_recent_user_messages(pool, session_id, CHAT_RATE_LIMIT_WINDOW_MINUTES)
    if used >= CHAT_RATE_LIMIT_MESSAGES:
        msg = (
            f"Chat limit reached ({CHAT_RATE_LIMIT_MESSAGES} messages per "
            f"{CHAT_RATE_LIMIT_WINDOW_MINUTES} minutes). Come back shortly."
            if lang == "en"
            else (
                f"Đã dùng hết {CHAT_RATE_LIMIT_MESSAGES} câu hỏi trong "
                f"{CHAT_RATE_LIMIT_WINDOW_MINUTES} phút. Vui lòng quay lại sau."
            )
        )
        raise HTTPException(429, msg)

    history = await _fetch_history(pool, session_id, req.match_id)

    # First turn carries the full RAG data block; follow-ups just send the
    # question (the model already saw the data in turn 1 via history replay).
    user_payload = (
        build_chat_user(**ctx, question=req.question, lang=lang)
        if not history
        else req.question
    )

    messages: list[dict] = [{"role": "system", "content": build_chat_system(lang)}]
    for h in history:
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": user_payload})

    await _persist(pool, session_id, req.match_id, "user", user_payload)

    async def gen() -> AsyncIterator[str]:
        buffer = ""
        try:
            async for token in _stream_qwen(messages, "qwen-plus"):
                buffer += token
                yield token
        except Exception as e:
            yield f"\n\n[chat error: {type(e).__name__}]"
        finally:
            if buffer:
                await _persist(pool, session_id, req.match_id, "assistant", buffer)

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "X-Session-Id": str(session_id),
    }
    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8", headers=headers)


@router.get("/history", response_model=list[HistoryMessage])
async def history(
    request: Request,
    session_id: str,
    match_id: int,
) -> list[HistoryMessage]:
    sid = _parse_session_id(session_id)
    if sid is None:
        raise HTTPException(400, "invalid session_id (must be UUID)")
    return await _fetch_history(request.app.state.pool, sid, match_id)


@router.get("/suggest/{match_id}")
async def suggest(match_id: int, request: Request, lang: str = "vi") -> dict:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT ht.name AS home, at.name AS away
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.id = $1
            """,
            match_id,
        )
    if row is None:
        raise HTTPException(404, f"match {match_id} not found")
    lang_arg = "en" if lang == "en" else "vi"
    return {"prompts": suggested_prompts(home=row["home"], away=row["away"], lang=lang_arg)}
