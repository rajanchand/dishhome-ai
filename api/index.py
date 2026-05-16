"""Vercel serverless entrypoint — exposes the FastAPI app for @vercel/python."""
import sys
import os

# ── Setup Paths ──────────────────────────────────────────────────────
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)

for p in [_root, os.path.join(_root, "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ── Import ───────────────────────────────────────────────────────────
# Vercel requires a top-level `app` variable — declare it here so
# static analysis always finds it, even if the real import fails.
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app: FastAPI  # top-level declaration for Vercel detection

try:
    from app.main import app as _real_app  # noqa: F811

    _real_app.root_path = "/api"
    app = _real_app
except Exception:
    import traceback

    _tb = traceback.format_exc()
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def _boot_error(path: str):
        return PlainTextResponse(
            f"BOOT ERROR — the backend failed to start.\n\n{_tb}",
            status_code=500,
        )
