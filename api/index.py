"""Vercel serverless entry-point.

Vercel rewrites /api/* to this function.  The ASGI scope still contains
the *original* request path (e.g. /api/auth/login), so we mount the
real FastAPI app at the /api prefix so its routes (e.g. /auth/login)
match correctly after the prefix is stripped.
"""

import sys
import os
import traceback

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

# ── Try to import and mount the real app ─────────────────────────────
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

# Add permissive CORS for the outer wrapper – the real app has its own
# CORS middleware too, but when mounted as a sub-app the outer app
# needs to handle OPTIONS preflight that arrives *before* routing into
# the sub-app.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from app.main import app as real_app
    # Mount at /api so that /api/auth/login → real_app sees /auth/login
    app.mount("/api", real_app)
except Exception as e:
    error_trace = traceback.format_exc()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
    async def catch_all(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Backend initialization failed",
                "message": str(e),
                "traceback": error_trace,
                "cwd": os.getcwd(),
                "file": __file__,
                "sys_path": sys.path[:6],
                "candidates": _candidates,
                "found_backend": [os.path.exists(p) for p in _candidates],
            },
        )
