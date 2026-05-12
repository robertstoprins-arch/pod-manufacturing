"""
API: Quotes — commercial pipeline

GET    /quotes                list all (filter: ?status= ?client_id= ?pod_spec_id=)
POST   /quotes                create (201)
GET    /quotes/{id}           get
PUT    /quotes/{id}           update
DELETE /quotes/{id}           delete (204)
PATCH  /quotes/{id}/status    status transition with auto-logic
GET    /quotes/{id}/events    event history
POST   /quotes/{id}/events    add manual event/note
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Quote, QuoteEvent

router = APIRouter(prefix="/quotes", tags=["quotes"])

Db = Annotated[Session, Depends(get_db)]

VALID_STATUSES = {"draft", "sent", "follow_up_due", "accepted", "lost", "expired", "converted"}


def _now():
    return datetime.now(timezone.utc)


# ── Schemas ───────────────────────────────────────────────────────────────────

class QuoteIn(BaseModel):
    title: str
    client_id: uuid.UUID | None = None
    pod_spec_id: int | None = None
    quote_number: str | None = None
    revision: str = "Rev 1"
    client_name: str | None = None
    client_email: str | None = None
    lead_source: str | None = None
    total_ex_vat: float | None = None
    total_inc_vat: float | None = None
    currency: str = "EUR"
    deposit_percent: float | None = None
    expires_at: datetime | None = None
    notes: str | None = None


class QuoteUpdateIn(BaseModel):
    title: str | None = None
    client_id: uuid.UUID | None = None
    pod_spec_id: int | None = None
    quote_number: str | None = None
    revision: str | None = None
    client_name: str | None = None
    client_email: str | None = None
    lead_source: str | None = None
    lost_reason: str | None = None
    total_ex_vat: float | None = None
    total_inc_vat: float | None = None
    currency: str | None = None
    deposit_percent: float | None = None
    deposit_amount: float | None = None
    payment_status: str | None = None
    payment_link: str | None = None
    expires_at: datetime | None = None
    follow_up_at: datetime | None = None
    notes: str | None = None


class QuoteStatusIn(BaseModel):
    status: str
    note: str | None = None
    lost_reason: str | None = None
    created_by: str | None = None


class QuoteEventIn(BaseModel):
    event_type: str
    note: str | None = None
    created_by: str | None = None


class QuoteEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quote_id: uuid.UUID
    event_type: str
    old_status: str | None
    new_status: str | None
    note: str | None
    created_by: str | None
    created_at: datetime | None


class QuoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    client_id: uuid.UUID | None
    pod_spec_id: int | None
    quote_number: str | None
    revision: str
    client_name: str | None
    client_email: str | None
    status: str
    lead_source: str | None
    lost_reason: str | None
    total_ex_vat: float | None
    total_inc_vat: float | None
    currency: str
    deposit_percent: float | None
    deposit_amount: float | None
    payment_status: str | None
    payment_link: str | None
    notes: str | None
    sent_at: datetime | None
    accepted_at: datetime | None
    lost_at: datetime | None
    expires_at: datetime | None
    converted_to_job_at: datetime | None
    follow_up_at: datetime | None
    last_followed_up_at: datetime | None
    accepted_revision_locked: bool
    created_at: datetime | None
    updated_at: datetime | None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _add_event(db: Session, quote: Quote, event_type: str, old_status: str | None,
               new_status: str | None, note: str | None, created_by: str | None):
    ev = QuoteEvent(
        quote_id=quote.id,
        event_type=event_type,
        old_status=old_status,
        new_status=new_status,
        note=note,
        created_by=created_by,
    )
    db.add(ev)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[QuoteOut])
def list_quotes(
    db: Db,
    status: str | None = None,
    client_id: uuid.UUID | None = None,
    pod_spec_id: int | None = None,
):
    q = db.query(Quote)
    if status:
        q = q.filter(Quote.status == status)
    if client_id:
        q = q.filter(Quote.client_id == client_id)
    if pod_spec_id:
        q = q.filter(Quote.pod_spec_id == pod_spec_id)
    return q.order_by(Quote.created_at.desc()).all()


@router.post("", response_model=QuoteOut, status_code=201)
def create_quote(body: QuoteIn, db: Db):
    quote = Quote(**body.model_dump())
    db.add(quote)
    db.flush()
    _add_event(db, quote, "created", None, "draft", None, None)
    db.commit()
    db.refresh(quote)
    return quote


@router.get("/{quote_id}", response_model=QuoteOut)
def get_quote(quote_id: uuid.UUID, db: Db):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(404, "Quote not found")
    return quote


@router.put("/{quote_id}", response_model=QuoteOut)
def update_quote(quote_id: uuid.UUID, body: QuoteUpdateIn, db: Db):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(404, "Quote not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(quote, k, v)
    db.commit()
    db.refresh(quote)
    return quote


@router.delete("/{quote_id}", status_code=204)
def delete_quote(quote_id: uuid.UUID, db: Db):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(404, "Quote not found")
    db.delete(quote)
    db.commit()
    return Response(status_code=204)


@router.patch("/{quote_id}/status", response_model=QuoteOut)
def update_status(quote_id: uuid.UUID, body: QuoteStatusIn, db: Db):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(404, "Quote not found")
    if body.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}")

    now = _now()
    old_status = quote.status

    if body.status == "sent":
        if not quote.sent_at:
            quote.sent_at = now
        if not quote.follow_up_at:
            quote.follow_up_at = now + timedelta(days=3)

    elif body.status == "accepted":
        if not quote.accepted_at:
            quote.accepted_at = now
        quote.accepted_revision_locked = True

    elif body.status == "lost":
        if not quote.lost_at:
            quote.lost_at = now
        if body.lost_reason:
            quote.lost_reason = body.lost_reason

    elif body.status == "converted":
        if not quote.converted_to_job_at:
            quote.converted_to_job_at = now

    elif body.status == "follow_up_due":
        quote.last_followed_up_at = now

    quote.status = body.status
    _add_event(db, quote, body.status, old_status, body.status, body.note, body.created_by)
    db.commit()
    db.refresh(quote)
    return quote


@router.get("/{quote_id}/events", response_model=list[QuoteEventOut])
def get_events(quote_id: uuid.UUID, db: Db):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(404, "Quote not found")
    return db.query(QuoteEvent).filter(QuoteEvent.quote_id == quote_id).order_by(QuoteEvent.created_at).all()


@router.post("/{quote_id}/events", response_model=QuoteEventOut, status_code=201)
def add_event(quote_id: uuid.UUID, body: QuoteEventIn, db: Db):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(404, "Quote not found")
    ev = QuoteEvent(
        quote_id=quote_id,
        event_type=body.event_type,
        note=body.note,
        created_by=body.created_by,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev
