from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class SystemConfigEntry(Base):
    """A single runtime config override.

    `key` is one of the whitelisted names defined in
    `app.services.runtime_config.SUPPORTED_KEYS`. A non-empty `value`
    overrides the matching env var; an empty `value` row is treated as
    "no override" (we keep it so the audit trail survives).
    """

    __tablename__ = "system_config"
    __table_args__ = {"schema": "dh"}

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str | None] = mapped_column(
        String(80), ForeignKey("dh.users.username", ondelete="SET NULL"), nullable=True
    )
