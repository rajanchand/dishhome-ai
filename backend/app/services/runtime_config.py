"""Runtime configuration overrides backed by the database.

The `settings` object (Pydantic) is fixed at process startup from env vars.
This service lets `super_admin` operators paste credentials in the Settings
UI and have them take effect on the next request, without redeploying.

Precedence
----------
1. DB row with a non-empty value  → wins
2. Env var (`settings.<attr>`)    → fallback
3. ""                             → unset

Only the keys in `SUPPORTED_KEYS` are writable. Bootstrap secrets
(APP_SECRET_KEY, DATABASE_URL, Supabase keys) are *not* in the list —
they must come from the platform, and we never echo them through this
layer.

Caching
-------
The full override map is cached process-locally for `_TTL_SECONDS` to
keep request hot-path latency flat. `PUT /admin/runtime-config` flushes
the cache so the next read sees the new value immediately.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.system_config import SystemConfigEntry


# ── Whitelist ────────────────────────────────────────────────────────
@dataclass(frozen=True)
class KeySpec:
    label: str
    is_secret: bool


SUPPORTED_KEYS: dict[str, KeySpec] = {
    # Telephony — SIP softphone
    "sip_ws_server":              KeySpec("SIP WebSocket URL",       False),
    "sip_domain":                 KeySpec("SIP domain",              False),
    "sip_passwords_json":         KeySpec("SIP passwords (JSON)",    True),
    # Telephony — Twilio
    "twilio_account_sid":         KeySpec("Twilio Account SID",      False),
    "twilio_auth_token":          KeySpec("Twilio auth token",       True),
    "twilio_from_number":         KeySpec("Twilio from number",      False),
    "public_base_url":            KeySpec("Public base URL",         False),
    # Voice — ElevenLabs
    "elevenlabs_api_key":         KeySpec("ElevenLabs API key",      True),
    "elevenlabs_voice_ne_female": KeySpec("ElevenLabs voice (ne/female)", False),
    "elevenlabs_voice_ne_male":   KeySpec("ElevenLabs voice (ne/male)",   False),
    "elevenlabs_voice_en_female": KeySpec("ElevenLabs voice (en/female)", False),
    "elevenlabs_voice_en_male":   KeySpec("ElevenLabs voice (en/male)",   False),
    # AI — Ollama
    "ollama_host":                KeySpec("Ollama host",             False),
    "ollama_model":               KeySpec("Ollama model",            False),
    # Observability
    "sentry_dsn":                 KeySpec("Sentry DSN",              True),
}

SECRET_MASK = "•••••• (set)"


# ── Cache ────────────────────────────────────────────────────────────
_TTL_SECONDS = 30.0
_cache: dict[str, str] | None = None
_cache_at: float = 0.0
_cache_lock = Lock()


def _cache_get() -> dict[str, str] | None:
    with _cache_lock:
        if _cache is None or (time.monotonic() - _cache_at) > _TTL_SECONDS:
            return None
        return dict(_cache)


def _cache_set(rows: dict[str, str]) -> None:
    global _cache, _cache_at
    with _cache_lock:
        _cache = dict(rows)
        _cache_at = time.monotonic()


def invalidate_cache() -> None:
    global _cache, _cache_at
    with _cache_lock:
        _cache = None
        _cache_at = 0.0


# ── Reads ────────────────────────────────────────────────────────────
async def get_overrides(db: AsyncSession) -> dict[str, str]:
    """Return {key: value} for every non-empty row. Cached."""
    cached = _cache_get()
    if cached is not None:
        return cached
    result = await db.execute(select(SystemConfigEntry))
    rows = {r.key: r.value for r in result.scalars().all() if r.value}
    _cache_set(rows)
    return rows


async def get_effective(db: AsyncSession, key: str) -> str:
    """Return the effective value: DB override if set, else env."""
    if key not in SUPPORTED_KEYS:
        raise KeyError(f"runtime_config: unsupported key {key!r}")
    overrides = await get_overrides(db)
    if overrides.get(key):
        return overrides[key]
    return str(getattr(settings, key, "") or "")


# ── Writes ───────────────────────────────────────────────────────────
async def set_overrides(
    db: AsyncSession, updates: Iterable[tuple[str, str]], actor: str
) -> list[str]:
    """Upsert each (key, value). Empty value clears the override.

    Returns the list of keys actually changed (for audit).
    """
    from app.security import audit  # local import to avoid cycle at module load

    # Validate first so partial writes don't happen.
    changes: list[tuple[str, str, bool]] = []
    for key, value in updates:
        if key not in SUPPORTED_KEYS:
            raise ValueError(f"unsupported key {key!r}")
        spec = SUPPORTED_KEYS[key]
        changes.append((key, value, spec.is_secret))

    changed_keys: list[str] = []
    for key, value, is_secret in changes:
        stmt = (
            pg_insert(SystemConfigEntry)
            .values(key=key, value=value, is_secret=is_secret, updated_by=actor)
            .on_conflict_do_update(
                index_elements=[SystemConfigEntry.key],
                set_={"value": value, "is_secret": is_secret, "updated_by": actor},
            )
        )
        await db.execute(stmt)
        changed_keys.append(key)
        audit(
            actor=actor,
            action="config.set",
            target=key,
            detail="(masked)" if is_secret else (value or "<cleared>"),
        )

    await db.commit()
    # Repopulate the cache from the just-committed state so subsequent reads
    # (including sync helpers like elevenlabs_client._resolved_key) see the
    # new values immediately, not after the next 30s refresh.
    invalidate_cache()
    await get_overrides(db)
    return changed_keys


# ── Helpers ──────────────────────────────────────────────────────────
def mask(value: str, is_secret: bool) -> str:
    if not value:
        return ""
    if is_secret:
        return SECRET_MASK
    return value


def sip_password_for(passwords_json: str, username: str) -> str:
    """Decode the JSON map and return the password for `username`, or ""."""
    import json
    if not (passwords_json or "").strip():
        return ""
    try:
        data = json.loads(passwords_json)
    except json.JSONDecodeError:
        return ""
    value = data.get(username) if isinstance(data, dict) else None
    return value if isinstance(value, str) else ""
