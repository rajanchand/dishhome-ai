"""Huawei OLT / ONT adapter.

In production this module shells out to Huawei iManager U2000 (or NCE) over
its NETCONF / SOAP / SNMP interfaces, or to vendor-specific TR-069 ACS
endpoints. Here we serve realistic responses from mock_data.

The endpoints are split into two groups:
  - /huawei/onts/{ont_id}       — per-device telemetry, reboot, WiFi control
  - /huawei/olts                — master/uplink status
  - /huawei/diagnose/{customer} — high-level "what's wrong" rollup the AI uses
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.mock_data import (
    CUSTOMERS,
    OLT_STATUS,
    ONT_STATUS,
    SCENARIO_BLURBS,
    find_customer,
)
from app.routers.auth import UserOut, current_user

router = APIRouter(prefix="/huawei", tags=["huawei"])


class HuaweiOnt(BaseModel):
    ont_id: str
    device_model: str
    serial_number: str
    firmware_version: str
    hardware_version: str
    olt_id: str
    olt_port: str
    ont_index: int
    online: bool
    rx_power_dbm: float | None
    tx_power_dbm: float | None
    line_attenuation_db: float | None
    uptime_hours: int
    last_reboot: str
    pppoe_session: str
    wifi_radio_2g: bool
    wifi_radio_5g: bool
    error_state: str | None
    area_outage: bool


class HuaweiOlt(BaseModel):
    olt_id: str
    site: str
    online: bool
    active_onts: int
    uptime_hours: int
    degraded: bool = False


class DiagnosisResponse(BaseModel):
    customer_id: str
    ont_id: str
    scenario: str
    headline: str
    tone: str
    advice: str
    recommended_action: Literal[
        "remote_reboot",
        "wait_for_outage",
        "escalate_noc",
        "dispatch_field",
        "reauth_pppoe",
        "remote_wifi_toggle",
        "none",
    ]
    ont: HuaweiOnt
    olt: HuaweiOlt | None


class WifiToggleRequest(BaseModel):
    radio: Literal["2g", "5g"]
    enabled: bool


def _ont_or_404(ont_id: str) -> dict:
    o = ONT_STATUS.get(ont_id)
    if not o:
        raise HTTPException(404, f"Huawei ONT {ont_id} not found")
    return o


@router.get("/onts/{ont_id}", response_model=HuaweiOnt)
def get_ont(
    ont_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> HuaweiOnt:
    return HuaweiOnt(**_ont_or_404(ont_id))


@router.get("/olts", response_model=list[HuaweiOlt])
def list_olts(_: Annotated[UserOut, Depends(current_user)]) -> list[HuaweiOlt]:
    return [HuaweiOlt(**o) for o in OLT_STATUS.values()]


@router.get("/olts/{olt_id}", response_model=HuaweiOlt)
def get_olt(
    olt_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> HuaweiOlt:
    o = OLT_STATUS.get(olt_id)
    if not o:
        raise HTTPException(404, f"OLT {olt_id} not found")
    return HuaweiOlt(**o)


@router.post("/onts/{ont_id}/reboot")
def reboot(
    ont_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> dict[str, str]:
    _ont_or_404(ont_id)
    return {
        "ont_id": ont_id,
        "status": "reboot_command_sent",
        "expected_back_online_sec": "120",
        "via": "iManager U2000 TR-069",
    }


@router.post("/onts/{ont_id}/wifi")
def toggle_wifi(
    ont_id: str,
    payload: WifiToggleRequest,
    _: Annotated[UserOut, Depends(current_user)],
) -> dict[str, str | bool]:
    o = _ont_or_404(ont_id)
    key = f"wifi_radio_{payload.radio}"
    o[key] = payload.enabled
    return {
        "ont_id": ont_id,
        "radio": payload.radio,
        "enabled": payload.enabled,
        "status": "ok",
    }


@router.post("/onts/{ont_id}/reauth-pppoe")
def reauth_pppoe(
    ont_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> dict[str, str]:
    o = _ont_or_404(ont_id)
    if o["pppoe_session"] != "active":
        o["pppoe_session"] = "active"
    return {
        "ont_id": ont_id,
        "status": "session_reset",
        "via": "FreeRADIUS POD",
    }


@router.get("/diagnose/{customer_query}", response_model=DiagnosisResponse)
def diagnose(
    customer_query: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> DiagnosisResponse:
    """High-level "what's wrong" lookup the AI tool-calls during a live call."""
    cust = find_customer(customer_query)
    if not cust:
        raise HTTPException(404, "Customer not found")
    ont = ONT_STATUS.get(cust["ont_id"])
    if not ont:
        raise HTTPException(404, "Customer's ONT not found")
    scenario = ont.get("scenario", "healthy")
    blurb = SCENARIO_BLURBS.get(scenario, SCENARIO_BLURBS["healthy"])
    recommended = {
        "healthy": "none",
        "router_offline": "dispatch_field",
        "area_outage": "wait_for_outage",
        "master_down": "escalate_noc",
        "network_down": "escalate_noc",
        "low_power": "dispatch_field",
        "pppoe_disconnected": "reauth_pppoe",
        "wifi_only_issue": "remote_wifi_toggle",
    }.get(scenario, "none")
    olt = OLT_STATUS.get(ont["olt_id"])
    return DiagnosisResponse(
        customer_id=cust["customer_id"],
        ont_id=ont["ont_id"],
        scenario=scenario,
        headline=blurb["headline"],
        tone=blurb["tone"],
        advice=blurb["advice"],
        recommended_action=recommended,
        ont=HuaweiOnt(**ont),
        olt=HuaweiOlt(**olt) if olt else None,
    )


@router.get("/customers")
def list_demo_customers(
    _: Annotated[UserOut, Depends(current_user)],
) -> list[dict]:
    """Demo helper: a flat list of every seeded customer + their scenario."""
    out = []
    for c in CUSTOMERS.values():
        ont = ONT_STATUS.get(c["ont_id"], {})
        scenario = ont.get("scenario", "unknown")
        blurb = SCENARIO_BLURBS.get(scenario, {})
        out.append(
            {
                "customer_id": c["customer_id"],
                "name": c["name"],
                "mobile": c["mobile"],
                "address": c["address"],
                "package": c["package"],
                "ont_id": c["ont_id"],
                "device_model": ont.get("device_model"),
                "scenario": scenario,
                "headline": blurb.get("headline", ""),
                "tone": blurb.get("tone", "info"),
                "online": ont.get("online", False),
                "rx_power_dbm": ont.get("rx_power_dbm"),
            }
        )
    return out
