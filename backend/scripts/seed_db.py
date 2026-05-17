import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.base import Base
# Import all models to ensure they are registered with Base
from app.models import *
from app.mock_data import CUSTOMERS, ONT_STATUS, CALLS, LABELS, SAVED_REPLIES, CONTACTS, CONVERSATIONS, FAQS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

async def seed_db():
    if not settings.effective_database_url:
        logger.error("No database URL configured!")
        return

    engine = create_async_engine(settings.effective_database_url, echo=False)
    
    # Create all tables (in a real scenario, Alembic handles this, but for testing we can create them)
    async with engine.begin() as conn:
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
                    status=data["status"],
                    ont_id=data["ont_id"]
                ))
        
        # Commit
        await session.commit()
        logger.info("Seeding completed.")

if __name__ == "__main__":
    asyncio.run(seed_db())
