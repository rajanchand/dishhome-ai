import sys
import os
import traceback

# ── Setup Paths ──────────────────────────────────────────────────────
cwd = os.getcwd()
here = os.path.dirname(os.path.abspath(__file__))
parent = os.path.dirname(here)

# Add paths to help diagnostics if it fails
sys.path.insert(0, parent)
sys.path.insert(0, os.path.join(parent, "backend"))

# ── Try to Import Real App ───────────────────────────────────────────
_real_app = None
_error = None
try:
    from app.main import app as _real_app
except Exception:
    _error = traceback.format_exc()

async def app(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            msg = await receive()
            if msg["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif msg["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    
    if scope["type"] != "http":
        return

    # If we have an error or no app, return diagnostic text
    if _error or not _real_app:
        body = f"BOOT ERROR:\n\n{_error}\n\nCWD: {cwd}\nSYS.PATH: {sys.path}".encode()
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [
                (b"content-type", b"text/plain"),
                (b"access-control-allow-origin", b"*"),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
        return

    # Normal routing: strip /api prefix
    if scope["type"] == "http":
        path = scope.get("path", "/")
        if path.startswith("/api"):
            scope = dict(scope)
            scope["path"] = path[4:] or "/"
            scope["root_path"] = "/api"
    
    await _real_app(scope, receive, send)
