from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
import asyncio
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.call import Call
from app.models.user import Session as UserSession
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
    sentiment_score: float | None = 0.0

class TranscriptTurn(BaseModel):
    role: str
    text: str

class CallDetail(CallSummary):
    resolution: str | None
    transcript: list[TranscriptTurn]

@router.get("", response_model=list[CallSummary])
async def list_calls(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[UserOut, Depends(current_user)]
) -> list[CallSummary]:
    result = await db.execute(select(Call).order_by(Call.start_time.desc()).limit(50))
    calls = result.scalars().all()
    
    return [
        CallSummary(
            id=c.id,
            caller_number=c.phone_number,
            called_number=c.called_number or "DishHome AI",
            customer_id=c.customer_id,
            customer_name=c.customer_name,
            language=c.language,
            started_at=c.start_time.isoformat() if c.start_time else "",
            ended_at=c.end_time.isoformat() if c.end_time else None,
            duration_sec=c.duration_seconds or 0,
            status=c.status,
            intent=c.intent or "unknown",
            ai_confidence=float(c.ai_confidence) if c.ai_confidence is not None else 0.0,
            sentiment_score=1.0 if c.sentiment == "positive" else (0.0 if c.sentiment == "negative" else 0.5),
        )
        for c in calls
    ]

@router.get("/stats")
async def stats(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[UserOut, Depends(current_user)]
) -> dict[str, int | float]:
    total = (await db.execute(select(func.count(Call.id)))).scalar_one() or 0
    in_progress = (await db.execute(select(func.count(Call.id)).where(Call.status == 'in_progress'))).scalar_one() or 0
    resolved = (await db.execute(select(func.count(Call.id)).where(Call.status == 'resolved'))).scalar_one() or 0
    ticketed = (await db.execute(select(func.count(Call.id)).where(Call.status == 'ticket_created'))).scalar_one() or 0
    sum_duration = (await db.execute(select(func.sum(Call.duration_seconds)))).scalar_one() or 0

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
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[UserOut, Depends(current_user)],
) -> CallDetail:
    result = await db.execute(select(Call).where(Call.id == call_id))
    c = result.scalar_one_or_none()
        
    if not c:
        raise HTTPException(404, "Call not found")
        
    return CallDetail(
        id=c.id,
        caller_number=c.phone_number,
        called_number=c.called_number or "DishHome AI",
        customer_id=c.customer_id,
        customer_name=c.customer_name,
        language=c.language,
        started_at=c.start_time.isoformat() if c.start_time else "",
        ended_at=c.end_time.isoformat() if c.end_time else None,
        duration_sec=c.duration_seconds or 0,
        status=c.status,
        resolution=c.resolution,
        intent=c.intent or "unknown",
        ai_confidence=float(c.ai_confidence) if c.ai_confidence is not None else 0.0,
        sentiment_score=1.0 if c.sentiment == "positive" else (0.0 if c.sentiment == "negative" else 0.5),
        transcript=[TranscriptTurn(**t) for t in (c.transcript or [])],
    )

@router.post("/session", response_model=CallSession)
async def create_session(
    payload: CallSessionCreate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[UserOut, Depends(current_user)],
) -> CallSession:
    session_id = str(uuid4())
    
    new_call = Call(
        id=session_id,
        phone_number=payload.caller_number,
        language="ne",
        status="in_progress",
        transcript=[]
    )
    db.add(new_call)
    await db.commit()

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
    
    from app.database import get_db_session
    # Note: Websockets can't use Depends() easily for sessions in a loop,
    # but we can resolve the token once at start.
    from sqlalchemy import select
    from app.database import engine
    from sqlalchemy.ext.asyncio import AsyncSession
    
    import time
    async with AsyncSession(engine) as db:
        result = await db.execute(select(UserSession).where(UserSession.token == token))
        sess = result.scalar_one_or_none()
        if not sess or sess.expires_at < time.time():
            await websocket.close(code=4001, reason="Invalid or expired token")
            return

    await websocket.accept()
    try:
        while True:
            chunk = await websocket.receive_bytes()
            # STUB: echo back
            await websocket.send_bytes(chunk)
    except WebSocketDisconnect:
        return

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                self.disconnect(connection)

live_manager = ConnectionManager()

@router.websocket("/live")
async def live_dashboard(websocket: WebSocket, token: str = Query(None)):
    from app.security import decode_access_token
    if not token or not decode_access_token(token):
        await websocket.close(code=4001, reason="Invalid token")
        return
        
    await live_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        live_manager.disconnect(websocket)
