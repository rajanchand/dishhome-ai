from datetime import datetime, timedelta
from typing import Annotated, Callable
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.user import User, Session as UserSession
from app.rbac import has_permission, permissions_for
from app.security import (
    audit,
    clear_login_failures,
    hash_password,
    login_throttled,
    needs_rehash,
    record_login_failure,
    verify_password,
    SESSION_TTL_SECONDS,
    DUMMY_HASH
)

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)

class UserOut(BaseModel):
    username: str
    full_name: str
    role: str
    permissions: list[str] = []

class LoginResponse(BaseModel):
    token: str
    user: UserOut
    expires_in: int

def _user_public(user: User) -> UserOut:
    return UserOut(
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        permissions=permissions_for(user.role),
    )

def _client_ip(request: Request | None) -> str:
    if request is None:
        return "0.0.0.0"
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"

async def current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> UserOut:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    
    token = authorization.split(" ", 1)[1].strip()
    
    # Lookup session in DB
    result = await db.execute(
        select(UserSession, User)
        .join(User, UserSession.username == User.username)
        .where(UserSession.id == token)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    
    sess, user = row
    if sess.expires_at < datetime.now():
        await db.delete(sess)
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")

    # Update last seen
    sess.last_seen_at = datetime.now()
    await db.commit()
    
    return _user_public(user)

@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest, 
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)]
) -> LoginResponse:
    ip = _client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    uname_raw = payload.username.strip().lower()

    throttled, retry_after = login_throttled(ip, uname_raw)
    if throttled:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Too many failed attempts. Try again in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )

    # Lookup user in DB
    result = await db.execute(select(User).where(User.username == uname_raw))
    user = result.scalar_one_or_none()
    
    stored_hash = user.password_hash if user else DUMMY_HASH
    
    ok = verify_password(stored_hash, payload.password) and (user is not None)
    
    if not ok:
        record_login_failure(ip, uname_raw)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)

    clear_login_failures(ip, uname_raw)
    
    # Generate persistent session
    token = secrets.token_urlsafe(32)
    new_sess = UserSession(
        id=token,
        username=user.username,
        expires_at=datetime.now() + timedelta(seconds=SESSION_TTL_SECONDS),
        ip_address=ip,
        user_agent=user_agent[:255]
    )
    db.add(new_sess)
    await db.commit()
    
    audit(actor=user.username, action="login", target=user.username, detail=f"ip={ip}")
    
    return LoginResponse(
        token=token,
        user=_user_public(user),
        expires_in=SESSION_TTL_SECONDS,
    )


@router.get("/me", response_model=UserOut)
def me(user: Annotated[UserOut, Depends(current_user)]) -> UserOut:
    return user

def require_permission(perm: str):
    """
    Dependency factory to check for a specific permission.
    """
    async def _check(user: Annotated[UserOut, Depends(current_user)]):
        if perm not in (user.permissions or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action forbidden. Required permission: {perm}",
            )
        return user
    return _check

