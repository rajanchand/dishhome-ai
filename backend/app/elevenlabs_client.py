"""Thin async ElevenLabs client.

Avoids the official SDK so we don't pull a heavy dependency for two endpoints.
All calls are no-ops if `settings.elevenlabs_api_key` is empty — callers should
gate on `settings.elevenlabs_enabled` first.
"""

from __future__ import annotations

import httpx

from app.config import settings

_BASE = "https://api.elevenlabs.io/v1"


class ElevenLabsError(Exception):
    pass


def _client() -> httpx.AsyncClient:
    if not settings.elevenlabs_enabled:
        raise ElevenLabsError(
            "ELEVENLABS_API_KEY is not configured — set it in backend/.env"
        )
    return httpx.AsyncClient(
        base_url=_BASE,
        headers={"xi-api-key": settings.elevenlabs_api_key},
        timeout=httpx.Timeout(60.0, connect=10.0),
    )


async def synthesize(
    *,
    voice_id: str,
    text: str,
    model_id: str | None = None,
    output_format: str = "mp3_44100_128",
) -> bytes:
    """Return raw MP3 bytes. Raises ElevenLabsError on non-2xx."""
    async with _client() as c:
        resp = await c.post(
            f"/text-to-speech/{voice_id}",
            params={"output_format": output_format},
            json={
                "text": text,
                "model_id": model_id or settings.elevenlabs_model_id,
            },
        )
        if resp.status_code >= 300:
            raise ElevenLabsError(
                f"ElevenLabs TTS failed [{resp.status_code}]: {resp.text[:300]}"
            )
        return resp.content


async def clone_voice(
    *,
    name: str,
    description: str,
    sample_filename: str,
    sample_bytes: bytes,
    sample_mime: str,
) -> str:
    """Create an Instant Voice Clone. Returns the new ElevenLabs voice_id."""
    async with _client() as c:
        files = {"files": (sample_filename, sample_bytes, sample_mime)}
        data = {"name": name, "description": description}
        resp = await c.post("/voices/add", data=data, files=files)
        if resp.status_code >= 300:
            raise ElevenLabsError(
                f"ElevenLabs voice clone failed [{resp.status_code}]: {resp.text[:400]}"
            )
        body = resp.json()
        if "voice_id" not in body:
            raise ElevenLabsError(f"ElevenLabs response missing voice_id: {body}")
        return body["voice_id"]


async def delete_remote_voice(voice_id: str) -> None:
    async with _client() as c:
        resp = await c.delete(f"/voices/{voice_id}")
        if resp.status_code >= 300 and resp.status_code != 404:
            raise ElevenLabsError(
                f"ElevenLabs delete failed [{resp.status_code}]: {resp.text[:200]}"
            )


async def list_remote_voices() -> list[dict]:
    async with _client() as c:
        resp = await c.get("/voices")
        if resp.status_code >= 300:
            raise ElevenLabsError(
                f"ElevenLabs list failed [{resp.status_code}]: {resp.text[:200]}"
            )
        return resp.json().get("voices", [])
