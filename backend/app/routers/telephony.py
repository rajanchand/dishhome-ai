"""Twilio outbound calling.

Flow:
  1. Client POSTs /telephony/originate {to, voice_id, text, language}
  2. We pre-synthesize the audio via ElevenLabs (or fall back to <Say>) and
     create a Twilio Call. Twilio's `url` parameter points at /telephony/twiml/{sid}.
  3. Twilio dials, fetches TwiML, plays the audio, posts status callbacks to
     /telephony/status which mutate the in-memory session record.
  4. The UI polls /telephony/sessions/{sid} for live status.

Without TWILIO_* env vars set, /originate returns 503. Without ELEVENLABS_*
the call still works — Twilio just uses its built-in <Say> voice.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timezone
from typing import Annotated, Literal
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from app.config import settings
from app.routers.auth import UserOut, current_user, require_permission

E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")

router = APIRouter(prefix="/telephony", tags=["telephony"])


class OriginateRequest(BaseModel):
    to: str = Field(min_length=8, max_length=20, description="E.164 number, e.g. +447570731478")
    voice_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.-]+$")
    text: str = Field(min_length=1, max_length=600)
    language: Literal["ne", "en"] = "ne"
    record: bool = False
    campaign_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_.-]*$")

    @field_validator("to")
    @classmethod
    def _e164(cls, v: str) -> str:
        v = v.strip().replace(" ", "").replace("-", "")
        if not E164_RE.match(v):
            raise ValueError("number must be E.164, e.g. +447570731478")
        return v


class CallSession(BaseModel):
    session_id: str
    call_sid: str | None
    to: str
    from_: str
    voice_id: str
    language: str
    text: str
    status: str
    error: str | None = None
    created_at: str
    started_at: str | None = None
    ended_at: str | None = None
    duration_sec: int | None = None
    campaign_id: str | None = None
    recording_url: str | None = None


SESSIONS: dict[str, dict] = {}


def _twilio_api_url(path: str) -> str:
    return f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}{path}"


def _require_twilio() -> None:
    if not settings.twilio_enabled:
        missing = [
            v for v, ok in [
                ("TWILIO_ACCOUNT_SID", bool(settings.twilio_account_sid)),
                ("TWILIO_AUTH_TOKEN", bool(settings.twilio_auth_token)),
                ("TWILIO_FROM_NUMBER", bool(settings.twilio_from_number)),
            ] if not ok
        ]
        raise HTTPException(
            503,
            f"Twilio not configured — missing env: {', '.join(missing)}. "
            "Add them to backend/.env and restart.",
        )


def _require_public_url() -> str:
    base = settings.public_base_url.strip().rstrip("/")
    if not base:
        raise HTTPException(
            503,
            "PUBLIC_BASE_URL is not set. Start ngrok (`ngrok http 8000`) and put the "
            "public https URL in backend/.env so Twilio can fetch TwiML.",
        )
    return base


def _new_session_id() -> str:
    return f"sess_{secrets.token_urlsafe(12)}"


@router.get("/health")
def health(_: Annotated[UserOut, Depends(current_user)]) -> dict:
    return {
        "twilio_enabled": settings.twilio_enabled,
        "from_number": settings.twilio_from_number or None,
        "public_base_url": settings.public_base_url or None,
        "elevenlabs_enabled": settings.elevenlabs_enabled,
    }


@router.post("/originate", response_model=CallSession)
async def originate(
    payload: OriginateRequest,
    user: Annotated[UserOut, Depends(require_permission("telephony.originate"))],
) -> CallSession:
    _require_twilio()
    base = _require_public_url()

    session_id = _new_session_id()
    now = datetime.now(timezone.utc).isoformat()

    # Pre-synthesize audio if ElevenLabs is available, so the TwiML can <Play>.
    # (If not, the TwiML route will fall back to <Say>.)
    audio_url: str | None = None
    # Route through resolve_voice so a configured primary voice (e.g. an
    # uploaded "Rajan" clone) overrides whatever the campaign was saved with.
    from app.routers.voice import resolve_voice  # local import to avoid cycle

    voice = resolve_voice(voice_id=payload.voice_id, language=payload.language)
    if not voice:
        raise HTTPException(404, f"Voice {payload.voice_id!r} not found")
    resolved_voice_id = voice["id"]
    eleven_id = voice.get("elevenlabs_voice_id")
    if settings.elevenlabs_enabled and eleven_id:
        try:
            from app.routers.voice import synthesize_to_cache
            await synthesize_to_cache(eleven_id, payload.text)
            qs = urlencode({"voice_id": resolved_voice_id, "text": payload.text, "token": session_id})
            audio_url = f"{base}/voice/tts/public?{qs}"
        except Exception as e:  # pragma: no cover - graceful fallback
            audio_url = None
            print(f"[telephony] pre-synth failed, falling back to <Say>: {e}")

    twiml_url = f"{base}/telephony/twiml/{session_id}"
    status_cb = f"{base}/telephony/status/{session_id}"

    sess = {
        "session_id": session_id,
        "call_sid": None,
        "to": payload.to,
        "from_": settings.twilio_from_number,
        # Store the *resolved* voice — that's the one we actually used for synth
        # and the one tts_public will be called against.
        "voice_id": resolved_voice_id,
        "language": payload.language,
        "text": payload.text,
        "status": "queued",
        "error": None,
        "created_at": now,
        "started_at": None,
        "ended_at": None,
        "duration_sec": None,
        "campaign_id": payload.campaign_id,
        "recording_url": None,
        # private fields:
        "_audio_url": audio_url,
        "_user": user.username,
    }
    SESSIONS[session_id] = sess

    # Place the call via Twilio REST API.
    form = {
        "To": payload.to,
        "From": settings.twilio_from_number,
        "Url": twiml_url,
        "Method": "GET",
        "StatusCallback": status_cb,
        "StatusCallbackMethod": "POST",
        "StatusCallbackEvent": ["initiated", "ringing", "answered", "completed"],
    }
    if payload.record:
        form["Record"] = "true"

    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            resp = await c.post(
                _twilio_api_url("/Calls.json"),
                data=form,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            )
    except httpx.HTTPError as e:
        sess["status"] = "failed"
        sess["error"] = f"Network error talking to Twilio: {e}"
        raise HTTPException(502, sess["error"]) from e

    if resp.status_code >= 300:
        sess["status"] = "failed"
        sess["error"] = f"Twilio error [{resp.status_code}]: {resp.text[:300]}"
        raise HTTPException(502, sess["error"])

    body = resp.json()
    sess["call_sid"] = body.get("sid")
    sess["status"] = (body.get("status") or "queued").lower()
    return _to_public(sess)


def _to_public(sess: dict) -> CallSession:
    return CallSession(
        session_id=sess["session_id"],
        call_sid=sess.get("call_sid"),
        to=sess["to"],
        from_=sess["from_"],
        voice_id=sess["voice_id"],
        language=sess["language"],
        text=sess["text"],
        status=sess.get("status", "queued"),
        error=sess.get("error"),
        created_at=sess["created_at"],
        started_at=sess.get("started_at"),
        ended_at=sess.get("ended_at"),
        duration_sec=sess.get("duration_sec"),
        campaign_id=sess.get("campaign_id"),
        recording_url=sess.get("recording_url"),
    )


@router.get("/sessions", response_model=list[CallSession])
def list_sessions(
    _: Annotated[UserOut, Depends(require_permission("telephony.read"))],
) -> list[CallSession]:
    rows = sorted(SESSIONS.values(), key=lambda s: s["created_at"], reverse=True)
    return [_to_public(s) for s in rows[:100]]


@router.get("/sessions/{session_id}", response_model=CallSession)
def get_session(
    session_id: str,
    _: Annotated[UserOut, Depends(require_permission("telephony.read"))],
) -> CallSession:
    s = SESSIONS.get(session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    return _to_public(s)


# ---- public webhooks (Twilio calls these — gated by signature) ----

def _verify_twilio_signature(request: Request, form_params: dict[str, str] | None = None) -> None:
    """Validate Twilio's X-Twilio-Signature header.

    https://www.twilio.com/docs/usage/security#validating-requests
    The signature is HMAC-SHA1 of (url + sorted concatenated form params)
    keyed by the account auth_token, base64-encoded.

    Skips validation when twilio_validate_signatures is False (dev/test).
    """
    if not settings.twilio_validate_signatures:
        return
    if not settings.twilio_auth_token:
        # Without an auth token we have nothing to validate against — refuse.
        raise HTTPException(503, "Cannot validate Twilio signature: TWILIO_AUTH_TOKEN unset")
    sig = request.headers.get("x-twilio-signature", "")
    if not sig:
        raise HTTPException(401, "Missing X-Twilio-Signature")
    # Twilio signs the full URL Twilio used to reach us. If we're behind ngrok
    # or another proxy, PUBLIC_BASE_URL is the authoritative host.
    path = request.url.path
    query = ("?" + request.url.query) if request.url.query else ""
    base = settings.public_base_url.rstrip("/") if settings.public_base_url else str(request.base_url).rstrip("/")
    full_url = f"{base}{path}{query}"
    payload = full_url
    if form_params:
        for k in sorted(form_params.keys()):
            payload += k + form_params[k]
    mac = hmac.new(settings.twilio_auth_token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1)
    expected = base64.b64encode(mac.digest()).decode("ascii")
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(401, "Twilio signature mismatch")


@router.get("/twiml/{session_id}")
def twiml(session_id: str, request: Request) -> Response:
    """TwiML Twilio fetches when the call is answered."""
    _verify_twilio_signature(request)
    if not re.match(r"^sess_[A-Za-z0-9_-]{8,32}$", session_id):
        raise HTTPException(400, "Bad session_id")
    s = SESSIONS.get(session_id)
    if not s:
        return Response(
            content="<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response><Say>Session expired.</Say><Hangup/></Response>",
            media_type="application/xml",
        )
    audio_url = s.get("_audio_url")
    text = s.get("text", "")
    lang = s.get("language", "en")
    if audio_url:
        body = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            "<Response>"
            f"<Play>{_xml_escape(audio_url)}</Play>"
            "<Pause length=\"1\"/>"
            "<Hangup/>"
            "</Response>"
        )
    else:
        say_lang = "hi-IN" if lang == "ne" else "en-GB"
        body = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            "<Response>"
            f"<Say voice=\"Polly.Aditi\" language=\"{say_lang}\">{_xml_escape(text)}</Say>"
            "<Pause length=\"1\"/>"
            "<Hangup/>"
            "</Response>"
        )
    return Response(content=body, media_type="application/xml")


@router.post("/status/{session_id}")
async def status_callback(session_id: str, request: Request) -> Response:
    """Twilio status webhook. Updates the session record."""
    if not re.match(r"^sess_[A-Za-z0-9_-]{8,32}$", session_id):
        raise HTTPException(400, "Bad session_id")
    form = await request.form()
    form_params = {k: str(v) for k, v in form.multi_items()}
    _verify_twilio_signature(request, form_params=form_params)
    s = SESSIONS.get(session_id)
    if not s:
        return Response(status_code=204)
    call_status = (form.get("CallStatus") or "").lower()
    if call_status:
        s["status"] = call_status
    if call_status in ("in-progress", "answered"):
        s["started_at"] = s["started_at"] or datetime.now(timezone.utc).isoformat()
    if call_status in ("completed", "busy", "failed", "no-answer", "canceled"):
        s["ended_at"] = datetime.now(timezone.utc).isoformat()
        try:
            dur = form.get("CallDuration")
            if dur:
                s["duration_sec"] = int(dur)
        except (TypeError, ValueError):
            pass
    rec = form.get("RecordingUrl")
    if rec:
        s["recording_url"] = str(rec)
    return Response(status_code=204)


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


