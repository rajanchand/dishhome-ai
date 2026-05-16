"""High-level persistence helpers for Supabase.

When Supabase is configured, login events + audit log entries get persisted
across restarts and become readable from any process — not just this one's
memory.

Design:
  • In-memory rings (security.py) stay as the fast path AND as a fallback
    when the DB call fails. Every successful write also lands in Supabase.
  • Reads prefer Supabase when enabled; if it errors we fall back to the
    in-memory data so the monitoring page never goes blank.
  • Functions are async and meant to be awaited by async endpoints; we don't
    fire-and-forget because that interacts badly with FastAPI's sync-worker
    threads.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.config import settings
from app.supabase_client import (
    SupabaseError,
    insert as sb_insert,
    select as sb_select,
)

log = logging.getLogger("dishhome.db_repo")


def _utc_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _from_iso(s: str) -> float:
    # Supabase returns ISO 8601; we expose Unix timestamps (matches the
    # in-memory shape). Trailing 'Z' is accepted.
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def _safe_ip(ip: str) -> str | None:
    """Coerce empty string to None so the inet column doesn't barf on insert."""
    return ip or None


# ─────────────────────────────────────────────────────────────
# Writes — best-effort. Never raise into the caller.
# ─────────────────────────────────────────────────────────────

async def persist_login_event(event: dict) -> None:
    if not settings.supabase_enabled:
        return
    row = {
        "at": _utc_iso(event["at"]),
        "username": event["username"],
        "ip": _safe_ip(event.get("ip", "")),
        "user_agent": event.get("user_agent", "") or "",
        "device": event.get("device", "") or "",
        "result": event["result"],
        "reason": event.get("reason", "") or "",
        "session_prefix": event.get("session_prefix", "") or "",
    }
    try:
        await sb_insert("login_events", row)
    except SupabaseError as e:
        log.warning("login_events persist failed: %s", e)
    except Exception as e:  # pragma: no cover - defensive
        log.warning("login_events unexpected error: %s", e)


async def persist_audit(entry: dict) -> None:
    if not settings.supabase_enabled:
        return
    row = {
        "at": _utc_iso(entry["at"]),
        "actor": entry["actor"],
        "action": entry["action"],
        "target": entry.get("target", "") or "",
        "detail": entry.get("detail", "") or "",
    }
    try:
        await sb_insert("audit_log", row)
    except SupabaseError as e:
        log.warning("audit_log persist failed: %s", e)
    except Exception as e:  # pragma: no cover
        log.warning("audit_log unexpected error: %s", e)


# ─────────────────────────────────────────────────────────────
# Reads — return None on error so the caller can fall back to memory.
# ─────────────────────────────────────────────────────────────

async def fetch_login_events(limit: int = 200) -> list[dict] | None:
    if not settings.supabase_enabled:
        return None
    try:
        rows = await sb_select(
            "login_events",
            order="at.desc",
            limit=max(1, min(limit, 500)),
        )
    except SupabaseError as e:
        log.warning("fetch_login_events failed: %s", e)
        return None
    except Exception as e:  # pragma: no cover
        log.warning("fetch_login_events unexpected error: %s", e)
        return None
    return [
        {
            "at": _from_iso(r["at"]),
            "username": r["username"],
            "ip": r.get("ip") or "",
            "user_agent": r.get("user_agent") or "",
            "device": r.get("device") or "",
            "result": r["result"],
            "reason": r.get("reason") or "",
            "session_prefix": r.get("session_prefix") or "",
        }
        for r in rows
    ]


async def fetch_audit_entries(limit: int = 100) -> list[dict] | None:
    if not settings.supabase_enabled:
        return None
    try:
        rows = await sb_select(
            "audit_log",
            order="at.desc",
            limit=max(1, min(limit, 500)),
        )
    except SupabaseError as e:
        log.warning("fetch_audit_entries failed: %s", e)
        return None
    except Exception as e:  # pragma: no cover
        log.warning("fetch_audit_entries unexpected error: %s", e)
        return None
    return [
        {
            "at": _from_iso(r["at"]),
            "actor": r["actor"],
            "action": r["action"],
            "target": r.get("target") or "",
            "detail": r.get("detail") or "",
        }
        for r in rows
    ]


async def row_count(table: str) -> int | None:
    if not settings.supabase_enabled:
        return None
    try:
        import httpx
        url = f"{settings.supabase_url.rstrip('/')}/rest/v1/{table}"
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.get(
                url,
                params={"select": "id"},
                headers={
                    "apikey": settings.supabase_service_role_key,
                    "authorization": f"Bearer {settings.supabase_service_role_key}",
                    "accept-profile": settings.supabase_schema,
                    "prefer": "count=exact",
                    "range-unit": "items",
                    "range": "0-0",
                },
            )
        cr = r.headers.get("content-range", "")
        if "/" in cr:
            total = cr.split("/", 1)[1]
            if total.isdigit():
                return int(total)
    except Exception:
        return None
    return None


__all__ = [
    "persist_login_event",
    "persist_audit",
    "fetch_login_events",
    "fetch_audit_entries",
    "row_count",
]
