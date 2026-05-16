from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.mock_data import CALLS
from app.routers.auth import UserOut, current_user

router = APIRouter(prefix="/calls", tags=["calls"])


class CallSessionCreate(BaseModel):
    caller_number: str
    called_number: str


class CallSession(BaseModel):
    session_id: str
    caller_number: str
    called_number: str
    status: str


class CallSummary(BaseModel):
    id: str
    caller_number: str
    called_number: str
    customer_id: str | None
    customer_name: str | None
    language: str
    started_at: str
    ended_at: str | None
    duration_sec: int
    status: str
    intent: str
    ai_confidence: float


class TranscriptTurn(BaseModel):
    role: str
    text: str


class CallDetail(CallSummary):
    resolution: str | None
    transcript: list[TranscriptTurn]


@router.get("", response_model=list[CallSummary])
async def list_calls(_: Annotated[UserOut, Depends(current_user)]) -> list[CallSummary]:
    from app.database import get_pool
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM dh.calls ORDER BY started_at DESC LIMIT 50")
    
    return [
        CallSummary(
            id=r["id"],
            caller_number=r["caller_number"],
            called_number=r["called_number"],
            customer_id=r["customer_id"],
            customer_name=r["customer_name"],
            language=r["language"],
            started_at=r["started_at"].isoformat() if r["started_at"] else "",
            ended_at=r["ended_at"].isoformat() if r["ended_at"] else "",
            duration_sec=r["duration_sec"] or 0,
            status=r["status"],
            intent=r["intent"] or "",
            ai_confidence=float(r["ai_confidence"]) if r["ai_confidence"] is not None else 0.0,
        )
        for r in rows
    ]


@router.get("/stats")
async def stats(_: Annotated[UserOut, Depends(current_user)]) -> dict[str, int | float]:
    from app.database import get_pool
    pool = get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT count(*) FROM dh.calls") or 0
        in_progress = await conn.fetchval("SELECT count(*) FROM dh.calls WHERE status = 'in_progress'") or 0
        resolved = await conn.fetchval("SELECT count(*) FROM dh.calls WHERE status = 'resolved'") or 0
        ticketed = await conn.fetchval("SELECT count(*) FROM dh.calls WHERE status = 'ticket_created'") or 0
        sum_duration = await conn.fetchval("SELECT sum(duration_sec) FROM dh.calls") or 0

    avg_handle = round(sum_duration / total, 1) if total else 0
    return {
        "total": total,
        "in_progress": in_progress,
        "resolved": resolved,
        "ticketed": ticketed,
        "avg_handle_sec": avg_handle,
        "ai_resolution_rate": round(resolved / total, 2) if total else 0.0,
    }


@router.get("/{call_id}", response_model=CallDetail)
async def call_detail(
    call_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> CallDetail:
    from app.database import get_pool
    import json
    pool = get_pool()
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT * FROM dh.calls WHERE id = $1", call_id)
        
    if not r:
        raise HTTPException(404, "Call not found")
        
    transcript = json.loads(r["transcript"]) if isinstance(r["transcript"], str) else r["transcript"]
    
    return CallDetail(
        id=r["id"],
        caller_number=r["caller_number"],
        called_number=r["called_number"],
        customer_id=r["customer_id"],
        customer_name=r["customer_name"],
        language=r["language"],
        started_at=r["started_at"].isoformat() if r["started_at"] else "",
        ended_at=r["ended_at"].isoformat() if r["ended_at"] else "",
        duration_sec=r["duration_sec"] or 0,
        status=r["status"],
        resolution=r["resolution"],
        intent=r["intent"] or "",
        ai_confidence=float(r["ai_confidence"]) if r["ai_confidence"] is not None else 0.0,
        transcript=[TranscriptTurn(**t) for t in (transcript or [])],
    )


@router.post("/session", response_model=CallSession)
async def create_session(
    payload: CallSessionCreate,
    _: Annotated[UserOut, Depends(current_user)],
) -> CallSession:
    session_id = str(uuid4())
    
    from app.database import get_pool
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO dh.calls (
                id, caller_number, called_number, language, started_at, 
                duration_sec, status, intent, ai_confidence, transcript
            )
            VALUES ($1, $2, $3, 'ne', NOW(), 0, 'in_progress', 'unknown', 0.0, '[]'::jsonb)
            """,
            session_id, payload.caller_number, payload.called_number
        )

    return CallSession(
        session_id=session_id,
        caller_number=payload.caller_number,
        called_number=payload.called_number,
        status="created",
    )


@router.websocket("/audio/{session_id}")
async def audio_bridge(websocket: WebSocket, session_id: str) -> None:
    # Authenticate via query param: ws://host/calls/audio/123?token=abc
    token = websocket.query_params.get("token", "")
    if not token:
        await websocket.close(code=4001, reason="Missing auth token")
        return
    from app.security import resolve_session
    username = resolve_session(token)
    if not username:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return
    del session_id  # will be used to route audio in real impl
    await websocket.accept()
    try:
        while True:
            # STUB: real impl will pump PCM frames -> STT -> LLM -> TTS -> PCM frames back.
            chunk = await websocket.receive_bytes()
            await websocket.send_bytes(chunk)
    except WebSocketDisconnect:
        return
