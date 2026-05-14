"""Thin async Supabase client over PostgREST.

We don't use the official `supabase-py` SDK because it pulls in a heavy
dependency tree and doesn't add much over the REST surface. Every operation
here is one HTTP call with explicit semantics:

  - Auth: service_role JWT (bypasses Row Level Security) for server-side ops.
    For end-user-scoped queries you'd swap in a per-user JWT instead.
  - URL shape: {SUPABASE_URL}/rest/v1/{table}?{filters}
  - Filters use PostgREST operators: eq.value, in.(a,b), order=col.desc, …

All methods raise SupabaseError on non-2xx; callers should let that bubble
up to FastAPI's HTTPException handler (which will return a 502/503).

Only call these helpers when settings.supabase_enabled is True.
"""

from __future__ import annotations

from typing import Any, Iterable

import httpx

from app.config import settings


class SupabaseError(Exception):
    pass


def _require() -> None:
    if not settings.supabase_enabled:
        raise SupabaseError(
            "Supabase is not configured — set SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY in backend/.env"
        )


def _headers(*, prefer: str | None = None) -> dict[str, str]:
    h = {
        "apikey": settings.supabase_service_role_key,
        "authorization": f"Bearer {settings.supabase_service_role_key}",
        "content-type": "application/json",
        "accept-profile": settings.supabase_schema,
        "content-profile": settings.supabase_schema,
    }
    if prefer:
        h["prefer"] = prefer
    return h


def _base() -> str:
    return f"{settings.supabase_url.rstrip('/')}/rest/v1"


async def select(
    table: str,
    *,
    columns: str = "*",
    filters: dict[str, str] | None = None,
    order: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[dict]:
    """Generic GET — `filters` values are PostgREST operators (eq.foo, gte.1)."""
    _require()
    params: dict[str, Any] = {"select": columns}
    if filters:
        params.update(filters)
    if order:
        params["order"] = order
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get(f"{_base()}/{table}", params=params, headers=_headers())
    if r.status_code >= 300:
        raise SupabaseError(f"select {table} → {r.status_code}: {r.text[:300]}")
    return r.json()


async def insert(table: str, row: dict | list[dict]) -> list[dict]:
    """Insert one or many rows. Returns the inserted rows (Prefer: return=representation)."""
    _require()
    body = row if isinstance(row, list) else [row]
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.post(
            f"{_base()}/{table}",
            json=body,
            headers=_headers(prefer="return=representation"),
        )
    if r.status_code >= 300:
        raise SupabaseError(f"insert {table} → {r.status_code}: {r.text[:300]}")
    return r.json()


async def upsert(
    table: str,
    row: dict | list[dict],
    *,
    on_conflict: str,
) -> list[dict]:
    _require()
    body = row if isinstance(row, list) else [row]
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.post(
            f"{_base()}/{table}",
            params={"on_conflict": on_conflict},
            json=body,
            headers=_headers(prefer="return=representation,resolution=merge-duplicates"),
        )
    if r.status_code >= 300:
        raise SupabaseError(f"upsert {table} → {r.status_code}: {r.text[:300]}")
    return r.json()


async def update(
    table: str,
    patch: dict,
    *,
    filters: dict[str, str],
) -> list[dict]:
    _require()
    if not filters:
        raise SupabaseError("update requires filters — refusing unbounded UPDATE")
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.patch(
            f"{_base()}/{table}",
            params=filters,
            json=patch,
            headers=_headers(prefer="return=representation"),
        )
    if r.status_code >= 300:
        raise SupabaseError(f"update {table} → {r.status_code}: {r.text[:300]}")
    return r.json()


async def delete(table: str, *, filters: dict[str, str]) -> list[dict]:
    _require()
    if not filters:
        raise SupabaseError("delete requires filters — refusing unbounded DELETE")
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.delete(
            f"{_base()}/{table}",
            params=filters,
            headers=_headers(prefer="return=representation"),
        )
    if r.status_code >= 300:
        raise SupabaseError(f"delete {table} → {r.status_code}: {r.text[:300]}")
    return r.json()


async def rpc(name: str, params: dict | None = None) -> Any:
    _require()
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.post(
            f"{_base()}/rpc/{name}",
            json=params or {},
            headers=_headers(),
        )
    if r.status_code >= 300:
        raise SupabaseError(f"rpc {name} → {r.status_code}: {r.text[:300]}")
    return r.json()


async def health() -> dict:
    """Cheap reachability check. Hits the schema introspection endpoint."""
    _require()
    async with httpx.AsyncClient(timeout=10.0) as c:
        # GET /rest/v1/ returns the OpenAPI document of the exposed schema —
        # confirms credentials work and the schema is reachable.
        r = await c.get(_base() + "/", headers=_headers())
    return {
        "ok": r.status_code < 300,
        "status_code": r.status_code,
        "schema": settings.supabase_schema,
        "url": settings.supabase_url,
    }


async def table_exists(table: str) -> bool:
    """Returns True iff a SELECT … LIMIT 0 on the table succeeds."""
    _require()
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get(
            f"{_base()}/{table}",
            params={"select": "*", "limit": 0},
            headers=_headers(),
        )
    return r.status_code < 300


async def required_tables_present(tables: Iterable[str]) -> dict[str, bool]:
    return {t: await table_exists(t) for t in tables}
