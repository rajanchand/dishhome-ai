import sys
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# ── Setup Paths ──────────────────────────────────────────────────────
# Add the project root and backend folder to sys.path
parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent)
sys.path.insert(0, os.path.join(parent, "backend"))

# Create the wrapper app
app = FastAPI()

# Add CORS to the wrapper
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Import Real App ──────────────────────────────────────────────────
try:
    from app.main import app as real_app
    
    # Mount the real app at /api
    # This way /api/auth/login -> real_app sees /auth/login
    app.mount("/api", real_app)
    
    # Also add a health check on the wrapper itself for testing
    @app.get("/api/health")
    async def wrapper_health():
        return {"status": "ok", "message": "Backend wrapper is active"}

except Exception as e:
    import traceback
    error_trace = traceback.format_exc()
    
    @app.get("/api/health")
    async def wrapper_error():
        return {
            "error": "Backend import failed",
            "message": str(e),
            "trace": error_trace,
            "sys_path": sys.path
        }
