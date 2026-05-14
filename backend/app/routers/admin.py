"""Admin: user + role management.

Only users with `users.manage` (super_admin / admin) can hit these endpoints.
Roles themselves are defined in code (rbac.py) for auditability; this router
lets admins assign roles to users, not invent new ones.
"""

import secrets
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.mock_data import USERS
from app.rbac import ROLE_ORDER, ROLE_PERMISSIONS, permissions_for
from app.routers.auth import UserOut, require_permission, revoke_user_sessions

router = APIRouter(prefix="/admin", tags=["admin"])


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
    role: str
    password: str = Field(min_length=8, max_length=128)


class UpdateUserRequest(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    role: str | None = None


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class RoleOut(BaseModel):
    id: str
    name: str
    permissions: list[str]
    user_count: int


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


def _check_role(role: str) -> None:
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(
            400, f"Unknown role {role!r}. Allowed: {', '.join(ROLE_ORDER)}"
        )


def _can_target(actor: UserOut, target_role: str) -> None:
    """Admins can manage anyone except other super_admins; super_admins manage all."""
    if actor.role == "super_admin":
        return
    if target_role == "super_admin":
        raise HTTPException(403, "Only super_admin can manage super_admin users")


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
    _check_role(payload.role)
    _can_target(actor, payload.role)
    uname = payload.username.lower()
    if uname in USERS:
        raise HTTPException(409, f"User {uname!r} already exists")
    entry = {
        "username": uname,
        "password": payload.password,
        "name": payload.name.strip(),
        "email": str(payload.email),
        "role": payload.role,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": actor.username,
    }
    USERS[uname] = entry
    return _to_admin_user(entry)


@router.patch("/users/{username}", response_model=AdminUser)
def update_user(
    username: str,
    payload: UpdateUserRequest,
    actor: Annotated[UserOut, Depends(require_permission("users.manage"))],
) -> AdminUser:
    u = USERS.get(username.lower())
    if not u:
        raise HTTPException(404, "User not found")
    _can_target(actor, u["role"])
    if payload.role is not None:
        _check_role(payload.role)
        _can_target(actor, payload.role)
        # Prevent demoting the last super_admin.
        if u["role"] == "super_admin" and payload.role != "super_admin":
            others = [x for x in USERS.values() if x["role"] == "super_admin" and x["username"] != u["username"]]
            if not others:
                raise HTTPException(409, "Cannot remove the last super_admin")
        u["role"] = payload.role
        revoke_user_sessions(u["username"])
    if payload.name is not None:
        u["name"] = payload.name.strip()
    if payload.email is not None:
        u["email"] = str(payload.email)
    return _to_admin_user(u)


@router.delete("/users/{username}", status_code=204)
def delete_user(
    username: str,
    actor: Annotated[UserOut, Depends(require_permission("users.manage"))],
) -> None:
    uname = username.lower()
    u = USERS.get(uname)
    if not u:
        raise HTTPException(404, "User not found")
    if uname == actor.username:
        raise HTTPException(409, "You cannot delete yourself")
    _can_target(actor, u["role"])
    if u["role"] == "super_admin":
        others = [x for x in USERS.values() if x["role"] == "super_admin" and x["username"] != uname]
        if not others:
            raise HTTPException(409, "Cannot delete the last super_admin")
    USERS.pop(uname, None)
    revoke_user_sessions(uname)


@router.post("/users/{username}/reset-password")
def reset_password(
    username: str,
    payload: ResetPasswordRequest,
    actor: Annotated[UserOut, Depends(require_permission("users.manage"))],
) -> dict[str, str]:
    u = USERS.get(username.lower())
    if not u:
        raise HTTPException(404, "User not found")
    _can_target(actor, u["role"])
    u["password"] = payload.new_password
    revoked = revoke_user_sessions(u["username"])
    return {"status": "password_reset", "username": u["username"], "revoked_sessions": str(revoked)}


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


@router.post("/users/_seed-token")
def issue_token_for_user(
    username: str,
    actor: Annotated[UserOut, Depends(require_permission("users.manage"))],
) -> dict[str, str]:
    """Diagnostic: mint a session token for another user (for impersonation/testing).
    Super_admin only."""
    if actor.role != "super_admin":
        raise HTTPException(403, "Only super_admin may impersonate")
    from app.routers.auth import issue_session
    u = USERS.get(username.lower())
    if not u:
        raise HTTPException(404, "User not found")
    return {"token": issue_session(u["username"]), "username": u["username"]}
