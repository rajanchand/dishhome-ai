from datetime import datetime
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import Base

class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = {"schema": "dh"}

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # e.g., TKT-123456
    customer_id: Mapped[str] = mapped_column(index=True)
    issue: Mapped[str] = mapped_column()
    priority: Mapped[str] = mapped_column(default="medium")  # low, medium, high, critical
    status: Mapped[str] = mapped_column(default="open")  # open, assigned, resolved, closed
    
    assigned_team: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
