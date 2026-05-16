"""Vercel serverless entry-point.

Vercel rewrites /api/* to this function.  The ASGI scope still carries
the *original* request path (e.g. /api/auth/login), but the real
FastAPI app defines routes without the /api prefix (/auth/login).

We solve this with a thin ASGI wrapper that strips "/api" from the
incoming path before delegating to the real app.
"""

import sys
import os

# ── Make the backend package importable ──────────────────────────────
_here = os.path.dirname(os.path.abspath(__file__))
_candidates = [
    os.path.join(_here, "backend"),
    os.path.join(_here, "..", "backend"),
    os.path.join(os.getcwd(), "backend"),
]
for p in _candidates:
    if p not in sys.path:
        sys.path.insert(0, p)

# ── Try to import the real app ───────────────────────────────────────
try:
    from app.main import app as _real_app

    async def app(scope, receive, send):
        """ASGI wrapper: strip /api prefix so routes match."""
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "/")
            if path.startswith("/api"):
                scope = dict(scope)
                scope["path"] = path[4:] or "/"
                scope["root_path"] = scope.get("root_path", "") + "/api"
        await _real_app(scope, receive, send)

except Exception as _boot_err:
    import traceback as _tb
    _boot_trace = _tb.format_exc()

    async def app(scope, receive, send):
        """Fallback: return a diagnostic JSON payload."""
        if scope["type"] == "lifespan":
            # Accept lifespan but do nothing
            while True:
                msg = await receive()
                if msg["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif msg["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        if scope["type"] != "http":
            return
        import json
        body = json.dumps({
            "error": "Backend initialization failed",
            "message": str(_boot_err),
            "traceback": _boot_trace,
            "cwd": os.getcwd(),
            "candidates": _candidates,
            "found": [os.path.exists(p) for p in _candidates],
        }).encode()
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [
                [b"content-type", b"application/json"],
                [b"access-control-allow-origin", b"*"],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
