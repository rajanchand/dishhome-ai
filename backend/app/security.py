"""Security primitives: password hashing, session store, rate limiting.

In-memory implementations suitable for a single-process dev/staging deploy.
For multi-instance production, swap `SESSIONS` and `LOGIN_FAILURES` for
Redis (the API contract is stable — just the storage backend changes).
"""

from __future__ import annotations

import secrets
import time
from collections import deque
from threading import Lock
import jwt
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError

# Tuned for an interactive web login: ~50ms on a modern laptop.
# m=64MB, t=2 iterations, p=2 lanes. Resists offline attacks while keeping
# the login endpoint snappy.
_HASHER = PasswordHasher(time_cost=2, memory_cost=64 * 1024, parallelism=2)

# Pre-computed dummy hash for timing-safe comparison when user doesn't exist.
# Ensures verify_password takes the same time regardless of whether the
# username is valid — prevents username enumeration via timing side-channel.
DUMMY_HASH = _HASHER.hash("__dummy_timing_safe_placeholder__")

# ----- Passwords -----

PASSWORD_PREFIX = "$argon2"


def hash_password(plain: str) -> str:
    return _HASHER.hash(plain)


def verify_password(stored: str, plain: str) -> bool:
    """Verify a plaintext password against a stored hash.

    Returns True on match. Never raises — invalid hashes or mismatches both
    return False so the caller can't distinguish (timing safe).
    """
    if not stored or not plain:
        return False
    try:
        _HASHER.verify(stored, plain)
        return True
    except (VerifyMismatchError, InvalidHash, Exception):
        return False


def needs_rehash(stored: str) -> bool:
    try:
        return _HASHER.check_needs_rehash(stored)
    except (InvalidHash, Exception):
        return True


def is_hashed(value: str) -> bool:
    return bool(value) and value.startswith(PASSWORD_PREFIX)


# ----- Sessions (Migrated to DB) -----
# Session management (UserSession) is now handled via SQLAlchemy in routers/auth.py
# and managed via routers/admin.py. In-memory sessions have been removed.

SESSION_TTL_SECONDS = 86400  # 24 hours
JWT_ALGORITHM = "HS256"
_MIN_SECRET_LEN = 32


def _require_secret() -> str:
    from app.config import settings
    secret = (settings.app_secret_key or "").strip()
    if len(secret) < _MIN_SECRET_LEN:
        raise RuntimeError(
            f"APP_SECRET_KEY must be set to at least {_MIN_SECRET_LEN} chars. "
            "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
        )
    return secret


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, _require_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Return claims if the token is valid, otherwise None.

    A None return collapses signature failures, expiration, and malformed
    tokens into the same outcome so callers can't infer *why* a token is bad.
    """
    try:
        return jwt.decode(token, _require_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None

# ----- Login rate limiter -----

LOGIN_FAIL_WINDOW_SECONDS = 15 * 60  # 15 minutes
LOGIN_FAIL_MAX = 10  # per (ip, username) bucket — soft block after this

_LOGIN_FAILURES: dict[str, deque[float]] = {}
_LIMITER_LOCK = Lock()


def _bucket_key(ip: str, username: str) -> str:
    return f"{ip}|{username.lower()}"


def login_failure_count(ip: str, username: str) -> int:
    key = _bucket_key(ip, username)
    cutoff = time.time() - LOGIN_FAIL_WINDOW_SECONDS
    with _LIMITER_LOCK:
        q = _LOGIN_FAILURES.get(key)
        if not q:
            return 0
        # Drop expired entries
        while q and q[0] < cutoff:
            q.popleft()
        return len(q)


def record_login_failure(ip: str, username: str) -> int:
    key = _bucket_key(ip, username)
    now = time.time()
    cutoff = now - LOGIN_FAIL_WINDOW_SECONDS
    with _LIMITER_LOCK:
        q = _LOGIN_FAILURES.setdefault(key, deque(maxlen=LOGIN_FAIL_MAX * 4))
        while q and q[0] < cutoff:
            q.popleft()
        q.append(now)
        return len(q)


def clear_login_failures(ip: str, username: str) -> None:
    with _LIMITER_LOCK:
        _LOGIN_FAILURES.pop(_bucket_key(ip, username), None)


def login_throttled(ip: str, username: str) -> tuple[bool, int]:
    """Return (throttled?, retry_after_seconds)."""
    key = _bucket_key(ip, username)
    cutoff = time.time() - LOGIN_FAIL_WINDOW_SECONDS
    with _LIMITER_LOCK:
        q = _LOGIN_FAILURES.get(key)
        if not q:
            return (False, 0)
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) < LOGIN_FAIL_MAX:
            return (False, 0)
        retry_after = int((q[0] + LOGIN_FAIL_WINDOW_SECONDS) - time.time())
        return (True, max(retry_after, 1))


# ----- Audit log -----

_AUDIT: deque[dict] = deque(maxlen=500)


def audit(actor: str, action: str, target: str, detail: str = "") -> None:
    _AUDIT.append(
        {
            "at": time.time(),
            "actor": actor,
            "action": action,
            "target": target,
            "detail": detail,
        }
    )


def audit_log(limit: int = 100) -> list[dict]:
    return list(reversed(list(_AUDIT)))[:limit]


# ----- Login events ring (rich, for the monitoring page) -----

_LOGIN_EVENTS: deque[dict] = deque(maxlen=500)


def record_login_event(
    *,
    username: str,
    ip: str,
    user_agent: str,
    result: str,  # "success" | "failure"
    reason: str = "",
    session_prefix: str = "",
) -> None:
    _LOGIN_EVENTS.append(
        {
            "at": time.time(),
            "username": username,
            "ip": ip,
            "user_agent": user_agent,
            "device": parse_user_agent(user_agent),
            "result": result,
            "reason": reason,
            "session_prefix": session_prefix,
        }
    )


def login_events(limit: int = 100) -> list[dict]:
    return list(reversed(list(_LOGIN_EVENTS)))[: max(1, min(limit, 500))]


# ----- User-agent parser (regex; no external dep) -----

_OS_PATTERNS = [
    ("iPhone", "iOS"),
    ("iPad", "iPadOS"),
    ("Android", "Android"),
    ("Windows NT 11", "Windows 11"),
    ("Windows NT 10", "Windows 10"),
    ("Windows NT", "Windows"),
    ("Mac OS X", "macOS"),
    ("CrOS", "ChromeOS"),
    ("Linux", "Linux"),
]
_BROWSER_PATTERNS = [
    # Order matters: Edge/Opera/Brave masquerade as Chrome.
    ("Edg/", "Edge"),
    ("EdgA/", "Edge"),
    ("OPR/", "Opera"),
    ("OPiOS/", "Opera"),
    ("Brave/", "Brave"),
    ("CriOS/", "Chrome"),
    ("Chromium/", "Chromium"),
    ("Chrome/", "Chrome"),
    ("FxiOS/", "Firefox"),
    ("Firefox/", "Firefox"),
    ("Safari/", "Safari"),
    ("curl/", "curl"),
    ("httpx", "httpx"),
    ("python-requests", "python"),
]


def parse_user_agent(ua: str | None) -> str:
    """Best-effort 'Chrome on macOS' label. Falls back to a truncated UA."""
    if not ua:
        return "Unknown"
    os_name = "Unknown OS"
    for pat, name in _OS_PATTERNS:
        if pat in ua:
            os_name = name
            break
    browser = "Unknown"
    for pat, name in _BROWSER_PATTERNS:
        if pat in ua:
            browser = name
            break
    if browser == "Unknown" and os_name == "Unknown OS":
        return ua[:64]
    return f"{browser} on {os_name}"


# ----- IP geolocation (cached, lazy via ip-api.com) -----

_GEO_CACHE: dict[str, dict] = {}
_GEO_LOCK = Lock()


def _is_private_ip(ip: str) -> bool:
    if not ip or ip in {"0.0.0.0", "::1", "127.0.0.1", "localhost"}:
        return True
    if ip.startswith(("10.", "192.168.", "169.254.", "fe80:", "fc00:", "fd00:")):
        return True
    # 172.16.0.0/12
    if ip.startswith("172."):
        try:
            second = int(ip.split(".", 2)[1])
            if 16 <= second <= 31:
                return True
        except (ValueError, IndexError):
            pass
    return False


async def geo_for_ip(ip: str) -> dict:
    """Return {city, country, country_code, region, lat, lon} for an IP.

    Cached per process. Uses ip-api.com (free, 45 req/min, no key). Falls
    back to a placeholder when the lookup fails or the IP is private.
    """
    with _GEO_LOCK:
        cached = _GEO_CACHE.get(ip)
    if cached is not None:
        return cached
    if _is_private_ip(ip):
        result = {"city": "Local network", "country": "—", "country_code": "", "region": "", "lat": None, "lon": None}
        with _GEO_LOCK:
            _GEO_CACHE[ip] = result
        return result
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(
                f"https://ip-api.com/json/{ip}",
                params={"fields": "status,country,countryCode,city,regionName,lat,lon"},
            )
            d = r.json()
        if d.get("status") == "success":
            result = {
                "city": d.get("city") or "—",
                "country": d.get("country") or "—",
                "country_code": d.get("countryCode") or "",
                "region": d.get("regionName") or "",
                "lat": d.get("lat"),
                "lon": d.get("lon"),
            }
        else:
            result = {"city": "Unknown", "country": "—", "country_code": "", "region": "", "lat": None, "lon": None}
    except Exception:
        result = {"city": "Lookup failed", "country": "—", "country_code": "", "region": "", "lat": None, "lon": None}
    with _GEO_LOCK:
        _GEO_CACHE[ip] = result
    return result
