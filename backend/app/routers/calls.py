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
def list_calls(_: Annotated[UserOut, Depends(current_user)]) -> list[CallSummary]:
    return [CallSummary(**{k: v for k, v in c.items() if k not in ("transcript", "resolution")}) for c in CALLS]


@router.get("/stats")
def stats(_: Annotated[UserOut, Depends(current_user)]) -> dict[str, int | float]:
    total = len(CALLS)
    in_progress = sum(1 for c in CALLS if c["status"] == "in_progress")
    resolved = sum(1 for c in CALLS if c["status"] == "resolved")
    ticketed = sum(1 for c in CALLS if c["status"] == "ticket_created")
    avg_handle = (
        round(sum(c["duration_sec"] for c in CALLS) / total, 1) if total else 0
    )
    return {
        "total": total,
        "in_progress": in_progress,
        "resolved": resolved,
        "ticketed": ticketed,
        "avg_handle_sec": avg_handle,
        "ai_resolution_rate": round(resolved / total, 2) if total else 0.0,
    }


@router.get("/{call_id}", response_model=CallDetail)
def call_detail(
    call_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> CallDetail:
    call = next((c for c in CALLS if c["id"] == call_id), None)
    if not call:
        raise HTTPException(404, "Call not found")
    return CallDetail(**call)


@router.post("/session", response_model=CallSession)
def create_session(
    payload: CallSessionCreate,
    _: Annotated[UserOut, Depends(current_user)],
) -> CallSession:
    session = CallSession(
        session_id=str(uuid4()),
        caller_number=payload.caller_number,
        called_number=payload.called_number,
        status="created",
    )
    CALLS.append(
        {
            "id": session.session_id,
            "caller_number": session.caller_number,
            "called_number": session.called_number,
            "customer_id": None,
            "customer_name": None,
            "language": "ne",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": None,
            "duration_sec": 0,
            "status": "in_progress",
            "resolution": None,
            "intent": "unknown",
            "ai_confidence": 0.0,
            "transcript": [],
        }
    )
    return session


@router.websocket("/audio/{session_id}")
async def audio_bridge(websocket: WebSocket, session_id: str) -> None:
    # session_id will be used to route audio to the right call session in real impl.
    del session_id
    await websocket.accept()
    try:
        while True:
            # STUB: real impl will pump PCM frames -> STT -> LLM -> TTS -> PCM frames back.
            chunk = await websocket.receive_bytes()
            await websocket.send_bytes(chunk)
    except WebSocketDisconnect:
        return
