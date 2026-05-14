"""Admin: user + role management.

All endpoints require the `users.manage` permission. Mutations are logged
to the audit ring (visible at /admin/audit-log).
"""

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.mock_data import USERS
from app.rbac import ROLE_ORDER, ROLE_PERMISSIONS, permissions_for
from app.routers.auth import UserOut, require_permission
from app.security import (
    audit,
    audit_log,
    hash_password,
    issue_session,
    revoke_user_sessions,
)

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


def _to_admin_user(u: dict) -> AdminUser:
    return AdminUser(
        username=u["username"],
        name=u["name"],
        email=u["email"],
        role=u["role"],
        permissions=permissions_for(u["role"]),
        created_at=u.get("created_at"),
        created_by=u.get("created_by"),
    )


def _can_target(actor: UserOut, target_role: str) -> None:
    """Admins can manage anyone except other super_admins; super_admins manage all."""
    if actor.role == "super_admin":
        return
    if target_role == "super_admin":
        raise HTTPException(403, "Only super_admin can manage super_admin users")


def _last_super_admin_guard(username_being_changed: str) -> None:
    others = [
        u for u in USERS.values()
        if u["role"] == "super_admin" and u["username"] != username_being_changed
    ]
    if not others:
        raise HTTPException(409, "Cannot remove the last super_admin")


@router.get("/users", response_model=list[AdminUser])
def list_users(
    _: Annotated[UserOut, Depends(require_permission("users.manage"))],
) -> list[AdminUser]:
    return [_to_admin_user(u) for u in USERS.values()]


@router.post("/users", response_model=AdminUser, status_code=201)
def create_user(
    payload: CreateUserRequest,
    actor: Annotated[UserOut, Depends(require_permission("users.manage"))],
) -> AdminUser:
    _can_target(actor, payload.role)
    uname = payload.username  # already lowercased by validator
    if uname in USERS:
        raise HTTPException(409, f"User {uname!r} already exists")
    entry = {
        "username": uname,
        "password": hash_password(payload.password),
        "name": payload.name.strip(),
        "email": str(payload.email),
        "role": payload.role,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": actor.username,
    }
    USERS[uname] = entry
    audit(actor=actor.username, action="user.create", target=uname, detail=f"role={payload.role}")
    return _to_admin_user(entry)


@router.patch("/users/{username}", response_model=AdminUser)
def update_user(
    username: str,
    payload: UpdateUserRequest,
    actor: Annotated[UserOut, Depends(require_permission("users.manage"))],
) -> AdminUser:
    uname = username.strip().lower()
    u = USERS.get(uname)
    if not u:
        raise HTTPException(404, "User not found")
    _can_target(actor, u["role"])
    update = payload.model_dump(exclude_unset=True, exclude_none=True)
    changed: list[str] = []
    if "role" in update and update["role"] != u["role"]:
        new_role = update["role"]
        _can_target(actor, new_role)
        if u["role"] == "super_admin" and new_role != "super_admin":
            _last_super_admin_guard(u["username"])
        u["role"] = new_role
        revoke_user_sessions(u["username"])
        changed.append(f"role={new_role}")
    if "name" in update:
        u["name"] = update["name"].strip()
        changed.append("name")
    if "email" in update:
        u["email"] = str(update["email"])
        changed.append("email")
    if changed:
        audit(actor=actor.username, action="user.update", target=u["username"], detail=",".join(changed))
    return _to_admin_user(u)


@router.delete("/users/{username}", status_code=204)
def delete_user(
    username: str,
    actor: Annotated[UserOut, Depends(require_permission("users.manage"))],
) -> None:
    uname = username.strip().lower()
    u = USERS.get(uname)
    if not u:
        raise HTTPException(404, "User not found")
    if uname == actor.username:
        raise HTTPException(409, "You cannot delete yourself")
    _can_target(actor, u["role"])
    if u["role"] == "super_admin":
        _last_super_admin_guard(uname)
    USERS.pop(uname, None)
    revoke_user_sessions(uname)
    audit(actor=actor.username, action="user.delete", target=uname)


@router.post("/users/{username}/reset-password")
def reset_password(
    username: str,
    payload: ResetPasswordRequest,
    actor: Annotated[UserOut, Depends(require_permission("users.manage"))],
) -> dict[str, int | str]:
    uname = username.strip().lower()
    u = USERS.get(uname)
    if not u:
        raise HTTPException(404, "User not found")
    _can_target(actor, u["role"])
    u["password"] = hash_password(payload.new_password)
    revoked = revoke_user_sessions(u["username"])
    audit(actor=actor.username, action="user.reset_password", target=u["username"], detail=f"revoked={revoked}")
    return {"status": "password_reset", "username": u["username"], "revoked_sessions": revoked}


@router.get("/roles", response_model=list[RoleOut])
def list_roles(
    _: Annotated[UserOut, Depends(require_permission("users.manage"))],
) -> list[RoleOut]:
    counts: dict[str, int] = {r: 0 for r in ROLE_ORDER}
    for u in USERS.values():
        counts[u["role"]] = counts.get(u["role"], 0) + 1
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


@router.post("/users/_seed-token")
def issue_token_for_user(
    username: str,
    actor: Annotated[UserOut, Depends(require_permission("users.manage"))],
) -> dict[str, str]:
    """Diagnostic: mint a session token for another user (super_admin only)."""
    if actor.role != "super_admin":
        raise HTTPException(403, "Only super_admin may impersonate")
    u = USERS.get(username.strip().lower())
    if not u:
        raise HTTPException(404, "User not found")
    audit(actor=actor.username, action="user.impersonate", target=u["username"])
    return {"token": issue_session(u["username"]), "username": u["username"]}
