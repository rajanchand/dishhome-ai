"""Vercel serverless entry-point.

Vercel rewrites /api/* to this function. We strip the /api prefix 
at the ASGI level so the real FastAPI app (which doesn't know about /api)
can handle the routes correctly.
"""

import sys
import os
import traceback

# ── Setup Paths ──────────────────────────────────────────────────────
# On Vercel, the function runs in /var/task. The backend/ folder is a 
# sibling to the api/ folder if included correctly.
cwd = os.getcwd()
here = os.path.dirname(os.path.abspath(__file__))
parent = os.path.dirname(here)

# Log paths to help diagnostics if it fails
sys.path.insert(0, parent)
sys.path.insert(0, os.path.join(parent, "backend"))

# ── Import Real App ──────────────────────────────────────────────────
try:
    from app.main import app as _real_app

    async def app(scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "/")
            # Strip /api prefix if present
            if path.startswith("/api"):
                scope = dict(scope)
                scope["path"] = path[4:] or "/"
                # Ensure the app knows where it is
                scope["root_path"] = "/api"
        
        await _real_app(scope, receive, send)

except Exception:
    error_trace = traceback.format_exc()
    
    async def app(scope, receive, send):
        if scope["type"] != "http":
            return
        
        # Diagnostic response
        import json
        payload = json.dumps({
            "error": "Backend Boot Failure",
            "trace": error_trace,
            "sys_path": sys.path,
            "cwd": cwd,
            "contents": os.listdir(cwd) if os.path.exists(cwd) else "cwd_missing",
            "parent_contents": os.listdir(parent) if os.path.exists(parent) else "parent_missing"
        }).encode()
        
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [
                (b"content-type", b"application/json"),
                (b"access-control-allow-origin", b"*"),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": payload,
        })
