"""DishHome system integration endpoints (billing/CRM, OSS, ticketing).

Mocked in this scaffold. Real impl plugs into your existing internal APIs.
"""

import secrets
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, or_, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.customer import Customer as CustomerModel, ONTStatus as ONTStatusModel
from app.models.ticket import Ticket as TicketModel
from app.routers.auth import UserOut, current_user

router = APIRouter(prefix="/integrations", tags=["integrations"])


class Customer(BaseModel):
    customer_id: str
    name: str
    mobile: str
    smartcard: str
    address: str
    package: str
    balance_npr: float
    due_date: str
    status: str
    ont_id: str


class RouterStatus(BaseModel):
    ont_id: str
    online: bool
    rx_power_dbm: float | None
    tx_power_dbm: float | None
    uptime_hours: int
    last_reboot: str
    pppoe_session: str
    area_outage: bool


class TicketCreate(BaseModel):
    customer_id: str
    issue: str
    priority: Literal["low", "normal", "high", "critical"] = "normal"


class Ticket(BaseModel):
    id: str
    customer_id: str
    issue: str
    priority: str
    status: str
    assigned_team: str
    eta_minutes: int
    created_at: str


class IntegrationTestRequest(BaseModel):
    system: Literal["billing", "oss", "ticketing", "sms"]


class IntegrationTestResponse(BaseModel):
    system: str
    ok: bool
    latency_ms: int
    message: str


@router.get("/dishhome/customer/{query}", response_model=Customer)
async def lookup_customer(
    query: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[UserOut, Depends(current_user)],
) -> Customer:
    """Lookup by customer_id, mobile, or smartcard."""
    q = (query or "").strip()
    if not q:
         raise HTTPException(404, "Customer not found")

    result = await db.execute(
        select(CustomerModel).where(
            or_(
                CustomerModel.customer_id == q,
                CustomerModel.mobile == q,
                CustomerModel.smartcard == q
            )
        )
    )
    cust = result.scalar_one_or_none()
    
    if not cust:
        raise HTTPException(404, "Customer not found")
        
    return Customer(
        customer_id=cust.customer_id,
        name=cust.name,
        mobile=cust.mobile,
        smartcard=cust.smartcard,
        address=cust.address,
        package=cust.package,
        balance_npr=cust.balance_npr,
        due_date=str(cust.due_date) if cust.due_date else "",
        status=cust.status,
        ont_id=cust.ont_id or ""
    )


@router.get("/dishhome/router-status/{ont_id}", response_model=RouterStatus)
async def router_status(
    ont_id: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[UserOut, Depends(current_user)],
) -> RouterStatus:
    result = await db.execute(select(ONTStatusModel).where(ONTStatusModel.ont_id == ont_id))
    row = result.scalar_one_or_none()
    
    if not row:
        raise HTTPException(404, "ONT device not found")
        
    return RouterStatus(
        ont_id=row.ont_id,
        online=row.online,
        rx_power_dbm=row.rx_power_dbm,
        tx_power_dbm=row.tx_power_dbm,
        uptime_hours=row.uptime_hours,
        last_reboot=row.last_reboot.isoformat() if row.last_reboot else "",
        pppoe_session=row.pppoe_session or "",
        area_outage=row.area_outage
    )


@router.post("/dishhome/router-reboot/{ont_id}")
async def reboot_router(
    ont_id: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[UserOut, Depends(current_user)],
) -> dict[str, str]:
    result = await db.execute(select(ONTStatusModel).where(ONTStatusModel.ont_id == ont_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "ONT device not found")
    
    await db.execute(
        update(ONTStatusModel)
        .where(ONTStatusModel.ont_id == ont_id)
        .values(last_reboot=func.now(), uptime_hours=0)
    )
    await db.commit()

    return {"ont_id": ont_id, "status": "reboot_sent", "expected_back_online_sec": "120"}


@router.post("/dishhome/ticket", response_model=Ticket)
async def create_ticket(
    payload: TicketCreate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[UserOut, Depends(current_user)],
) -> Ticket:
    result = await db.execute(select(CustomerModel).where(CustomerModel.customer_id == payload.customer_id))
    cust = result.scalar_one_or_none()
    if not cust:
        raise HTTPException(404, "Customer not found")
    
    ticket_id = f"DH-T-{secrets.randbelow(90000) + 10000}"
    eta = {"critical": 30, "high": 90, "normal": 240, "low": 1440}[payload.priority]
    team = f"{cust.address.split(',')[-1].strip()} Field Team"
    
    new_ticket = TicketModel(
        id=ticket_id,
        customer_id=payload.customer_id,
        issue=payload.issue,
        priority=payload.priority,
        status="dispatched",
        assigned_team=team
    )
    db.add(new_ticket)
    await db.commit()
    await db.refresh(new_ticket)
    
    return Ticket(
        id=new_ticket.id,
        customer_id=new_ticket.customer_id,
        issue=new_ticket.issue,
        priority=new_ticket.priority,
        status=new_ticket.status,
        assigned_team=new_ticket.assigned_team or "Unknown",
        eta_minutes=eta,
        created_at=new_ticket.created_at.isoformat()
    )


@router.get("/dishhome/tickets", response_model=list[Ticket])
async def list_tickets(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[UserOut, Depends(current_user)]
) -> list[Ticket]:
    result = await db.execute(select(TicketModel).order_by(TicketModel.created_at.desc()).limit(100))
    tickets = result.scalars().all()
    
    return [
        Ticket(
            id=t.id,
            customer_id=t.customer_id,
            issue=t.issue,
            priority=t.priority,
            status=t.status,
            assigned_team=t.assigned_team or "Unknown",
            eta_minutes=0, # In real impl, calculate from priority/team
            created_at=t.created_at.isoformat()
        )
        for t in tickets
    ]


@router.post("/test", response_model=IntegrationTestResponse)
def test_integration(
    payload: IntegrationTestRequest,
    _: Annotated[UserOut, Depends(current_user)],
) -> IntegrationTestResponse:
    # In real impl: probe the configured URL with a HEAD/health check.
    latency = secrets.randbelow(180) + 40
    return IntegrationTestResponse(
        system=payload.system,
        ok=True,
        latency_ms=latency,
        message=f"Mock {payload.system} integration reachable in {latency}ms",
    )
