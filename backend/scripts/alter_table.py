import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

async def run():
    url = settings.effective_database_url.replace('postgresql://', 'postgresql+asyncpg://')
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE dh.sessions ALTER COLUMN token TYPE VARCHAR(500)"))

asyncio.run(run())
