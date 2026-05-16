from datetime import datetime
from sqlalchemy import DateTime, String, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import Base

class Call(Base):
    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # Twilio/FreeSWITCH Call SID
    customer_id: Mapped[str] = mapped_column(index=True, nullable=True)
    customer_name: Mapped[str] = mapped_column(nullable=True)
    phone_number: Mapped[str] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(default="ringing")  # ringing, in-progress, completed, failed
    
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(nullable=True)
    
    # AI Metadata
    language: Mapped[str] = mapped_column(default="ne")
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=True)
    transcript: Mapped[list[dict]] = mapped_column(JSON, default=list)  # List of {speaker: str, text: str, ts: str}
    summary: Mapped[str] = mapped_column(nullable=True)
    
    recording_url: Mapped[str] = mapped_column(nullable=True)
