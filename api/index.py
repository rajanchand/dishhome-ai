import sys
import os

# ── Setup Paths ──────────────────────────────────────────────────────
# Add the project root and backend folder to sys.path
_here = os.path.dirname(os.path.abspath(__file__))
_parent = os.path.dirname(_here)

if _parent not in sys.path:
    sys.path.insert(0, _parent)
if os.path.join(_parent, "backend") not in sys.path:
    sys.path.insert(0, os.path.join(_parent, "backend"))

# ── Import Real App ──────────────────────────────────────────────────
try:
    from app.main import app as _real_app
except Exception as e:
    import traceback
    _error = traceback.format_exc()
    _real_app = None

async def app(scope, receive, send):
    """ASGI wrapper: strip /api prefix so routes match."""
    if _real_app is None:
        if scope["type"] != "http": return
        body = f"BOOT ERROR:\n\n{_error}".encode()
        await send({"type": "http.response.start", "status": 500, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": body})
        return

    if scope["type"] in ("http", "websocket"):
        path = scope.get("path", "/")
        if path.startswith("/api"):
            scope = dict(scope)
            scope["path"] = path[4:] or "/"
            scope["root_path"] = "/api"
    
    await _real_app(scope, receive, send)
