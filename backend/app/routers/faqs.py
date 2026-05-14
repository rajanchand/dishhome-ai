"""FAQ knowledge base.

Admin uploads Q/A pairs (single or bulk JSON). The /ask endpoint runs a
simple keyword + language-aware match. In production swap the matcher for a
vector store (e.g. FAISS over embeddings from the same Ollama model).
"""

import json
import re
import secrets
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.mock_data import FAQS
from app.routers.auth import UserOut, current_user

router = APIRouter(prefix="/faqs", tags=["faqs"])


class Faq(BaseModel):
    id: str
    question_en: str | None = None
    question_ne: str | None = None
    answer_en: str | None = None
    answer_ne: str | None = None
    category: str | None = None
    tags: list[str] = []


class FaqCreate(BaseModel):
    question_en: str | None = None
    question_ne: str | None = None
    answer_en: str | None = None
    answer_ne: str | None = None
    category: str | None = "general"
    tags: list[str] = []


class AskRequest(BaseModel):
    query: str
    language: Literal["ne", "en"] = "ne"
    top_k: int = 3


class AskHit(BaseModel):
    faq: Faq
    score: float


class AskResponse(BaseModel):
    query: str
    language: str
    answer: str | None
    matched: list[AskHit]


def _new_id() -> str:
    return f"faq_{secrets.token_hex(4)}"


def _faq_categories() -> list[str]:
    return sorted({f.get("category") or "general" for f in FAQS})


@router.get("", response_model=list[Faq])
def list_faqs(_: Annotated[UserOut, Depends(current_user)]) -> list[Faq]:
    return [Faq(**f) for f in FAQS]


@router.get("/categories", response_model=list[str])
def categories(_: Annotated[UserOut, Depends(current_user)]) -> list[str]:
    return _faq_categories()


@router.post("", response_model=Faq, status_code=201)
def create_faq(
    payload: FaqCreate,
    _: Annotated[UserOut, Depends(current_user)],
) -> Faq:
    if not any([payload.question_en, payload.question_ne]):
        raise HTTPException(400, "Provide at least one question (en or ne)")
    if not any([payload.answer_en, payload.answer_ne]):
        raise HTTPException(400, "Provide at least one answer (en or ne)")
    entry = {"id": _new_id(), **payload.model_dump()}
    FAQS.append(entry)
    return Faq(**entry)


@router.delete("/{faq_id}", status_code=204)
def delete_faq(
    faq_id: str,
    _: Annotated[UserOut, Depends(current_user)],
) -> None:
    for i, f in enumerate(FAQS):
        if f["id"] == faq_id:
            FAQS.pop(i)
            return
    raise HTTPException(404, "FAQ not found")


@router.post("/import")
async def bulk_import(
    user: Annotated[UserOut, Depends(current_user)],
    file: Annotated[UploadFile, File(...)],
) -> dict[str, int | str]:
    """Accept .json (list of FAQ dicts) or .jsonl. Returns counts."""
    _ = user
    raw = await file.read()
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(413, "FAQ import too large (>2 MB)")
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        raise HTTPException(400, "Empty file")
    items: list[dict] = []
    try:
        if text.startswith("["):
            items = json.loads(text)
        else:
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                items.append(json.loads(line))
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"Could not parse JSON: {e.msg}") from e

    added = 0
    skipped = 0
    for it in items:
        if not isinstance(it, dict):
            skipped += 1
            continue
        try:
            payload = FaqCreate(**{k: it.get(k) for k in FaqCreate.model_fields.keys()})
        except Exception:
            skipped += 1
            continue
        if not any([payload.question_en, payload.question_ne]) or not any(
            [payload.answer_en, payload.answer_ne]
        ):
            skipped += 1
            continue
        FAQS.append({"id": _new_id(), **payload.model_dump()})
        added += 1
    return {"added": added, "skipped": skipped, "total": len(FAQS)}


_TOKEN_RE = re.compile(r"[\w']+", re.UNICODE)


def _tokens(s: str | None) -> set[str]:
    if not s:
        return set()
    return {t.lower() for t in _TOKEN_RE.findall(s)}


@router.post("/ask", response_model=AskResponse)
def ask(
    payload: AskRequest,
    _: Annotated[UserOut, Depends(current_user)],
) -> AskResponse:
    """Lightweight keyword match. Returns top-K FAQs scored by token overlap."""
    q_tokens = _tokens(payload.query)
    if not q_tokens:
        return AskResponse(query=payload.query, language=payload.language, answer=None, matched=[])

    scored: list[tuple[float, dict]] = []
    for f in FAQS:
        # Score against the question in the requested language (with fallback)
        candidate_q = (
            (f.get(f"question_{payload.language}") or "")
            + " "
            + (f.get("question_en") or "")
            + " "
            + (f.get("question_ne") or "")
            + " "
            + " ".join(f.get("tags") or [])
        )
        c_tokens = _tokens(candidate_q)
        if not c_tokens:
            continue
        overlap = len(q_tokens & c_tokens)
        if not overlap:
            continue
        score = overlap / max(len(q_tokens), 1)
        scored.append((score, f))

    scored.sort(key=lambda kv: -kv[0])
    top = scored[: payload.top_k]
    answer = None
    if top and top[0][0] >= 0.25:
        winner = top[0][1]
        answer = (
            winner.get(f"answer_{payload.language}")
            or winner.get("answer_en")
            or winner.get("answer_ne")
        )
    return AskResponse(
        query=payload.query,
        language=payload.language,
        answer=answer,
        matched=[AskHit(faq=Faq(**f), score=round(s, 3)) for s, f in top],
    )
