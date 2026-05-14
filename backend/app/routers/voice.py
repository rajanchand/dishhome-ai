"""Voice catalog + preview + custom voice upload.

In production:
- /preview returns streamed audio from Piper/Coqui TTS.
- /upload accepts a customer sample, runs it through a voice-cloning trainer,
  and produces a Piper/Coqui voice model.

Here we accept the upload, validate the audio header, store metadata, and
expose it in the catalog. The demo /preview returns a synthesis spec the
browser plays via the Web Speech API.
"""

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.mock_data import VOICES
from app.routers.auth import UserOut, current_user

router = APIRouter(prefix="/voice", tags=["voice"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "voice_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CATALOG_FILE = UPLOAD_DIR / "_catalog.json"

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {
    "audio/wav": ".wav",
    "audio/wave": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
    "audio/m4a": ".m4a",
    "audio/x-m4a": ".m4a",
}


class Voice(BaseModel):
    id: str
    name: str
    language: str
    gender: str
    tone: str
    source: Literal["builtin", "uploaded"] = "builtin"
    sample_url: str | None = None
    created_at: str | None = None


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
    sample_url: str | None = None


def _load_uploaded() -> list[dict]:
    if not CATALOG_FILE.exists():
        return []
    try:
        return json.loads(CATALOG_FILE.read_text())
    except json.JSONDecodeError:
        return []


def _save_uploaded(items: list[dict]) -> None:
    CATALOG_FILE.write_text(json.dumps(items, indent=2))


def _all_voices() -> list[dict]:
    builtins = [{**v, "source": "builtin", "sample_url": None} for v in VOICES]
    uploaded = [{**v, "source": "uploaded"} for v in _load_uploaded()]
    return builtins + uploaded


@router.get("/voices", response_model=list[Voice])
def list_voices(_: Annotated[UserOut, Depends(current_user)]) -> list[Voice]:
    return [Voice(**v) for v in _all_voices()]


@router.post("/preview", response_model=PreviewResponse)
def preview(
    payload: PreviewRequest,
    _: Annotated[UserOut, Depends(current_user)],
) -> PreviewResponse:
    voice = next((v for v in _all_voices() if v["id"] == payload.voice_id), None)
    if not voice:
        raise HTTPException(404, "Voice not found")
    return PreviewResponse(
        voice_id=voice["id"],
        text=payload.text,
        language="ne-NP" if voice["language"] == "ne" else "en-US",
        gender=voice["gender"],
        rate=1.0,
        pitch=1.0 if voice["gender"] == "female" else 0.9,
        sample_url=voice.get("sample_url"),
    )


@router.post("/upload", response_model=Voice)
async def upload_voice(
    user: Annotated[UserOut, Depends(current_user)],
    file: Annotated[UploadFile, File(...)],
    name: Annotated[str, Form(min_length=1, max_length=80)],
    language: Annotated[Literal["ne", "en"], Form()] = "ne",
    gender: Annotated[Literal["female", "male"], Form()] = "female",
    tone: Annotated[str, Form(max_length=120)] = "custom upload",
) -> Voice:
    ctype = (file.content_type or "").lower()
    if ctype not in ALLOWED_TYPES:
        raise HTTPException(
            415,
            f"Unsupported audio type {ctype!r}. Allowed: {', '.join(sorted(ALLOWED_TYPES))}",
        )
    ext = ALLOWED_TYPES[ctype]
    voice_id = f"custom-{language}-{gender}-{secrets.token_hex(4)}"
    target = UPLOAD_DIR / f"{voice_id}{ext}"

    written = 0
    with target.open("wb") as out:
        while chunk := await file.read(64 * 1024):
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                out.close()
                target.unlink(missing_ok=True)
                raise HTTPException(413, f"File too large (>{MAX_UPLOAD_BYTES // (1024 * 1024)}MB)")
            out.write(chunk)

    entry = {
        "id": voice_id,
        "name": name.strip(),
        "language": language,
        "gender": gender,
        "tone": tone.strip() or "custom upload",
        "sample_url": f"/voice/sample/{voice_id}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "uploaded_by": user.username,
        "_filename": target.name,
    }
    items = _load_uploaded()
    items.append(entry)
    _save_uploaded(items)
    return Voice(
        id=entry["id"],
        name=entry["name"],
        language=entry["language"],
        gender=entry["gender"],
        tone=entry["tone"],
        source="uploaded",
        sample_url=entry["sample_url"],
        created_at=entry["created_at"],
    )


@router.get("/sample/{voice_id}")
def get_sample(
    voice_id: str,
    _: Annotated[UserOut, Depends(current_user)],
):
    from fastapi.responses import FileResponse

    item = next((v for v in _load_uploaded() if v["id"] == voice_id), None)
    if not item:
        raise HTTPException(404, "Sample not found")
    path = UPLOAD_DIR / item["_filename"]
    if not path.exists():
        raise HTTPException(404, "Sample file missing on disk")
    return FileResponse(path, media_type="application/octet-stream", filename=item["_filename"])


@router.delete("/voices/{voice_id}", status_code=204)
def delete_voice(
    voice_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> None:
    items = _load_uploaded()
    target = next((v for v in items if v["id"] == voice_id), None)
    if not target:
        raise HTTPException(404, "Voice not found or not deletable")
    path = UPLOAD_DIR / target["_filename"]
    path.unlink(missing_ok=True)
    _save_uploaded([v for v in items if v["id"] != voice_id])
