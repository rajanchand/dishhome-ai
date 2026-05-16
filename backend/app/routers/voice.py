"""Voice catalog + preview + custom voice upload + ElevenLabs clone/synth.

When `ELEVENLABS_API_KEY` is set:
  - /voice/upload also creates an Instant Voice Clone on ElevenLabs and stores
    the remote voice_id alongside the local catalog entry.
  - /voice/preview returns real MP3 audio synthesized in the chosen voice.
  - /voice/synth returns MP3 bytes for an arbitrary text (used by /telephony
    to generate the audio Twilio plays into the call).

When no key is configured, /upload still works (just stores the raw file),
and /preview falls back to a synthesis spec the browser can play via the
Web Speech API.
"""

import hashlib
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app.config import settings
from app.elevenlabs_client import ElevenLabsError, clone_voice, synthesize
from app.mock_data import VOICES
from app.routers.auth import UserOut, current_user, require_permission

router = APIRouter(prefix="/voice", tags=["voice"])

# Detect if running on Vercel (read-only filesystem except for /tmp)
IS_VERCEL = os.environ.get("VERCEL") == "1" or os.environ.get("VERCEL_ENV") is not None

if IS_VERCEL:
    UPLOAD_DIR = Path("/tmp/voice_uploads")
else:
    UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "voice_uploads"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CATALOG_FILE = UPLOAD_DIR / "_catalog.json"
DEFAULTS_FILE = UPLOAD_DIR / "_defaults.json"

SYNTH_CACHE_DIR = UPLOAD_DIR / "_synth_cache"
SYNTH_CACHE_DIR.mkdir(parents=True, exist_ok=True)

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
    elevenlabs_voice_id: str | None = None
    cloned: bool = False


class PreviewRequest(BaseModel):
    # Now optional: when omitted the resolver picks the primary voice (or the
    # per-language default). Clients can pass voice_id to test a specific one.
    voice_id: str | None = None
    text: str = Field(min_length=1, max_length=400)
    language: str | None = None
    gender: str | None = None


class PreviewResponse(BaseModel):
    voice_id: str
    text: str
    language: str
    gender: str
    rate: float
    pitch: float
    sample_url: str | None = None
    # When ElevenLabs is configured we return a streamable MP3 URL instead of
    # asking the browser to TTS via Web Speech API.
    audio_url: str | None = None
    engine: Literal["elevenlabs", "browser-tts"] = "browser-tts"


def _load_uploaded() -> list[dict]:
    if not CATALOG_FILE.exists():
        return []
    try:
        return json.loads(CATALOG_FILE.read_text())
    except json.JSONDecodeError:
        return []


def _save_uploaded(items: list[dict]) -> None:
    CATALOG_FILE.write_text(json.dumps(items, indent=2))


def _builtin_with_eleven(v: dict) -> dict:
    eleven_id = settings.elevenlabs_voice_for(v["language"], v["gender"])
    return {
        **v,
        "source": "builtin",
        "sample_url": None,
        "elevenlabs_voice_id": eleven_id or None,
        "cloned": False,
    }


def _all_voices() -> list[dict]:
    builtins = [_builtin_with_eleven(v) for v in VOICES]
    uploaded = [{**v, "source": "uploaded", "cloned": bool(v.get("elevenlabs_voice_id"))} for v in _load_uploaded()]
    return builtins + uploaded


def _find_voice(voice_id: str) -> dict | None:
    return next((v for v in _all_voices() if v["id"] == voice_id), None)


# ---- primary-voice resolver ----
# `primary_voice_id` (when set) overrides everything: every preview, campaign,
# and outbound call uses this voice regardless of what the caller passed.
# `defaults_by_lang_gender` lets you set per-(language,gender) fallbacks.

def _load_defaults() -> dict:
    if not DEFAULTS_FILE.exists():
        return {"primary_voice_id": None, "defaults_by_lang_gender": {}}
    try:
        data = json.loads(DEFAULTS_FILE.read_text())
        data.setdefault("primary_voice_id", None)
        data.setdefault("defaults_by_lang_gender", {})
        return data
    except json.JSONDecodeError:
        return {"primary_voice_id": None, "defaults_by_lang_gender": {}}


def _save_defaults(data: dict) -> None:
    DEFAULTS_FILE.write_text(json.dumps(data, indent=2))


def resolve_voice(
    voice_id: str | None = None,
    language: str | None = None,
    gender: str | None = None,
) -> dict | None:
    """Return the voice the system should actually use.

    Precedence:
      1. primary_voice_id (operator override — wins over everything)
      2. requested voice_id (if it exists in the catalog)
      3. per-(language, gender) default
      4. per-language default (any gender)
      5. first matching builtin for that language
      6. first voice in catalog
    """
    defaults = _load_defaults()
    primary = defaults.get("primary_voice_id")
    if primary:
        v = _find_voice(primary)
        if v:
            return v
    if voice_id:
        v = _find_voice(voice_id)
        if v:
            return v
    by_lg = defaults.get("defaults_by_lang_gender") or {}
    if language and gender:
        key = f"{language}/{gender}"
        target = by_lg.get(key)
        if target:
            v = _find_voice(target)
            if v:
                return v
    if language:
        for key, target in by_lg.items():
            if key.startswith(f"{language}/"):
                v = _find_voice(target)
                if v:
                    return v
        for v in _all_voices():
            if v.get("language") == language:
                return v
    catalog = _all_voices()
    return catalog[0] if catalog else None


def _cache_key(eleven_voice_id: str, text: str) -> str:
    h = hashlib.sha256(f"{eleven_voice_id}|{text}".encode()).hexdigest()[:24]
    return h


async def synthesize_to_cache(eleven_voice_id: str, text: str) -> Path:
    """Synthesize via ElevenLabs and cache to disk. Returns the file path."""
    key = _cache_key(eleven_voice_id, text)
    target = SYNTH_CACHE_DIR / f"{key}.mp3"
    if target.exists() and target.stat().st_size > 0:
        return target
    audio = await synthesize(voice_id=eleven_voice_id, text=text)
    target.write_bytes(audio)
    return target


@router.get("/voices", response_model=list[Voice])
def list_voices(_: Annotated[UserOut, Depends(require_permission("voice.read"))]) -> list[Voice]:
    return [Voice(**v) for v in _all_voices()]


@router.get("/health")
def voice_health(_: Annotated[UserOut, Depends(current_user)]) -> dict:
    d = _load_defaults()
    return {
        "elevenlabs_enabled": settings.elevenlabs_enabled,
        "model_id": settings.elevenlabs_model_id,
        "primary_voice_id": d.get("primary_voice_id"),
        "defaults_by_lang_gender": d.get("defaults_by_lang_gender", {}),
        "defaults_set": {
            "ne_female": bool(settings.elevenlabs_voice_ne_female),
            "ne_male": bool(settings.elevenlabs_voice_ne_male),
            "en_female": bool(settings.elevenlabs_voice_en_female),
            "en_male": bool(settings.elevenlabs_voice_en_male),
        },
    }


# ---- voice defaults (primary override + per-lang/gender) ----
class VoiceDefaults(BaseModel):
    primary_voice_id: str | None = None
    defaults_by_lang_gender: dict[str, str] = {}


@router.get("/defaults", response_model=VoiceDefaults)
def get_defaults(_: Annotated[UserOut, Depends(require_permission("voice.read"))]) -> VoiceDefaults:
    return VoiceDefaults(**_load_defaults())


@router.put("/defaults", response_model=VoiceDefaults)
def set_defaults(
    payload: VoiceDefaults,
    _: Annotated[UserOut, Depends(require_permission("voice.upload"))],
) -> VoiceDefaults:
    # Validate every referenced voice_id exists.
    if payload.primary_voice_id and not _find_voice(payload.primary_voice_id):
        raise HTTPException(404, f"primary_voice_id {payload.primary_voice_id!r} not found")
    for key, vid in payload.defaults_by_lang_gender.items():
        if "/" not in key:
            raise HTTPException(400, f"Bad lang/gender key {key!r} — use 'ne/female' style")
        if not _find_voice(vid):
            raise HTTPException(404, f"Voice {vid!r} for {key} not found")
    data = payload.model_dump()
    _save_defaults(data)
    return VoiceDefaults(**data)


@router.post("/voices/{voice_id}/set-primary", response_model=VoiceDefaults)
def set_primary(
    voice_id: str,
    _: Annotated[UserOut, Depends(require_permission("voice.upload"))],
) -> VoiceDefaults:
    v = _find_voice(voice_id)
    if not v:
        raise HTTPException(404, "Voice not found")
    data = _load_defaults()
    data["primary_voice_id"] = voice_id
    _save_defaults(data)
    return VoiceDefaults(**data)


@router.post("/defaults/clear-primary", response_model=VoiceDefaults)
def clear_primary(
    _: Annotated[UserOut, Depends(require_permission("voice.upload"))],
) -> VoiceDefaults:
    data = _load_defaults()
    data["primary_voice_id"] = None
    _save_defaults(data)
    return VoiceDefaults(**data)


@router.get("/resolve")
def resolve(
    _: Annotated[UserOut, Depends(require_permission("voice.read"))],
    voice_id: str | None = None,
    language: str | None = None,
    gender: str | None = None,
) -> dict:
    """Diagnostic: show which voice the system would pick for these inputs."""
    v = resolve_voice(voice_id=voice_id, language=language, gender=gender)
    if not v:
        raise HTTPException(404, "No voices available")
    d = _load_defaults()
    return {
        "resolved": Voice(**v).model_dump(),
        "primary_override_applied": d.get("primary_voice_id") == v["id"],
        "requested": {"voice_id": voice_id, "language": language, "gender": gender},
    }


@router.post("/preview", response_model=PreviewResponse)
async def preview(
    payload: PreviewRequest,
    _: Annotated[UserOut, Depends(require_permission("voice.read"))],
) -> PreviewResponse:
    voice = resolve_voice(
        voice_id=payload.voice_id,
        language=payload.language,
        gender=payload.gender,
    )
    if not voice:
        raise HTTPException(404, "No voices available")
    eleven_id = voice.get("elevenlabs_voice_id")
    audio_url: str | None = None
    engine: Literal["elevenlabs", "browser-tts"] = "browser-tts"
    if settings.elevenlabs_enabled and eleven_id:
        try:
            await synthesize_to_cache(eleven_id, payload.text)
            audio_url = f"/voice/tts?voice_id={voice['id']}&text={payload.text}"
            engine = "elevenlabs"
        except ElevenLabsError:
            audio_url = None
            engine = "browser-tts"
    return PreviewResponse(
        voice_id=voice["id"],
        text=payload.text,
        language="ne-NP" if voice["language"] == "ne" else "en-US",
        gender=voice["gender"],
        rate=1.0,
        pitch=1.0 if voice["gender"] == "female" else 0.9,
        sample_url=voice.get("sample_url"),
        audio_url=audio_url,
        engine=engine,
    )


@router.get("/tts")
async def tts(
    voice_id: str,
    text: str,
    _: Annotated[UserOut, Depends(require_permission("voice.read"))],
) -> Response:
    """Stream the cached MP3 for (voice_id, text). Generates on first hit."""
    voice = _find_voice(voice_id)
    if not voice:
        raise HTTPException(404, "Voice not found")
    eleven_id = voice.get("elevenlabs_voice_id")
    if not (settings.elevenlabs_enabled and eleven_id):
        raise HTTPException(
            503,
            "ElevenLabs not configured for this voice. Set ELEVENLABS_API_KEY and a voice mapping.",
        )
    try:
        path = await synthesize_to_cache(eleven_id, text)
    except ElevenLabsError as e:
        raise HTTPException(502, str(e)) from e
    return FileResponse(path, media_type="audio/mpeg")


@router.get("/tts/public")
async def tts_public(voice_id: str, text: str, token: str = "") -> Response:
    """Unauthenticated TTS used by Twilio TwiML <Play>.

    The token must match an active telephony session. We additionally require
    that (voice_id, text) match the session's bound parameters — preventing
    a leaked token from synthesizing arbitrary text against the operator's
    ElevenLabs credit.
    """
    if not token:
        raise HTTPException(401, "Missing session token")
    from app.routers.telephony import SESSIONS  # local import: avoid cycle
    sess = SESSIONS.get(token)
    if not sess:
        raise HTTPException(401, "Unknown or expired session token")
    if sess.get("voice_id") != voice_id or sess.get("text") != text:
        raise HTTPException(403, "Token not bound to this voice/text")
    voice = _find_voice(voice_id)
    if not voice:
        raise HTTPException(404, "Voice not found")
    eleven_id = voice.get("elevenlabs_voice_id")
    if not (settings.elevenlabs_enabled and eleven_id):
        raise HTTPException(503, "ElevenLabs not configured for this voice")
    try:
        path = await synthesize_to_cache(eleven_id, text)
    except ElevenLabsError as e:
        raise HTTPException(502, str(e)) from e
    return FileResponse(path, media_type="audio/mpeg")


@router.post("/upload", response_model=Voice)
async def upload_voice(
    user: Annotated[UserOut, Depends(require_permission("voice.upload"))],
    file: Annotated[UploadFile, File(...)],
    name: Annotated[str, Form(min_length=1, max_length=80)],
    language: Annotated[Literal["ne", "en"], Form()] = "ne",
    gender: Annotated[Literal["female", "male"], Form()] = "female",
    tone: Annotated[str, Form(max_length=120)] = "custom upload",
    clone: Annotated[bool, Form()] = True,
    set_as_primary: Annotated[bool, Form()] = False,
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
    raw_chunks: list[bytes] = []
    with target.open("wb") as out:
        while chunk := await file.read(64 * 1024):
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                out.close()
                target.unlink(missing_ok=True)
                raise HTTPException(413, f"File too large (>{MAX_UPLOAD_BYTES // (1024 * 1024)}MB)")
            out.write(chunk)
            raw_chunks.append(chunk)

    elevenlabs_voice_id: str | None = None
    if clone and settings.elevenlabs_enabled:
        try:
            elevenlabs_voice_id = await clone_voice(
                name=name.strip(),
                description=f"DishHome custom voice ({language}/{gender}): {tone}",
                sample_filename=target.name,
                sample_bytes=b"".join(raw_chunks),
                sample_mime=ctype,
            )
        except ElevenLabsError as e:
            # Keep the local upload but flag the clone failure to the caller.
            raise HTTPException(502, f"Voice saved locally but cloning failed: {e}") from e

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
        "elevenlabs_voice_id": elevenlabs_voice_id,
    }
    items = _load_uploaded()
    items.append(entry)
    _save_uploaded(items)

    # Promote this voice to primary either when the operator asked for it, or
    # automatically when it's the FIRST uploaded voice and no primary is set
    # yet — so "I just uploaded Rajan's voice" makes the whole system use it
    # without an extra click.
    defaults = _load_defaults()
    has_primary = bool(defaults.get("primary_voice_id"))
    is_first_upload = len(items) == 1
    if set_as_primary or (is_first_upload and not has_primary):
        defaults["primary_voice_id"] = voice_id
        _save_defaults(defaults)

    return Voice(
        id=entry["id"],
        name=entry["name"],
        language=entry["language"],
        gender=entry["gender"],
        tone=entry["tone"],
        source="uploaded",
        sample_url=entry["sample_url"],
        created_at=entry["created_at"],
        elevenlabs_voice_id=elevenlabs_voice_id,
        cloned=bool(elevenlabs_voice_id),
    )


@router.get("/sample/{voice_id}")
def get_sample(
    voice_id: str,
    _: Annotated[UserOut, Depends(require_permission("voice.read"))],
):
    item = next((v for v in _load_uploaded() if v["id"] == voice_id), None)
    if not item:
        raise HTTPException(404, "Sample not found")
    path = UPLOAD_DIR / item["_filename"]
    if not path.exists():
        raise HTTPException(404, "Sample file missing on disk")
    return FileResponse(path, media_type="application/octet-stream", filename=item["_filename"])


@router.delete("/voices/{voice_id}", status_code=204)
async def delete_voice(
    voice_id: str,
    _: Annotated[UserOut, Depends(require_permission("voice.upload"))],
) -> None:
    items = _load_uploaded()
    target = next((v for v in items if v["id"] == voice_id), None)
    if not target:
        raise HTTPException(404, "Voice not found or not deletable")
    path = UPLOAD_DIR / target["_filename"]
    path.unlink(missing_ok=True)
    _save_uploaded([v for v in items if v["id"] != voice_id])
    # Best-effort cleanup of the remote ElevenLabs clone so we don't leak
    # storage / credit on their side. Don't fail the local delete if remote
    # cleanup fails.
    remote_id = target.get("elevenlabs_voice_id")
    if remote_id and settings.elevenlabs_enabled:
        from app.elevenlabs_client import delete_remote_voice
        try:
            await delete_remote_voice(remote_id)
        except Exception as e:
            print(f"[voice] remote ElevenLabs delete failed for {remote_id}: {e}")
