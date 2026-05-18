"""Admin: user + role management.

All endpoints require the `users.manage` permission. Mutations are logged
to the audit ring (visible at /admin/audit-log).
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.config import settings
from app.database import get_db_session
from app.models.user import User, Session as UserSession
from app.rbac import ROLE_ORDER, ROLE_PERMISSIONS, permissions_for
from app.routers.auth import UserOut, current_user, require_permission
from app.security import (
    audit,
    audit_log,
    geo_for_ip,
    hash_password,
    login_events,
    parse_user_agent,
)
import time
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin", tags=["admin"])

# Literal type for role validation (Pydantic gives clean 422 error)
RoleLiteral = Literal["super_admin", "admin", "supervisor", "agent"]


class AdminUser(BaseModel):
    username: str
    name: str
    email: str
    role: str
    permissions: list[str]
    created_at: str | None = None
    created_by: str | None = None


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-z0-9_.-]+$")
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    role: RoleLiteral
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def _normalize_username(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        if v.isdigit() or v.isalpha():
            raise ValueError("password must mix letters and numbers")
        return v


class UpdateUserRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    email: EmailStr | None = None
    role: RoleLiteral | None = None


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        if v.isdigit() or v.isalpha():
            raise ValueError("password must mix letters and numbers")
        return v


class RoleOut(BaseModel):
    id: str
    name: str
    permissions: list[str]
    user_count: int


class AuditEntry(BaseModel):
    at: float
    actor: str
    action: str
    target: str
    detail: str = ""


# ── System config snapshot (read-only) ──
# Mirrors what the Settings page displays. Never includes secrets — only
# enabled flags, model names, and the non-sensitive identifiers an operator
# would put on a status board.
class _AIConfig(BaseModel):
    ollama_model: str
    ollama_host: str
    tts_engine: str
    elevenlabs_model_id: str | None


class _TelephonyConfig(BaseModel):
    sip_enabled: bool
    sip_ws_server: str | None
    sip_domain: str | None
    audiosocket_host: str
    audiosocket_port: int
    audio_server_enabled: bool
    twilio_enabled: bool
    twilio_from_number: str | None
    public_base_url: str | None


class _IntegrationsConfig(BaseModel):
    elevenlabs_configured: bool
    supabase_configured: bool
    sentry_configured: bool


class SystemConfig(BaseModel):
    app_env: str
    ai: _AIConfig
    telephony: _TelephonyConfig
    integrations: _IntegrationsConfig
    cors_origins: list[str]


@router.get("/system-config", response_model=SystemConfig)
def system_config(_: Annotated[UserOut, Depends(current_user)]) -> SystemConfig:
    """Snapshot of effective configuration for the Settings page.

    All values are derived from environment variables — the UI is purely
    informational, edits must happen via env / Vercel dashboard. Secrets
    (API keys, passwords, DB URLs) are never returned.
    """
    return SystemConfig(
        app_env=settings.app_env,
        ai=_AIConfig(
            ollama_model=settings.ollama_model,
            ollama_host=settings.ollama_host,
            tts_engine="ElevenLabs" if settings.elevenlabs_enabled else "Piper (local fallback)",
            elevenlabs_model_id=settings.elevenlabs_model_id if settings.elevenlabs_enabled else None,
        ),
        telephony=_TelephonyConfig(
            sip_enabled=settings.sip_enabled,
            sip_ws_server=settings.sip_ws_server or None,
            sip_domain=settings.sip_domain or None,
            audiosocket_host=settings.freeswitch_audiosocket_host,
            audiosocket_port=settings.freeswitch_audiosocket_port,
            audio_server_enabled=settings.enable_audio_server,
            twilio_enabled=settings.twilio_enabled,
            twilio_from_number=settings.twilio_from_number or None,
            public_base_url=settings.public_base_url or None,
        ),
        integrations=_IntegrationsConfig(
            elevenlabs_configured=settings.elevenlabs_enabled,
            supabase_configured=settings.supabase_enabled,
            sentry_configured=bool(settings.sentry_dsn),
        ),
        cors_origins=settings.cors_origins_list,
    )


def _to_admin_user(u: User) -> AdminUser:
    return AdminUser(
        username=u.username,
        name=u.full_name,
        email=u.email,
        role=u.role,
        permissions=permissions_for(u.role),
        created_at=u.created_at.isoformat() if u.created_at else None,
        created_by=None, # In production, link to creator
    )


def _can_target(actor: UserOut, target_role: str) -> None:
    """Admins can manage anyone except other super_admins; super_admins manage all."""
    if actor.role == "super_admin":
        return
    if target_role == "super_admin":
        raise HTTPException(403, "Only super_admin can manage super_admin users")


@router.get("/users", response_model=list[AdminUser])
async def list_users(
    _: Annotated[UserOut, Depends(require_permission("users.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[AdminUser]:
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [_to_admin_user(u) for u in users]


@router.post("/users", response_model=AdminUser, status_code=201)
async def create_user(
    payload: CreateUserRequest,
    actor: Annotated[UserOut, Depends(require_permission("users.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminUser:
    _can_target(actor, payload.role)
    uname = payload.username
    
    result = await db.execute(select(User).where(User.username == uname))
    if result.scalar_one_or_none():
        raise HTTPException(409, f"User {uname!r} already exists")
    
    new_user = User(
        username=uname,
        email=str(payload.email),
        full_name=payload.name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    audit(actor=actor.username, action="user.create", target=uname, detail=f"role={payload.role}")
    return _to_admin_user(new_user)


@router.patch("/users/{username}", response_model=AdminUser)
async def update_user(
    username: str,
    payload: UpdateUserRequest,
    actor: Annotated[UserOut, Depends(require_permission("users.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminUser:
    uname = username.strip().lower()
    result = await db.execute(select(User).where(User.username == uname))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(404, "User not found")
    _can_target(actor, u.role)
    
    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    changed: list[str] = []
    
    if "role" in update_data and update_data["role"] != u.role:
        new_role = update_data["role"]
        _can_target(actor, new_role)
        # Last super admin check
        if u.role == "super_admin" and new_role != "super_admin":
            res = await db.execute(select(User).where(User.role == "super_admin", User.username != u.username))
            if not res.scalars().first():
                raise HTTPException(409, "Cannot remove the last super_admin")
        u.role = new_role
        # Revoke sessions
        await db.execute(delete(UserSession).where(UserSession.username == u.username))
        changed.append(f"role={new_role}")
        
    if "name" in update_data:
        u.full_name = update_data["name"].strip()
        changed.append("name")
    if "email" in update_data:
        u.email = str(update_data["email"])
        changed.append("email")
        
    if changed:
        await db.commit()
        await db.refresh(u)
        audit(actor=actor.username, action="user.update", target=u.username, detail=",".join(changed))
    
    return _to_admin_user(u)


@router.delete("/users/{username}", status_code=204)
async def delete_user(
    username: str,
    actor: Annotated[UserOut, Depends(require_permission("users.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    uname = username.strip().lower()
    result = await db.execute(select(User).where(User.username == uname))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(404, "User not found")
    if uname == actor.username:
        raise HTTPException(409, "You cannot delete yourself")
    _can_target(actor, u.role)
    
    if u.role == "super_admin":
        res = await db.execute(select(User).where(User.role == "super_admin", User.username != u.username))
        if not res.scalars().first():
            raise HTTPException(409, "Cannot delete the last super_admin")
            
    await db.delete(u)
    await db.execute(delete(UserSession).where(UserSession.username == uname))
    await db.commit()
    audit(actor=actor.username, action="user.delete", target=uname)


@router.post("/users/{username}/reset-password")
async def reset_password(
    username: str,
    payload: ResetPasswordRequest,
    actor: Annotated[UserOut, Depends(require_permission("users.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, int | str]:
    uname = username.strip().lower()
    result = await db.execute(select(User).where(User.username == uname))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(404, "User not found")
    _can_target(actor, u.role)
    
    u.password_hash = hash_password(payload.new_password)
    # Revoke sessions
    res = await db.execute(delete(UserSession).where(UserSession.username == u.username))
    revoked = res.rowcount
    await db.commit()
    
    audit(actor=actor.username, action="user.reset_password", target=u.username, detail=f"revoked={revoked}")
    return {"status": "password_reset", "username": u.username, "revoked_sessions": revoked}


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(
    _: Annotated[UserOut, Depends(require_permission("users.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[RoleOut]:
    result = await db.execute(select(User.role))
    roles = result.scalars().all()
    counts: dict[str, int] = {r: 0 for r in ROLE_ORDER}
    for r in roles:
        counts[r] = counts.get(r, 0) + 1
    pretty = {
        "super_admin": "Super Admin",
        "admin": "Admin",
        "supervisor": "Supervisor",
        "agent": "Agent",
    }
    return [
        RoleOut(
            id=r,
            name=pretty.get(r, r.title()),
            permissions=sorted(ROLE_PERMISSIONS[r]),
            user_count=counts.get(r, 0),
        )
        for r in ROLE_ORDER
    ]


@router.get("/audit-log", response_model=list[AuditEntry])
def get_audit_log(
    _: Annotated[UserOut, Depends(require_permission("users.manage"))],
    limit: int = 100,
) -> list[AuditEntry]:
    return [AuditEntry(**e) for e in audit_log(limit=max(1, min(limit, 500)))]


# ---- Monitoring: login activity + active sessions ----

class GeoInfo(BaseModel):
    city: str = ""
    country: str = ""
    country_code: str = ""
    region: str = ""
    lat: float | None = None
    lon: float | None = None


class LoginEvent(BaseModel):
    at: float
    username: str
    ip: str
    user_agent: str
    device: str
    result: str  # "success" | "failure"
    reason: str = ""
    session_prefix: str = ""
    geo: GeoInfo | None = None


class ActiveSession(BaseModel):
    token_prefix: str
    username: str
    issued_at: float
    expires_at: float
    last_seen: float
    issued_ip: str
    last_ip: str
    user_agent: str
    device: str
    geo: GeoInfo | None = None


class LoginActivityResponse(BaseModel):
    events: list[LoginEvent]
    stats: dict


@router.get("/login-activity", response_model=LoginActivityResponse)
async def get_login_activity(
    _: Annotated[UserOut, Depends(require_permission("users.manage"))],
    limit: int = 100,
) -> LoginActivityResponse:
    import time as _time
    raw = login_events(limit=max(1, min(limit, 500)))
    # Enrich every distinct IP with a geo lookup (cached after the first hit).
    distinct_ips = {e["ip"] for e in raw if e.get("ip")}
    geo_by_ip: dict[str, dict] = {}
    for ip in distinct_ips:
        geo_by_ip[ip] = await geo_for_ip(ip)

    events: list[LoginEvent] = []
    for e in raw:
        events.append(
            LoginEvent(
                at=e["at"],
                username=e["username"],
                ip=e["ip"],
                user_agent=e["user_agent"],
                device=e["device"],
                result=e["result"],
                reason=e.get("reason", "") or "",
                session_prefix=e.get("session_prefix", "") or "",
                geo=GeoInfo(**geo_by_ip[e["ip"]]) if e.get("ip") in geo_by_ip else None,
            )
        )
    now = _time.time()
    day_ago = now - 86400
    last24 = [e for e in raw if e["at"] >= day_ago]
    stats = {
        "total_events": len(raw),
        "logins_24h_success": sum(1 for e in last24 if e["result"] == "success"),
        "logins_24h_failure": sum(1 for e in last24 if e["result"] == "failure"),
        "unique_ips_24h": len({e["ip"] for e in last24 if e.get("ip")}),
        "unique_users_24h": len({e["username"] for e in last24 if e["result"] == "success"}),
    }
    return LoginActivityResponse(events=events, stats=stats)


@router.get("/active-sessions", response_model=list[ActiveSession])
async def get_active_sessions(
    _: Annotated[UserOut, Depends(require_permission("users.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ActiveSession]:
    result = await db.execute(select(UserSession).order_by(UserSession.last_seen.desc()))
    sessions = result.scalars().all()
    
    # Enrich distinct IPs.
    distinct_ips = {s.issued_ip for s in sessions if s.issued_ip}
    geo_by_ip: dict[str, dict] = {}
    for ip in distinct_ips:
        geo_by_ip[ip] = await geo_for_ip(ip)

    out: list[ActiveSession] = []
    for s in sessions:
        out.append(
            ActiveSession(
                token_prefix=s.token[:8],
                username=s.username,
                issued_at=s.issued_at,
                expires_at=s.expires_at,
                last_seen=s.last_seen,
                issued_ip=s.issued_ip or "0.0.0.0",
                last_ip=s.last_ip or "0.0.0.0",
                user_agent=s.user_agent or "Unknown",
                device=parse_user_agent(s.user_agent),
                geo=GeoInfo(**geo_by_ip[s.issued_ip]) if s.issued_ip in geo_by_ip else None,
            )
        )
    return out


@router.post("/active-sessions/{token_prefix}/revoke")
async def revoke_one_session(
    token_prefix: str,
    actor: Annotated[UserOut, Depends(require_permission("users.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str | bool]:
    if len(token_prefix) < 8:
        raise HTTPException(400, "Token prefix must be at least 8 characters")
    result = await db.execute(delete(UserSession).where(UserSession.token.like(f"{token_prefix}%")))
    if result.rowcount == 0:
        raise HTTPException(404, "No session matched that prefix")
    await db.commit()
    audit(actor=actor.username, action="session.revoke", target=token_prefix, detail="manual")
    return {"status": "revoked", "token_prefix": token_prefix}


# ---- Database / Supabase health ----

@router.get("/db/health")
async def db_health(
    _: Annotated[UserOut, Depends(require_permission("users.manage"))],
) -> dict:
    """Confirm Supabase credentials work and the expected tables exist."""
    from app.config import settings as _settings
    from app.supabase_client import (
        SupabaseError,
        health as sb_health,
        required_tables_present,
    )

    if not _settings.supabase_enabled:
        return {
            "enabled": False,
            "url": _settings.supabase_url or None,
            "hint": "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env",
        }
    expected = ("users", "sessions", "login_events", "audit_log")
    try:
        h = await sb_health()
        tables = await required_tables_present(expected)
    except SupabaseError as e:
        return {"enabled": True, "reachable": False, "error": str(e)}
    return {
        "enabled": True,
        "reachable": h["ok"],
        "url": h["url"],
        "schema": h["schema"],
        "tables": tables,
        "migration_applied": all(tables.values()),
        "hint": (
            None if all(tables.values())
            else "Open Supabase → SQL Editor and run backend/migrations/0001_initial.sql"
        ),
    }


@router.post("/users/_seed-token")
async def issue_token_for_user(
    username: str,
    actor: Annotated[UserOut, Depends(require_permission("users.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    """Diagnostic: mint a session token for another user (super_admin only)."""
    if settings.app_env != "development":
        raise HTTPException(404, "Not found")
    if actor.role != "super_admin":
        raise HTTPException(403, "Only super_admin may impersonate")
    
    uname = username.strip().lower()
    result = await db.execute(select(User).where(User.username == uname))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(404, "User not found")
        
    import secrets
    from app.security import SESSION_TTL_SECONDS
    token = secrets.token_urlsafe(32)
    now = time.time()
    new_sess = UserSession(
        token=token,
        username=u.username,
        issued_at=now,
        expires_at=now + SESSION_TTL_SECONDS,
        last_seen=now,
        issued_ip="0.0.0.0",
        user_agent="impersonation",
        last_ip="0.0.0.0"
    )
    db.add(new_sess)
    await db.commit()
    
    audit(actor=actor.username, action="user.impersonate", target=u.username)
    return {"token": token, "username": u.username}
