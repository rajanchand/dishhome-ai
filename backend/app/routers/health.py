from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app import database
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness() -> dict[str, str | bool]:
    if settings.effective_database_url and database.engine is None:
        raise HTTPException(503, "Database engine is not initialized")
    if settings.effective_database_url and database.engine is not None:
        try:
            async with database.engine.connect() as conn:
                await conn.execute(text("select 1"))
        except Exception:
            raise HTTPException(503, "Database readiness check failed")
    return {"status": "ok", "database": bool(settings.effective_database_url)}
