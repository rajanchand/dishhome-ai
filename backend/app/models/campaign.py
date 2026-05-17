from sqlalchemy import Column, String, Integer, Float, JSON
from .base import Base

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    type = Column(String, nullable=False)
    audience_size = Column(Integer, nullable=False)
    completed = Column(Integer, nullable=False)
    success_rate = Column(Float, nullable=False)
    created_at = Column(String, nullable=False)

class CampaignContact(Base):
    __tablename__ = "campaign_contacts"

    id = Column(String, primary_key=True)
    campaign_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    mobile = Column(String, nullable=False)
    status = Column(String, nullable=False)
    last_attempt = Column(String, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    result = Column(String, nullable=True)
