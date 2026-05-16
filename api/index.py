"""Vercel serverless entrypoint — exposes the FastAPI app for @vercel/python."""
import sys # Force rebuild 1
import os

# ── Setup Paths ──────────────────────────────────────────────────────
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)

for p in [_root, os.path.join(_root, "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ── Import ───────────────────────────────────────────────────────────
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

# Top-level assignment so Vercel's static analysis always finds `app`.
app = FastAPI(title="DishHome AI Call Center")

try:
    from app.main import app as _real_app

    _real_app.root_path = "/api"
    app = _real_app
except Exception:
    import traceback
    _tb = traceback.format_exc()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def _boot_error(path: str):
        return PlainTextResponse(
            f"BOOT ERROR — the backend failed to start.\n\n{_tb}",
            status_code=500,
        )
