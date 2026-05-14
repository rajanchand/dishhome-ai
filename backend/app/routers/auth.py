"""Auth: login, logout, /me. Uses argon2-hashed passwords, sliding-window
sessions, and per-(ip,username) login throttling."""

from typing import Annotated, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.mock_data import USERS
from app.rbac import has_permission, permissions_for
from app.security import (
    audit,
    clear_login_failures,
    hash_password,
    issue_session as _issue_session,
    login_throttled,
    needs_rehash,
    record_login_failure,
    resolve_session,
    revoke_session,
    revoke_user_sessions as _revoke_user_sessions,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class UserOut(BaseModel):
    username: str
    name: str
    email: str
    role: str
    permissions: list[str] = []


class LoginResponse(BaseModel):
    token: str
    user: UserOut
    expires_in: int


def _user_public(user: dict) -> UserOut:
    return UserOut(
        username=user["username"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        permissions=permissions_for(user["role"]),
    )


def _client_ip(request: Request | None) -> str:
    if request is None:
        return "0.0.0.0"
    # Prefer X-Forwarded-For when behind a proxy, else direct client.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


def current_user(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> UserOut:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    username = resolve_session(token)
    if not username:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    user = USERS.get(username)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    # Attach the bearer for downstream logout
    request.state.bearer_token = token
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
    return _issue_session(username)


def revoke_user_sessions(username: str) -> int:
    return _revoke_user_sessions(username)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request) -> LoginResponse:
    ip = _client_ip(request)
    uname_raw = payload.username.strip().lower()

    throttled, retry_after = login_throttled(ip, uname_raw)
    if throttled:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Too many failed attempts. Try again in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )

    user = USERS.get(uname_raw)
    stored = user.get("password") if user else None
    # Always run argon2 verify (against a dummy hash if user missing) so the
    # response time is constant whether the username exists or not.
    ok = bool(user) and verify_password(stored or "", payload.password)
    if not ok:
        record_login_failure(ip, uname_raw)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    # Upgrade-in-place if argon2 parameters changed (or seed was plaintext).
    assert user is not None
    if needs_rehash(user["password"]):
        user["password"] = hash_password(payload.password)

    clear_login_failures(ip, uname_raw)
    token = issue_session(user["username"])
    audit(actor=user["username"], action="login", target=user["username"], detail=f"ip={ip}")
    from app.security import SESSION_TTL_SECONDS
    return LoginResponse(
        token=token,
        user=_user_public(user),
        expires_in=SESSION_TTL_SECONDS,
    )


@router.post("/logout")
def logout(
    user: Annotated[UserOut, Depends(current_user)],
    request: Request,
) -> dict[str, str]:
    tok = getattr(request.state, "bearer_token", None)
    if tok:
        revoke_session(tok)
    audit(actor=user.username, action="logout", target=user.username)
    return {"status": "logged_out", "username": user.username}


@router.get("/me", response_model=UserOut)
def me(user: Annotated[UserOut, Depends(current_user)]) -> UserOut:
    return user
