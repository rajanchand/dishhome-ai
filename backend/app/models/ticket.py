from datetime import datetime
from sqlalchemy import DateTime, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # e.g., TKT-123456
    customer_id: Mapped[str] = mapped_column(index=True)
    issue: Mapped[str] = mapped_column()
    priority: Mapped[str] = mapped_column(default="medium")  # low, medium, high, critical
    status: Mapped[str] = mapped_column(default="open")  # open, assigned, resolved, closed
    
    assigned_team: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Link to the call that created the ticket
    call_id: Mapped[str] = mapped_column(ForeignKey("calls.id"), nullable=True)
