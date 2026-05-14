"""Voice catalog + preview stubs.

In production, /preview returns streamed audio from Piper/Coqui TTS.
Here we return the catalog + a synthesis spec the frontend uses with the
Web Speech API for a live, working demo.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.mock_data import VOICES
from app.routers.auth import UserOut, current_user

router = APIRouter(prefix="/voice", tags=["voice"])


class Voice(BaseModel):
    id: str
    name: str
    language: str
    gender: str
    tone: str


class PreviewRequest(BaseModel):
    voice_id: str
    text: str = Field(min_length=1, max_length=400)


class PreviewResponse(BaseModel):
    voice_id: str
    text: str
    language: str
    gender: str
    rate: float
    pitch: float


@router.get("/voices", response_model=list[Voice])
def list_voices(_: Annotated[UserOut, Depends(current_user)]) -> list[Voice]:
    return [Voice(**v) for v in VOICES]


@router.post("/preview", response_model=PreviewResponse)
def preview(
    payload: PreviewRequest,
    _: Annotated[UserOut, Depends(current_user)],
) -> PreviewResponse:
    voice = next((v for v in VOICES if v["id"] == payload.voice_id), None)
    if not voice:
        voice = VOICES[0]
    return PreviewResponse(
        voice_id=voice["id"],
        text=payload.text,
        language="ne-NP" if voice["language"] == "ne" else "en-US",
        gender=voice["gender"],
        rate=1.0,
        pitch=1.0 if voice["gender"] == "female" else 0.9,
    )
