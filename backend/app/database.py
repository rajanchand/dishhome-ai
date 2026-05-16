import logging
from typing import Optional

import asyncpg

from app.config import settings

log = logging.getLogger("dishhome.db")

_pool: Optional[asyncpg.Pool] = None


async def connect_db():
    """Initialize the asyncpg connection pool."""
    global _pool
    if not settings.database_url:
        log.warning("No DATABASE_URL provided. Database will not be connected.")
        return

    try:
        log.info("Connecting to Supabase Postgres (Connection Pooling)...")
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        log.info("Successfully connected to Postgres pool.")
    except Exception as e:
        log.error(f"Failed to connect to database: {e}")
        raise


async def disconnect_db():
    """Close the asyncpg connection pool."""
    global _pool
    if _pool:
        log.info("Closing database connection pool.")
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Get the initialized asyncpg connection pool."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Did you call connect_db()?")
    return _pool
