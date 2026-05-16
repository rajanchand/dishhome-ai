from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "dh"}

    username: Mapped[str] = mapped_column(String(80), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, server_default="agent")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = {"schema": "dh"}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # token
    username: Mapped[str] = mapped_column(String(80), ForeignKey("dh.users.username"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
