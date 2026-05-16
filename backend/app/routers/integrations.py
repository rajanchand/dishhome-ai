"""DishHome system integration endpoints (billing/CRM, OSS, ticketing).

Mocked in this scaffold. Real impl plugs into your existing internal APIs.
"""

import secrets
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.mock_data import ONT_STATUS, TICKETS, find_customer
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
    _: Annotated[UserOut, Depends(current_user)],
) -> Customer:
    """Lookup by customer_id, mobile, or smartcard."""
    q = (query or "").strip()
    if not q:
         raise HTTPException(404, "Customer not found")

    from app.database import get_pool
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT customer_id, name, mobile, smartcard, address, package, 
                   balance_npr, due_date, status, ont_id
            FROM dh.customers
            WHERE customer_id = $1 OR mobile = $1 OR smartcard = $1
            """,
            q
        )
    if not row:
        raise HTTPException(404, "Customer not found")
        
    return Customer(
        customer_id=row["customer_id"],
        name=row["name"],
        mobile=row["mobile"],
        smartcard=row["smartcard"],
        address=row["address"],
        package=row["package"],
        balance_npr=row["balance_npr"],
        due_date=str(row["due_date"]) if row["due_date"] else "",
        status=row["status"],
        ont_id=row["ont_id"]
    )


@router.get("/dishhome/router-status/{ont_id}", response_model=RouterStatus)
async def router_status(
    ont_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> RouterStatus:
    from app.database import get_pool
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT ont_id, online, rx_power_dbm, tx_power_dbm, uptime_hours, 
                   last_reboot, pppoe_session, area_outage
            FROM dh.ont_status
            WHERE ont_id = $1
            """,
            ont_id
        )
    if not row:
        raise HTTPException(404, "ONT device not found")
        
    return RouterStatus(
        ont_id=row["ont_id"],
        online=row["online"],
        rx_power_dbm=row["rx_power_dbm"],
        tx_power_dbm=row["tx_power_dbm"],
        uptime_hours=row["uptime_hours"],
        last_reboot=row["last_reboot"].isoformat() if row["last_reboot"] else "",
        pppoe_session=row["pppoe_session"] or "",
        area_outage=row["area_outage"]
    )


@router.post("/dishhome/router-reboot/{ont_id}")
async def reboot_router(
    ont_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> dict[str, str]:
    from app.database import get_pool
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT ont_id FROM dh.ont_status WHERE ont_id = $1", ont_id)
        if not row:
            raise HTTPException(404, "ONT device not found")
            
        await conn.execute("UPDATE dh.ont_status SET last_reboot = NOW(), uptime_hours = 0 WHERE ont_id = $1", ont_id)

    return {"ont_id": ont_id, "status": "reboot_sent", "expected_back_online_sec": "120"}


@router.post("/dishhome/ticket", response_model=Ticket)
def create_ticket(
    payload: TicketCreate,
    _: Annotated[UserOut, Depends(current_user)],
) -> Ticket:
    cust = find_customer(payload.customer_id)
    if not cust:
        raise HTTPException(404, "Customer not found")
    ticket_id = f"DH-T-{secrets.randbelow(90000) + 10000}"
    eta = {"critical": 30, "high": 90, "normal": 240, "low": 1440}[payload.priority]
    team = f"{cust['address'].split(',')[-1].strip()} Field Team"
    ticket = {
        "id": ticket_id,
        "customer_id": payload.customer_id,
        "issue": payload.issue,
        "priority": payload.priority,
        "status": "dispatched",
        "assigned_team": team,
        "eta_minutes": eta,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    TICKETS.append(ticket)
    return Ticket(**ticket)


@router.get("/dishhome/tickets", response_model=list[Ticket])
def list_tickets(_: Annotated[UserOut, Depends(current_user)]) -> list[Ticket]:
    return [Ticket(**t) for t in TICKETS]


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
