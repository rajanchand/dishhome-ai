import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

log = logging.getLogger("dishhome.db")

from .models.base import Base

engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None

async def connect_db():
    """Initialize the SQLAlchemy async engine and session factory."""
    global engine, async_session_maker
    if not settings.database_url:
        log.warning("No DATABASE_URL provided. Database will not be connected.")
        return

    try:
        log.info("Connecting to Supabase Postgres (SQLAlchemy 2.0)...")
        # Ensure the URL uses asyncpg
        url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
        
        # Remove pgbouncer query parameter as asyncpg doesn't support it
        if "pgbouncer=" in url:
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qsl(parsed.query)
            filtered_params = [kv for kv in query_params if kv[0] != "pgbouncer"]
            new_query = urllib.parse.urlencode(filtered_params)
            url = urllib.parse.ParseResult(
                scheme=parsed.scheme,
                netloc=parsed.netloc,
                path=parsed.path,
                params=parsed.params,
                query=new_query,
                fragment=parsed.fragment
            ).geturl()
        
        import uuid
        engine = create_async_engine(
            url,
            pool_size=10,
            max_overflow=20,
            pool_timeout=60,
            pool_recycle=1800,
            echo=False,
            connect_args={
                "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
                "statement_cache_size": 0,
            }
        )
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
        )
        log.info("Successfully connected to Postgres via SQLAlchemy.")
    except Exception as e:
        log.error(f"Failed to connect to database: {e}")
        raise

async def disconnect_db():
    """Dispose of the SQLAlchemy async engine."""
    global engine
    if engine:
        log.info("Disposing SQLAlchemy engine.")
        await engine.dispose()
        engine = None

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection for FastAPI routes to get a database session."""
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call connect_db() during lifespan.")
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
