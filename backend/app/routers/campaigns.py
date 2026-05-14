"""Voice-assistance campaigns (TingTing-style API).

In production the /run endpoint enqueues outbound calls onto FreeSWITCH via
mod_originate, each handed to the AI agent with the campaign script as the
opening line.

Here every endpoint is fully wired against in-memory state so the UI is
testable end-to-end.
"""

import csv
import io
import secrets
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.mock_data import CAMPAIGN_CONTACTS, CAMPAIGNS, VOICES
from app.routers.auth import UserOut, current_user

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignStats(BaseModel):
    dialed: int = 0
    connected: int = 0
    completed: int = 0
    failed: int = 0


class Campaign(BaseModel):
    id: str
    name: str
    language: Literal["ne", "en"]
    voice_id: str
    script: str
    status: Literal["draft", "running", "paused", "completed"]
    contacts_count: int
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    stats: CampaignStats


class CampaignCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    language: Literal["ne", "en"] = "ne"
    voice_id: str
    script: str = Field(min_length=10, max_length=600)


class CampaignUpdate(BaseModel):
    name: str | None = None
    language: Literal["ne", "en"] | None = None
    voice_id: str | None = None
    script: str | None = None


class CampaignContact(BaseModel):
    id: str
    name: str
    mobile: str
    status: str
    attempts: int
    outcome: str | None = None


class DemoCallRequest(BaseModel):
    mobile: str = Field(min_length=10, max_length=15)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(4)}"


def _find(camp_id: str) -> dict:
    for c in CAMPAIGNS:
        if c["id"] == camp_id:
            return c
    raise HTTPException(404, "Campaign not found")


def _voice_or_400(voice_id: str) -> None:
    if not any(v["id"] == voice_id for v in VOICES):
        raise HTTPException(400, f"Voice {voice_id!r} is not in the catalog")


@router.get("", response_model=list[Campaign])
def list_campaigns(
    _: Annotated[UserOut, Depends(current_user)],
) -> list[Campaign]:
    return [Campaign(**c) for c in CAMPAIGNS]


@router.post("", response_model=Campaign, status_code=201)
def create_campaign(
    payload: CampaignCreate,
    _: Annotated[UserOut, Depends(current_user)],
) -> Campaign:
    _voice_or_400(payload.voice_id)
    entry = {
        "id": _new_id("camp"),
        "name": payload.name,
        "language": payload.language,
        "voice_id": payload.voice_id,
        "script": payload.script,
        "status": "draft",
        "contacts_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
        "stats": {"dialed": 0, "connected": 0, "completed": 0, "failed": 0},
    }
    CAMPAIGNS.append(entry)
    CAMPAIGN_CONTACTS.setdefault(entry["id"], [])
    return Campaign(**entry)


@router.get("/{camp_id}", response_model=Campaign)
def campaign_detail(
    camp_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> Campaign:
    return Campaign(**_find(camp_id))


@router.patch("/{camp_id}", response_model=Campaign)
def update_campaign(
    camp_id: str,
    payload: CampaignUpdate,
    _: Annotated[UserOut, Depends(current_user)],
) -> Campaign:
    c = _find(camp_id)
    if c["status"] == "running":
        raise HTTPException(409, "Cannot edit a running campaign — pause it first")
    update = payload.model_dump(exclude_unset=True)
    if "voice_id" in update:
        _voice_or_400(update["voice_id"])
    c.update(update)
    return Campaign(**c)


@router.delete("/{camp_id}", status_code=204)
def delete_campaign(
    camp_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> None:
    for i, c in enumerate(CAMPAIGNS):
        if c["id"] == camp_id:
            if c["status"] == "running":
                raise HTTPException(409, "Cannot delete a running campaign")
            CAMPAIGNS.pop(i)
            CAMPAIGN_CONTACTS.pop(camp_id, None)
            return
    raise HTTPException(404, "Campaign not found")


@router.get("/{camp_id}/contacts", response_model=list[CampaignContact])
def list_contacts(
    camp_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> list[CampaignContact]:
    _find(camp_id)
    return [CampaignContact(**c) for c in CAMPAIGN_CONTACTS.get(camp_id, [])]


@router.post("/{camp_id}/contacts/upload")
async def upload_contacts(
    camp_id: str,
    user: Annotated[UserOut, Depends(current_user)],
    file: Annotated[UploadFile, File(...)],
) -> dict[str, int]:
    """CSV with columns: name, mobile."""
    _ = user
    c = _find(camp_id)
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(413, "CSV too large (>5 MB)")
    text = raw.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    added = 0
    skipped = 0
    bucket = CAMPAIGN_CONTACTS.setdefault(camp_id, [])
    for row in reader:
        name = (row.get("name") or "").strip()
        mobile = (row.get("mobile") or row.get("phone") or "").strip()
        if not name or not mobile:
            skipped += 1
            continue
        bucket.append(
            {
                "id": _new_id("cc"),
                "name": name,
                "mobile": mobile,
                "status": "queued",
                "attempts": 0,
                "outcome": None,
            }
        )
        added += 1
    c["contacts_count"] = len(bucket)
    return {"added": added, "skipped": skipped, "total": c["contacts_count"]}


@router.delete("/{camp_id}/contacts/{contact_id}", status_code=204)
def delete_contact(
    camp_id: str,
    contact_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> None:
    c = _find(camp_id)
    bucket = CAMPAIGN_CONTACTS.setdefault(camp_id, [])
    for i, cc in enumerate(bucket):
        if cc["id"] == contact_id:
            bucket.pop(i)
            c["contacts_count"] = len(bucket)
            return
    raise HTTPException(404, "Contact not in this campaign")


@router.post("/{camp_id}/demo-call")
def demo_call(
    camp_id: str,
    payload: DemoCallRequest,
    _: Annotated[UserOut, Depends(current_user)],
) -> dict[str, str]:
    """Dial a single number with the campaign script — for QA before launch."""
    c = _find(camp_id)
    return {
        "campaign_id": c["id"],
        "to": payload.mobile,
        "voice_id": c["voice_id"],
        "language": c["language"],
        "script_preview": c["script"][:120],
        "status": "queued",
        "session_id": _new_id("demo"),
    }


@router.post("/{camp_id}/run", response_model=Campaign)
def run_campaign(
    camp_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> Campaign:
    c = _find(camp_id)
    if c["status"] == "running":
        raise HTTPException(409, "Campaign already running")
    if c["contacts_count"] == 0:
        raise HTTPException(400, "No contacts uploaded — add some first")
    c["status"] = "running"
    c["started_at"] = datetime.now(timezone.utc).isoformat()
    # Simulate progress: mark half as dialed+connected, a few completed
    bucket = CAMPAIGN_CONTACTS.setdefault(camp_id, [])
    for i, cc in enumerate(bucket[:5]):
        cc["status"] = "completed" if i % 2 == 0 else "no_answer"
        cc["attempts"] = 1
        cc["outcome"] = "delivered" if cc["status"] == "completed" else None
    c["stats"]["dialed"] = min(5, len(bucket))
    c["stats"]["connected"] = max(0, c["stats"]["dialed"] - 1)
    c["stats"]["completed"] = (c["stats"]["dialed"] + 1) // 2
    c["stats"]["failed"] = c["stats"]["dialed"] - c["stats"]["completed"]
    return Campaign(**c)


@router.post("/{camp_id}/pause", response_model=Campaign)
def pause_campaign(
    camp_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> Campaign:
    c = _find(camp_id)
    if c["status"] != "running":
        raise HTTPException(409, "Only running campaigns can be paused")
    c["status"] = "paused"
    return Campaign(**c)


@router.post("/{camp_id}/report")
def download_report(
    camp_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> dict:
    c = _find(camp_id)
    bucket = CAMPAIGN_CONTACTS.setdefault(camp_id, [])
    summary = {s: 0 for s in ("queued", "completed", "no_answer", "failed")}
    for cc in bucket:
        summary[cc["status"]] = summary.get(cc["status"], 0) + 1
    return {
        "campaign_id": c["id"],
        "name": c["name"],
        "totals": summary,
        "stats": c["stats"],
        "contacts": bucket,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
