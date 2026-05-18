"""Thin async ElevenLabs client.

Avoids the official SDK so we don't pull a heavy dependency for two endpoints.
The API key is resolved per call from the runtime-config override cache,
falling back to the env value. Callers should gate on
`elevenlabs_enabled()` (also defined here) rather than touching `settings`
directly so DB overrides win.
"""

from __future__ import annotations

import httpx

from app.config import settings

_BASE = "https://api.elevenlabs.io/v1"


class ElevenLabsError(Exception):
    pass


def _resolved_key() -> str:
    """Cached override (if any) wins over the env var."""
    # Local import to avoid a circular import at module load.
    from app.services.runtime_config import _cache_get
    cache = _cache_get() or {}
    return cache.get("elevenlabs_api_key") or (settings.elevenlabs_api_key or "")


def elevenlabs_enabled() -> bool:
    return bool(_resolved_key())


def _client() -> httpx.AsyncClient:
    key = _resolved_key()
    if not key:
        raise ElevenLabsError(
            "ElevenLabs API key is not configured — set it in Settings or as ELEVENLABS_API_KEY."
        )
    return httpx.AsyncClient(
        base_url=_BASE,
        headers={"xi-api-key": key},
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
        try:
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
        except httpx.RequestError as e:
            raise ElevenLabsError(f"Network error communicating with ElevenLabs: {e}") from e


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
        try:
            resp = await c.post("/voices/add", data=data, files=files)
            if resp.status_code >= 300:
                raise ElevenLabsError(
                    f"ElevenLabs voice clone failed [{resp.status_code}]: {resp.text[:400]}"
                )
            body = resp.json()
            if "voice_id" not in body:
                raise ElevenLabsError(f"ElevenLabs response missing voice_id: {body}")
            return body["voice_id"]
        except httpx.RequestError as e:
            raise ElevenLabsError(f"Network error communicating with ElevenLabs: {e}") from e


async def delete_remote_voice(voice_id: str) -> None:
    async with _client() as c:
        try:
            resp = await c.delete(f"/voices/{voice_id}")
            if resp.status_code >= 300 and resp.status_code != 404:
                raise ElevenLabsError(
                    f"ElevenLabs delete failed [{resp.status_code}]: {resp.text[:200]}"
                )
        except httpx.RequestError as e:
            raise ElevenLabsError(f"Network error communicating with ElevenLabs: {e}") from e


async def list_remote_voices() -> list[dict]:
    async with _client() as c:
        try:
            resp = await c.get("/voices")
            if resp.status_code >= 300:
                raise ElevenLabsError(
                    f"ElevenLabs list failed [{resp.status_code}]: {resp.text[:200]}"
                )
            return resp.json().get("voices", [])
        except httpx.RequestError as e:
            raise ElevenLabsError(f"Network error communicating with ElevenLabs: {e}") from e
