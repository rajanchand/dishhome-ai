"""Contacts, labels, saved replies, and a lightweight inbox (conversations).

The frontend's Contacts / Saved replies / Inbox pages read from here.
"""

import secrets
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.mock_data import CONTACTS, CONVERSATIONS, LABELS, SAVED_REPLIES
from app.routers.auth import UserOut, current_user

router = APIRouter(tags=["inbox"])


# ---------------- Labels ----------------
class Label(BaseModel):
    id: str
    name: str
    color: str


class LabelCreate(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    color: str = "#0ea5e9"


@router.get("/labels", response_model=list[Label])
def list_labels(_: Annotated[UserOut, Depends(current_user)]) -> list[Label]:
    return [Label(**l) for l in LABELS]


@router.post("/labels", response_model=Label, status_code=201)
def create_label(
    payload: LabelCreate,
    _: Annotated[UserOut, Depends(current_user)],
) -> Label:
    entry = {"id": f"lbl_{secrets.token_hex(3)}", **payload.model_dump()}
    LABELS.append(entry)
    return Label(**entry)


@router.delete("/labels/{label_id}", status_code=204)
def delete_label(
    label_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> None:
    for i, l in enumerate(LABELS):
        if l["id"] == label_id:
            LABELS.pop(i)
            return
    raise HTTPException(404, "Label not found")


# ---------------- Saved replies ----------------
class SavedReply(BaseModel):
    id: str
    title: str
    body: str
    language: Literal["ne", "en"] = "ne"


class SavedReplyCreate(BaseModel):
    title: str = Field(min_length=2, max_length=80)
    body: str = Field(min_length=2, max_length=600)
    language: Literal["ne", "en"] = "ne"


@router.get("/saved-replies", response_model=list[SavedReply])
def list_replies(
    _: Annotated[UserOut, Depends(current_user)],
) -> list[SavedReply]:
    return [SavedReply(**r) for r in SAVED_REPLIES]


@router.post("/saved-replies", response_model=SavedReply, status_code=201)
def create_reply(
    payload: SavedReplyCreate,
    _: Annotated[UserOut, Depends(current_user)],
) -> SavedReply:
    entry = {"id": f"rep_{secrets.token_hex(3)}", **payload.model_dump()}
    SAVED_REPLIES.append(entry)
    return SavedReply(**entry)


@router.delete("/saved-replies/{rep_id}", status_code=204)
def delete_reply(
    rep_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> None:
    for i, r in enumerate(SAVED_REPLIES):
        if r["id"] == rep_id:
            SAVED_REPLIES.pop(i)
            return
    raise HTTPException(404, "Reply not found")


# ---------------- Contacts ----------------
class Contact(BaseModel):
    id: str
    name: str
    mobile: str
    email: str | None
    customer_id: str | None
    labels: list[str]
    last_contacted_at: str | None
    notes: str | None = None


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    mobile: str = Field(min_length=10, max_length=15)
    email: str | None = None
    customer_id: str | None = None
    labels: list[str] = []
    notes: str | None = None


@router.get("/contacts", response_model=list[Contact])
def list_contacts(
    _: Annotated[UserOut, Depends(current_user)],
    label: str | None = None,
    q: str | None = None,
) -> list[Contact]:
    out = list(CONTACTS)
    if label:
        out = [c for c in out if label in c["labels"]]
    if q:
        ql = q.lower()
        out = [
            c
            for c in out
            if ql in c["name"].lower()
            or ql in c["mobile"]
            or (c.get("email") or "").lower().startswith(ql)
            or (c.get("customer_id") or "").lower() == ql
        ]
    return [Contact(**c) for c in out]


@router.post("/contacts", response_model=Contact, status_code=201)
def create_contact(
    payload: ContactCreate,
    _: Annotated[UserOut, Depends(current_user)],
) -> Contact:
    entry = {
        "id": f"ct_{secrets.token_hex(3)}",
        **payload.model_dump(),
        "last_contacted_at": None,
    }
    CONTACTS.append(entry)
    return Contact(**entry)


@router.patch("/contacts/{contact_id}", response_model=Contact)
def update_contact(
    contact_id: str,
    payload: ContactCreate,
    _: Annotated[UserOut, Depends(current_user)],
) -> Contact:
    for c in CONTACTS:
        if c["id"] == contact_id:
            c.update(payload.model_dump(exclude_unset=True))
            return Contact(**c)
    raise HTTPException(404, "Contact not found")


@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(
    contact_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> None:
    for i, c in enumerate(CONTACTS):
        if c["id"] == contact_id:
            CONTACTS.pop(i)
            return
    raise HTTPException(404, "Contact not found")


# ---------------- Conversations (inbox) ----------------
class Message(BaseModel):
    author: Literal["customer", "ai", "agent"]
    at: str
    body: str


class Conversation(BaseModel):
    id: str
    channel: Literal["voice", "sms", "whatsapp", "web"]
    contact_id: str
    subject: str
    labels: list[str]
    status: Literal["open", "closed"]
    last_message_at: str
    messages: list[Message]


class AppendMessage(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    author: Literal["agent", "ai"] = "agent"


@router.get("/conversations", response_model=list[Conversation])
def list_conversations(
    _: Annotated[UserOut, Depends(current_user)],
    status: str | None = None,
) -> list[Conversation]:
    out = list(CONVERSATIONS)
    if status:
        out = [c for c in out if c["status"] == status]
    out.sort(key=lambda c: c["last_message_at"], reverse=True)
    return [Conversation(**c) for c in out]


@router.get("/conversations/{conv_id}", response_model=Conversation)
def conversation_detail(
    conv_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> Conversation:
    for c in CONVERSATIONS:
        if c["id"] == conv_id:
            return Conversation(**c)
    raise HTTPException(404, "Conversation not found")


@router.post("/conversations/{conv_id}/reply", response_model=Conversation)
def append_message(
    conv_id: str,
    payload: AppendMessage,
    _: Annotated[UserOut, Depends(current_user)],
) -> Conversation:
    for c in CONVERSATIONS:
        if c["id"] == conv_id:
            now = datetime.now(timezone.utc).isoformat()
            c["messages"].append({"author": payload.author, "at": now, "body": payload.body})
            c["last_message_at"] = now
            if c["status"] == "closed":
                c["status"] = "open"
            return Conversation(**c)
    raise HTTPException(404, "Conversation not found")


@router.post("/conversations/{conv_id}/close", response_model=Conversation)
def close_conversation(
    conv_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> Conversation:
    for c in CONVERSATIONS:
        if c["id"] == conv_id:
            c["status"] = "closed"
            return Conversation(**c)
    raise HTTPException(404, "Conversation not found")
