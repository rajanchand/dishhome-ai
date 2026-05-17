from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "dh"}

    username: Mapped[str] = mapped_column(String(80), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column("name", String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, server_default="agent")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = {"schema": "dh"}

    token: Mapped[str] = mapped_column(String(500), primary_key=True)
    username: Mapped[str] = mapped_column(String(80), ForeignKey("dh.users.username"), nullable=False)
    issued_at: Mapped[float] = mapped_column(server_default="0")
    expires_at: Mapped[float] = mapped_column(nullable=False)
    last_seen: Mapped[float] = mapped_column(server_default="0")
    issued_ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(1024))
    last_ip: Mapped[str | None] = mapped_column(String(45))
