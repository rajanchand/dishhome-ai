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
import logging
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Literal
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_session
from app.routers.auth import UserOut, current_user, require_permission
from app.services.runtime_config import get_effective, sip_password_for

E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")

router = APIRouter(prefix="/telephony", tags=["telephony"])
log = logging.getLogger("dishhome.telephony")


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


@dataclass
class _TwilioCreds:
    account_sid: str
    auth_token: str
    from_number: str


async def _resolve_twilio(db: AsyncSession) -> _TwilioCreds:
    """Pull Twilio creds via the runtime-config override layer (DB > env)."""
    account_sid = await get_effective(db, "twilio_account_sid")
    auth_token = await get_effective(db, "twilio_auth_token")
    from_number = await get_effective(db, "twilio_from_number")
    missing = [
        k for k, v in [
            ("TWILIO_ACCOUNT_SID", account_sid),
            ("TWILIO_AUTH_TOKEN", auth_token),
            ("TWILIO_FROM_NUMBER", from_number),
        ] if not v
    ]
    if missing:
        raise HTTPException(
            503,
            f"Twilio not configured — missing: {', '.join(missing)}. "
            "Provision via Settings (Vercel env vars also accepted).",
        )
    return _TwilioCreds(account_sid=account_sid, auth_token=auth_token, from_number=from_number)


def _twilio_api_url(account_sid: str, path: str) -> str:
    return f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}{path}"


async def _resolve_public_url(db: AsyncSession) -> str:
    base = (await get_effective(db, "public_base_url")).strip().rstrip("/")
    if not base:
        raise HTTPException(
            503,
            "PUBLIC_BASE_URL is not set. Add it in Settings or as an env var so "
            "Twilio can reach the TwiML endpoint.",
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
        "sip_enabled": settings.sip_enabled,
    }


class SipCredentials(BaseModel):
    ws_server: str
    sip_uri: str
    password: str
    display_name: str


@router.get("/sip-credentials", response_model=SipCredentials)
async def sip_credentials(
    user: Annotated[UserOut, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SipCredentials:
    """Return SIP softphone credentials for the authenticated agent.

    Reads from the runtime-config override layer (DB > env). Without a
    configured server / domain / per-user password we return 503 so the
    browser softphone can show a clear error instead of faking a
    "Registered" state.
    """
    ws_server = await get_effective(db, "sip_ws_server")
    sip_domain = await get_effective(db, "sip_domain")
    if not (ws_server and sip_domain):
        raise HTTPException(
            503,
            "SIP softphone not configured. Set sip_ws_server + sip_domain in "
            "the Settings page (super_admin) or as env vars.",
        )
    passwords_json = await get_effective(db, "sip_passwords_json")
    password = sip_password_for(passwords_json, user.username)
    if not password:
        raise HTTPException(
            503,
            f"No SIP password provisioned for {user.username!r}. "
            "Add the user to sip_passwords_json (JSON object).",
        )
    return SipCredentials(
        ws_server=ws_server,
        sip_uri=f"sip:{user.username}@{sip_domain}",
        password=password,
        display_name=user.full_name or user.username,
    )


@router.post("/originate", response_model=CallSession)
async def originate(
    payload: OriginateRequest,
    user: Annotated[UserOut, Depends(require_permission("telephony.originate"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CallSession:
    twilio = await _resolve_twilio(db)
    base = await _resolve_public_url(db)
    eleven_key = await get_effective(db, "elevenlabs_api_key")

    session_id = _new_session_id()
    now = datetime.now(timezone.utc).isoformat()

    audio_url: str | None = None
    from app.routers.voice import resolve_voice  # local import to avoid cycle

    voice = resolve_voice(voice_id=payload.voice_id, language=payload.language)
    if not voice:
        raise HTTPException(404, f"Voice {payload.voice_id!r} not found")
    resolved_voice_id = voice["id"]
    eleven_id = voice.get("elevenlabs_voice_id")
    if eleven_key and eleven_id:
        try:
            from app.routers.voice import synthesize_to_cache
            await synthesize_to_cache(eleven_id, payload.text)
            qs = urlencode({"voice_id": resolved_voice_id, "text": payload.text, "token": session_id})
            audio_url = f"{base}/voice/tts/public?{qs}"
        except Exception as e:  # pragma: no cover - graceful fallback
            audio_url = None
            log.warning("Pre-synthesis failed, falling back to Twilio Say: %s", e)

    twiml_url = f"{base}/telephony/twiml/{session_id}"
    status_cb = f"{base}/telephony/status/{session_id}"

    sess = {
        "session_id": session_id,
        "call_sid": None,
        "to": payload.to,
        "from_": twilio.from_number,
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
        "_audio_url": audio_url,
        "_user": user.username,
    }
    SESSIONS[session_id] = sess

    form = {
        "To": payload.to,
        "From": twilio.from_number,
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
                _twilio_api_url(twilio.account_sid, "/Calls.json"),
                data=form,
                auth=(twilio.account_sid, twilio.auth_token),
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

async def _verify_twilio_signature(
    request: Request,
    db: AsyncSession,
    form_params: dict[str, str] | None = None,
) -> None:
    """Validate Twilio's X-Twilio-Signature header.

    https://www.twilio.com/docs/usage/security#validating-requests
    Signature = HMAC-SHA1(url + sorted concatenated form params) keyed by
    the account auth_token, base64-encoded. Auth token is read via the
    runtime-config override layer so a DB-set value matches outbound calls.
    """
    if not settings.twilio_validate_signatures:
        return
    auth_token = await get_effective(db, "twilio_auth_token")
    if not auth_token:
        raise HTTPException(503, "Cannot validate Twilio signature: twilio_auth_token unset")
    sig = request.headers.get("x-twilio-signature", "")
    if not sig:
        raise HTTPException(401, "Missing X-Twilio-Signature")
    public_base = (await get_effective(db, "public_base_url")).rstrip("/")
    path = request.url.path
    query = ("?" + request.url.query) if request.url.query else ""
    base = public_base or str(request.base_url).rstrip("/")
    full_url = f"{base}{path}{query}"
    payload = full_url
    if form_params:
        for k in sorted(form_params.keys()):
            payload += k + form_params[k]
    mac = hmac.new(auth_token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1)
    expected = base64.b64encode(mac.digest()).decode("ascii")
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(401, "Twilio signature mismatch")


@router.get("/twiml/{session_id}")
async def twiml(
    session_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    """TwiML Twilio fetches when the call is answered."""
    await _verify_twilio_signature(request, db)
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
async def status_callback(
    session_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    """Twilio status webhook. Updates the session record."""
    if not re.match(r"^sess_[A-Za-z0-9_-]{8,32}$", session_id):
        raise HTTPException(400, "Bad session_id")
    form = await request.form()
    form_params = {k: str(v) for k, v in form.multi_items()}
    await _verify_twilio_signature(request, db, form_params=form_params)
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

