from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter(prefix="/calls", tags=["calls"])


class CallSessionCreate(BaseModel):
    caller_number: str
    called_number: str


class CallSession(BaseModel):
    session_id: str
    caller_number: str
    called_number: str
    status: str


@router.post("/session", response_model=CallSession)
async def create_session(payload: CallSessionCreate) -> CallSession:
    return CallSession(
        session_id=str(uuid4()),
        caller_number=payload.caller_number,
        called_number=payload.called_number,
        status="created",
    )


@router.websocket("/audio/{session_id}")
async def audio_bridge(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    try:
        while True:
            # STUB: real impl will pump PCM frames -> STT -> LLM -> TTS -> PCM frames back.
            chunk = await websocket.receive_bytes()
            await websocket.send_bytes(chunk)
    except WebSocketDisconnect:
        return
