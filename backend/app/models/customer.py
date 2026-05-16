from datetime import datetime
from sqlalchemy import String, Float, Date, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import Base

class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "dh"}

    customer_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mobile: Mapped[str] = mapped_column(String(20), index=True)
    smartcard: Mapped[str] = mapped_column(String(20), index=True)
    address: Mapped[str] = mapped_column(String(512))
    package: Mapped[str] = mapped_column(String(100))
    balance_npr: Mapped[float] = mapped_column(Float, default=0.0)
    due_date: Mapped[datetime.date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")
    ont_id: Mapped[str | None] = mapped_column(String(50))

class ONTStatus(Base):
    __tablename__ = "ont_status"
    __table_args__ = {"schema": "dh"}

    ont_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    online: Mapped[bool] = mapped_column(Boolean, default=False)
    rx_power_dbm: Mapped[float | None] = mapped_column(Float)
    tx_power_dbm: Mapped[float | None] = mapped_column(Float)
    uptime_hours: Mapped[int] = mapped_column(default=0)
    last_reboot: Mapped[datetime | None] = mapped_column(server_default=func.now())
    pppoe_session: Mapped[str | None] = mapped_column(String(50))
    area_outage: Mapped[bool] = mapped_column(Boolean, default=False)
