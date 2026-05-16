"""Auth: login, logout, /me. Uses argon2-hashed passwords, sliding-window
sessions, and per-(ip,username) login throttling."""

from typing import Annotated, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.db_repo import persist_audit, persist_login_event
from app.mock_data import USERS
from app.rbac import has_permission, permissions_for
from app.security import (
    audit,
    clear_login_failures,
    hash_password,
    issue_session as _issue_session,
    login_throttled,
    needs_rehash,
    record_login_event,
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


async def current_user(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> UserOut:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    ip = _client_ip(request)
    
    import time
    from app.database import get_pool
    pool = get_pool()
    now = time.time()
    
    async with pool.acquire() as conn:
        session = await conn.fetchrow(
            "SELECT username, expires_at FROM dh.sessions WHERE token = $1", token
        )
        if not session or session["expires_at"] < now:
            if session:
                await conn.execute("DELETE FROM dh.sessions WHERE token = $1", token)
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
            
        # Sliding window renewal
        from app.security import SESSION_IDLE_RENEWAL_SECONDS, SESSION_TTL_SECONDS
        await conn.execute(
            "UPDATE dh.sessions SET last_seen = $1, last_ip = $2 WHERE token = $3 AND last_seen < $4",
            now, ip, token, now - SESSION_IDLE_RENEWAL_SECONDS
        )
        
        user_row = await conn.fetchrow(
            "SELECT username, name, email, role FROM dh.users WHERE username = $1",
            session["username"]
        )
        if not user_row:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
            
    request.state.bearer_token = token
    return _user_public(dict(user_row))


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


def issue_session(username: str, ip: str = "", user_agent: str = "") -> str:
    return _issue_session(username, ip=ip, user_agent=user_agent)


def revoke_user_sessions(username: str) -> int:
    return _revoke_user_sessions(username)


def _last_login_event() -> dict:
    """Last entry we just appended via record_login_event."""
    from app.security import _LOGIN_EVENTS  # private but stable in-process
    return _LOGIN_EVENTS[-1]


def _last_audit() -> dict:
    from app.security import _AUDIT
    return _AUDIT[-1]


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, request: Request) -> LoginResponse:
    ip = _client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    uname_raw = payload.username.strip().lower()

    throttled, retry_after = login_throttled(ip, uname_raw)
    if throttled:
        record_login_event(
            username=uname_raw, ip=ip, user_agent=user_agent,
            result="failure", reason="rate_limited",
        )
        await persist_login_event(_last_login_event())
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Too many failed attempts. Try again in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )

    user = None
    stored = None
    try:
        from app.database import get_pool
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT username, password_hash as password, name, email, role FROM dh.users WHERE username = $1",
                uname_raw
            )
            if row:
                user = dict(row)
                stored = user.get("password")
    except Exception as e:
        import logging
        logging.getLogger("dishhome.auth").error(f"DB Error: {e}")
        # fallback to empty user if DB fails
        pass

    # Always run argon2 verify (against a pre-computed dummy hash if user
    # missing) so the response time is constant whether the username exists or
    # not — prevents username enumeration via timing side-channel.
    from app.security import DUMMY_HASH
    ok = verify_password(stored or DUMMY_HASH, payload.password) and bool(user)
    if not ok:
        record_login_failure(ip, uname_raw)
        record_login_event(
            username=uname_raw, ip=ip, user_agent=user_agent,
            result="failure", reason="bad_credentials",
        )
        await persist_login_event(_last_login_event())
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    assert user is not None
    if needs_rehash(user["password"]):
        user["password"] = hash_password(payload.password)

    clear_login_failures(ip, uname_raw)
    
    import secrets
    import time
    from app.security import SESSION_TTL_SECONDS
    token = secrets.token_urlsafe(32)
    now = time.time()
    
    # Store session in Postgres
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO dh.sessions (token, username, issued_at, expires_at, last_seen, issued_ip, user_agent, last_ip)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            token, user["username"], now, now + SESSION_TTL_SECONDS, now, ip, user_agent, ip
        )
    audit(actor=user["username"], action="login", target=user["username"], detail=f"ip={ip}")
    record_login_event(
        username=user["username"], ip=ip, user_agent=user_agent,
        result="success", session_prefix=token[:8],
    )
    await persist_audit(_last_audit())
    await persist_login_event(_last_login_event())

    from app.security import SESSION_TTL_SECONDS
    return LoginResponse(
        token=token,
        user=_user_public(user),
        expires_in=SESSION_TTL_SECONDS,
    )


@router.post("/logout")
async def logout(
    user: Annotated[UserOut, Depends(current_user)],
    request: Request,
) -> dict[str, str]:
    tok = getattr(request.state, "bearer_token", None)
    if tok:
        from app.database import get_pool
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM dh.sessions WHERE token = $1", tok)
    audit(actor=user.username, action="logout", target=user.username)
    await persist_audit(_last_audit())
    return {"status": "logged_out", "username": user.username}


@router.get("/me", response_model=UserOut)
def me(user: Annotated[UserOut, Depends(current_user)]) -> UserOut:
    return user
