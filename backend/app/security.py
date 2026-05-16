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


# ----- Sessions -----

SESSION_TTL_SECONDS = 24 * 60 * 60  # 24h sliding window
SESSION_IDLE_RENEWAL_SECONDS = 60 * 60  # only bump expiry at most hourly to keep dict writes cheap
MAX_SESSIONS_PER_USER = 10  # prevent session flooding


class _Session:
    __slots__ = (
        "username",
        "issued_at",
        "expires_at",
        "last_seen",
        "issued_ip",
        "user_agent",
        "last_ip",
    )

    def __init__(self, username: str, ttl: int, ip: str = "", user_agent: str = "") -> None:
        now = time.time()
        self.username = username
        self.issued_at = now
        self.expires_at = now + ttl
        self.last_seen = now
        self.issued_ip = ip
        self.user_agent = user_agent
        self.last_ip = ip


_SESSIONS: dict[str, _Session] = {}
_SESSIONS_LOCK = Lock()


def issue_session(
    username: str,
    ttl: int = SESSION_TTL_SECONDS,
    ip: str = "",
    user_agent: str = "",
) -> str:
    token = secrets.token_urlsafe(32)
    with _SESSIONS_LOCK:
        # Enforce per-user session limit — evict oldest sessions
        user_tokens = [
            (t, s) for t, s in _SESSIONS.items() if s.username == username
        ]
        if len(user_tokens) >= MAX_SESSIONS_PER_USER:
            user_tokens.sort(key=lambda x: x[1].last_seen)
            for old_tok, _ in user_tokens[: len(user_tokens) - MAX_SESSIONS_PER_USER + 1]:
                _SESSIONS.pop(old_tok, None)
        _SESSIONS[token] = _Session(username, ttl, ip=ip, user_agent=user_agent)
    return token


def resolve_session(token: str, ip: str | None = None) -> str | None:
    """Return the session's username if valid, else None.

    Side effect: bumps `expires_at` if the session is more than
    SESSION_IDLE_RENEWAL_SECONDS into its TTL — sliding-window auth.
    Also records the current IP so the monitoring view shows "last seen from".
    """
    if not token:
        return None
    now = time.time()
    with _SESSIONS_LOCK:
        s = _SESSIONS.get(token)
        if not s:
            return None
        if s.expires_at < now:
            _SESSIONS.pop(token, None)
            return None
        if (now - s.last_seen) > SESSION_IDLE_RENEWAL_SECONDS:
            s.last_seen = now
            s.expires_at = now + SESSION_TTL_SECONDS
        if ip:
            s.last_ip = ip
        return s.username


def revoke_session(token: str) -> bool:
    with _SESSIONS_LOCK:
        return _SESSIONS.pop(token, None) is not None


def revoke_user_sessions(username: str) -> int:
    n = 0
    with _SESSIONS_LOCK:
        for tok, s in list(_SESSIONS.items()):
            if s.username == username:
                _SESSIONS.pop(tok, None)
                n += 1
    return n


def revoke_session_by_prefix(prefix: str) -> bool:
    """Admin convenience: revoke a session by its token's first ~8 chars.

    Full tokens are never exposed via the API — the admin UI shows a short
    prefix so they can identify and kill specific sessions.
    """
    if not prefix or len(prefix) < 6:
        return False
    with _SESSIONS_LOCK:
        for tok in list(_SESSIONS.keys()):
            if tok.startswith(prefix):
                _SESSIONS.pop(tok, None)
                return True
    return False


def session_count() -> int:
    return len(_SESSIONS)


def active_sessions() -> list[dict]:
    """Snapshot of every live session (no token values; just prefixes)."""
    with _SESSIONS_LOCK:
        rows = []
        for tok, s in _SESSIONS.items():
            rows.append(
                {
                    "token_prefix": tok[:8],
                    "username": s.username,
                    "issued_at": s.issued_at,
                    "expires_at": s.expires_at,
                    "last_seen": s.last_seen,
                    "issued_ip": s.issued_ip,
                    "last_ip": s.last_ip,
                    "user_agent": s.user_agent,
                }
            )
    rows.sort(key=lambda r: r["last_seen"], reverse=True)
    return rows


def prune_expired_sessions() -> int:
    now = time.time()
    pruned = 0
    with _SESSIONS_LOCK:
        for tok, s in list(_SESSIONS.items()):
            if s.expires_at < now:
                _SESSIONS.pop(tok, None)
                pruned += 1
    return pruned


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
