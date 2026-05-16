"""Vercel serverless entrypoint — exposes the FastAPI app for @vercel/python.

@vercel/python recognizes ASGI apps automatically when the module-level
variable is named `app`. We strip the /api prefix via FastAPI's root_path
so all routes work transparently.
"""
import sys
import os

# ── Setup Paths ──────────────────────────────────────────────────────
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)

# Add project root and backend/ to sys.path so `from app.main import app` works.
for p in [_root, os.path.join(_root, "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ── Import ───────────────────────────────────────────────────────────
try:
    from app.main import app  # noqa: F811 — FastAPI instance

    # Tell FastAPI it's mounted at /api so redirects etc. work correctly.
    app.root_path = "/api"
except Exception:
    # If the real app can't boot, surface the error as a plain-text 500
    # so it's diagnosable instead of silently returning index.html.
    import traceback
    _tb = traceback.format_exc()

    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse

    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def _boot_error(path: str):
        return PlainTextResponse(
            f"BOOT ERROR — the backend failed to start.\n\n{_tb}",
            status_code=500,
        )
