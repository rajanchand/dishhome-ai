"""Mock auth. Replace with real OAuth/LDAP/JWT in production."""

import secrets
from typing import Annotated, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.mock_data import USERS
from app.rbac import has_permission, permissions_for

router = APIRouter(prefix="/auth", tags=["auth"])

# session_token -> username
_SESSIONS: dict[str, str] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    username: str
    name: str
    email: str
    role: str
    permissions: list[str] = []


class LoginResponse(BaseModel):
    token: str
    user: UserOut


def _user_public(user: dict) -> UserOut:
    return UserOut(
        username=user["username"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        permissions=permissions_for(user["role"]),
    )


def current_user(authorization: Annotated[str | None, Header()] = None) -> UserOut:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    username = _SESSIONS.get(token)
    if not username:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = USERS.get(username)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return _user_public(user)


def require_permission(perm: str) -> Callable[[UserOut], UserOut]:
    """FastAPI dependency factory: enforces the caller's role has `perm`."""

    def _dep(user: Annotated[UserOut, Depends(current_user)]) -> UserOut:
        if not has_permission(user.role, perm):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Role {user.role!r} lacks permission {perm!r}",
            )
        return user

    return _dep


def issue_session(username: str) -> str:
    """Public helper so the admin router can rotate a user's tokens on update."""
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = username
    return token


def revoke_user_sessions(username: str) -> int:
    n = 0
    for tok, uname in list(_SESSIONS.items()):
        if uname == username:
            _SESSIONS.pop(tok, None)
            n += 1
    return n


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    user = USERS.get(payload.username.lower())
    if not user or user["password"] != payload.password:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token = issue_session(user["username"])
    return LoginResponse(token=token, user=_user_public(user))


@router.post("/logout")
def logout(user: Annotated[UserOut, Depends(current_user)]) -> dict[str, str]:
    return {"status": "logged_out", "username": user.username}


@router.get("/me", response_model=UserOut)
def me(user: Annotated[UserOut, Depends(current_user)]) -> UserOut:
    return user
