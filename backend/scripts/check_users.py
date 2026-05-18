import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.config import settings
from app.models.user import User

async def run():
    url = settings.effective_database_url.replace('postgresql://', 'postgresql+asyncpg://')
    engine = create_async_engine(url)
    async with AsyncSession(engine) as s:
        res = await s.execute(select(User))
        users = res.scalars().all()
        print([u.username for u in users])

asyncio.run(run())
