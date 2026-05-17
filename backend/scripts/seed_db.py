import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.base import Base
# Import all models to ensure they are registered with Base
from app.models import *
from app.mock_data import CUSTOMERS, ONT_STATUS, CALLS, LABELS, SAVED_REPLIES, CONTACTS, CONVERSATIONS, FAQS, USERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

async def seed_db():
    if not settings.effective_database_url:
        logger.error("No database URL configured!")
        return

    raw_url = settings.effective_database_url
    url = raw_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(url, echo=False)
    
    # Create all tables (in a real scenario, Alembic handles this, but for testing we can create them)
    from sqlalchemy import text
    async with engine.begin() as conn:
        logger.info("Creating schema dh...")
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS dh"))
        logger.info("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        logger.info("Seeding data...")
        
        # We can write simple loops to insert the data into the models.
        # But wait, we just want to create the scaffolding for the user to run.
        # Customers
        for cid, data in CUSTOMERS.items():
            # Check if exists
            cust = await session.get(Customer, cid)
            if not cust:
                session.add(Customer(
                    customer_id=data["customer_id"],
                    name=data["name"],
                    mobile=data["mobile"],
                    smartcard=data["smartcard"],
                    address=data["address"],
                    package=data["package"],
                    balance_npr=data["balance_npr"],
                    due_date=datetime.strptime(data["due_date"], "%Y-%m-%d").date() if data.get("due_date") else None,
                    status=data["status"],
                    ont_id=data["ont_id"]
                ))
                
        # Users
        for uname, udata in USERS.items():
            u = await session.get(User, uname)
            if not u:
                session.add(User(
                    username=udata["username"],
                    full_name=udata["name"],
                    email=udata["email"],
                    role=udata["role"],
                    password_hash=udata["password"]
                ))
        
        # Commit
        await session.commit()
        logger.info("Seeding completed.")

if __name__ == "__main__":
    asyncio.run(seed_db())
