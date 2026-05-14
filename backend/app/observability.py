"""Production-grade observability: request IDs, timing, metrics, structured errors."""

import logging
import time
import uuid
from collections import deque
from contextvars import ContextVar
from typing import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(request_id)s] %(name)s — %(message)s"
        )
    )
    handler.addFilter(RequestIdLogFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


# ---------------- Metrics (in-memory ring buffer) ----------------
class Metrics:
    """Simple in-memory metrics. Replace with Prometheus client in production."""

    def __init__(self, capacity: int = 1000) -> None:
        self.requests: deque[dict] = deque(maxlen=capacity)
        self.errors_by_status: dict[int, int] = {}
        self.requests_by_route: dict[str, int] = {}

    def record(self, route: str, method: str, status_code: int, duration_ms: float) -> None:
        self.requests.append(
            {
                "route": route,
                "method": method,
                "status": status_code,
                "duration_ms": round(duration_ms, 2),
                "ts": time.time(),
            }
        )
        if status_code >= 400:
            self.errors_by_status[status_code] = self.errors_by_status.get(status_code, 0) + 1
        self.requests_by_route[route] = self.requests_by_route.get(route, 0) + 1

    def snapshot(self) -> dict:
        recent = list(self.requests)
        if not recent:
            return {
                "total_requests": 0,
                "error_rate": 0.0,
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "errors_by_status": {},
                "top_routes": [],
            }
        durs = sorted(r["duration_ms"] for r in recent)
        errors = sum(1 for r in recent if r["status"] >= 400)
        return {
            "total_requests": len(recent),
            "error_rate": round(errors / len(recent), 4),
            "p50_ms": _pct(durs, 0.50),
            "p95_ms": _pct(durs, 0.95),
            "p99_ms": _pct(durs, 0.99),
            "errors_by_status": dict(self.errors_by_status),
            "top_routes": sorted(
                self.requests_by_route.items(), key=lambda kv: -kv[1]
            )[:8],
            "window_size": len(recent),
        }


def _pct(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(int(len(sorted_values) * p), len(sorted_values) - 1)
    return round(sorted_values[idx], 2)


metrics = Metrics()


# ---------------- Middleware ----------------
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable]
    ):
        incoming = request.headers.get("x-request-id")
        rid = incoming or uuid.uuid4().hex[:12]
        token = request_id_var.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.record(
                request.url.path, request.method, 500, duration_ms
            )
            logging.getLogger("dishhome").exception(
                "Unhandled error %s %s", request.method, request.url.path
            )
            request_id_var.reset(token)
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "internal_error",
                        "message": "Internal server error",
                        "request_id": rid,
                    }
                },
                headers={"x-request-id": rid},
            )
        duration_ms = (time.perf_counter() - start) * 1000
        metrics.record(
            request.url.path, request.method, response.status_code, duration_ms
        )
        response.headers["x-request-id"] = rid
        response.headers["x-process-time-ms"] = f"{duration_ms:.1f}"
        _apply_security_headers(response)
        request_id_var.reset(token)
        return response


def _apply_security_headers(response) -> None:
    """Defense-in-depth headers. Cheap to add, hard to forget later."""
    # Block MIME sniffing.
    response.headers.setdefault("x-content-type-options", "nosniff")
    # Don't leak referrer URLs cross-origin.
    response.headers.setdefault("referrer-policy", "no-referrer")
    # Disable the legacy XSS auditor (it's been removed from modern browsers but
    # some intermediaries still respect 0 = off).
    response.headers.setdefault("x-xss-protection", "0")
    # Deny framing so the portal can't be wrapped in a clickjacking iframe.
    response.headers.setdefault("x-frame-options", "DENY")
    # Restrict the set of powerful APIs unless explicitly granted.
    response.headers.setdefault(
        "permissions-policy",
        "camera=(), geolocation=(), microphone=(), payment=(), usb=()",
    )
    # HSTS only makes sense when served over HTTPS; harmless when not.
    response.headers.setdefault(
        "strict-transport-security",
        "max-age=31536000; includeSubDomains",
    )


# ---------------- Structured error handlers ----------------
def _error_payload(code: str, message: str, status_code: int) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id_var.get(),
            "status": status_code,
        }
    }


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    code = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        413: "payload_too_large",
        422: "unprocessable_entity",
        429: "rate_limited",
    }.get(exc.status_code, "http_error")
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(code, str(exc.detail), exc.status_code),
    )


_SENSITIVE_KEYS = {"password", "new_password", "current_password", "token", "auth_token"}


def _json_safe(v):
    """Pydantic v2 sometimes puts non-serializable objects (e.g. the raw
    ValueError) into a detail's `ctx`. Stringify anything JSON can't handle."""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, (list, tuple)):
        return [_json_safe(x) for x in v]
    if isinstance(v, dict):
        return {k: _json_safe(x) for k, x in v.items()}
    return str(v)


def _scrub(detail: dict) -> dict:
    """Mask the input value when the field name is sensitive — so a 422 on
    password validation doesn't echo the attempted password back to the client."""
    out = _json_safe(detail)
    if not isinstance(out, dict):
        return {"detail": out}
    loc = out.get("loc") or []
    last = str(loc[-1]) if loc else ""
    if last.lower() in _SENSITIVE_KEYS:
        if "input" in out:
            out["input"] = "***"
        if isinstance(out.get("ctx"), dict):
            out["ctx"] = {k: ("***" if "value" in k.lower() else v) for k, v in out["ctx"].items()}
    return out


async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request payload failed validation",
                "request_id": request_id_var.get(),
                "status": 422,
                "details": [_scrub(e) for e in exc.errors()],
            }
        },
    )


def install(app: FastAPI) -> None:
    configure_logging()
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(
        RequestValidationError, validation_exception_handler
    )
