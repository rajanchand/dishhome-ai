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


class _Session:
    __slots__ = ("username", "issued_at", "expires_at", "last_seen")

    def __init__(self, username: str, ttl: int) -> None:
        now = time.time()
        self.username = username
        self.issued_at = now
        self.expires_at = now + ttl
        self.last_seen = now


_SESSIONS: dict[str, _Session] = {}
_SESSIONS_LOCK = Lock()


def issue_session(username: str, ttl: int = SESSION_TTL_SECONDS) -> str:
    token = secrets.token_urlsafe(32)
    with _SESSIONS_LOCK:
        _SESSIONS[token] = _Session(username, ttl)
    return token


def resolve_session(token: str) -> str | None:
    """Return the session's username if valid, else None.

    Side effect: bumps `expires_at` if the session is more than
    SESSION_IDLE_RENEWAL_SECONDS into its TTL — sliding-window auth.
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


def session_count() -> int:
    return len(_SESSIONS)


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
