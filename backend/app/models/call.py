from datetime import datetime
from sqlalchemy import DateTime, String, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import Base

class Call(Base):
    __tablename__ = "calls"
    __table_args__ = {"schema": "dh"}

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # Twilio/FreeSWITCH Call SID
    customer_id: Mapped[str] = mapped_column(index=True, nullable=True)
    customer_name: Mapped[str] = mapped_column(nullable=True)
    phone_number: Mapped[str] = mapped_column("caller_number", String(50), index=True)
    called_number: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(default="ringing")  # ringing, in-progress, completed, failed
    
    start_time: Mapped[datetime] = mapped_column("started_at", DateTime(timezone=True), server_default=func.now())
    end_time: Mapped[datetime] = mapped_column("ended_at", DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int] = mapped_column("duration_sec", nullable=True)
    
    # AI Metadata
    language: Mapped[str] = mapped_column(default="ne")
    sentiment: Mapped[str] = mapped_column(String(50), nullable=True)
    transcript: Mapped[list[dict]] = mapped_column(JSON, default=list)  # List of {speaker: str, text: str, ts: str}
    intent: Mapped[str] = mapped_column(String(100), nullable=True)
    ai_confidence: Mapped[float] = mapped_column(Numeric(5, 3), nullable=True)
    resolution: Mapped[str] = mapped_column(nullable=True)
