"""
Customer Quote Portal — public endpoints (no auth required)

POST /quotes/{quote_id}/client-link     generate / regenerate client token
GET  /quotes/view/{token}               public — client fetches their quote summary
POST /quotes/view/{token}/respond       public — client accepts / declines / requests changes
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Quote, QuoteEvent

router_internal = APIRouter(prefix="/quotes", tags=["quote-portal"])
router_public   = APIRouter(prefix="/quotes", tags=["quote-portal"])

Db = Annotated[Session, Depends(get_db)]

VALID_RESPONSES = {"accepted", "changes_requested", "declined"}


def _now():
    return datetime.now(timezone.utc)


# ── Schemas ───────────────────────────────────────────────────────────────────

class ClientLinkIn(BaseModel):
    expires_days: int = 30


class ClientLinkOut(BaseModel):
    token: uuid.UUID
    expires_at: datetime
    quote_id: uuid.UUID


class ClientQuoteOut(BaseModel):
    """Client-safe quote view — no BOM, no margins, no internal data."""
    quote_id: uuid.UUID
    title: str
    quote_number: str | None
    revision: str
    client_name: str | None
    currency: str
    total_ex_vat: float | None
    total_inc_vat: float | None
    deposit_percent: float | None
    deposit_amount: float | None
    status: str
    expires_at: datetime | None
    notes: str | None          # shown only if non-internal (kept simple)
    spec_summary: dict | None  # from spec_snapshot — client-safe subset
    already_responded: bool
    client_response: str | None
    client_viewed_at: datetime | None


class ClientRespondIn(BaseModel):
    action: str            # "accepted" | "changes_requested" | "declined"
    note: str | None = None


# ── Internal: generate / regenerate client link ───────────────────────────────

@router_internal.post("/{quote_id}/client-link", response_model=ClientLinkOut, status_code=201)
def generate_client_link(quote_id: uuid.UUID, body: ClientLinkIn, db: Db):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(404, "Quote not found")

    now = _now()
    quote.client_token = uuid.uuid4()
    quote.client_token_expires_at = now + timedelta(days=body.expires_days)
    # Reset previous response tracking on regeneration
    quote.client_viewed_at = None
    quote.client_responded_at = None
    quote.client_response = None
    quote.client_response_note = None

    _add_event(db, quote, "client_link_generated", None,
               f"Client link generated, expires in {body.expires_days} days", None)
    db.commit()
    db.refresh(quote)

    return ClientLinkOut(
        token=quote.client_token,
        expires_at=quote.client_token_expires_at,
        quote_id=quote.id,
    )


# ── Public: client views their quote ─────────────────────────────────────────

@router_public.get("/view/{token}", response_model=ClientQuoteOut)
def get_client_quote(token: uuid.UUID, db: Db):
    quote = db.query(Quote).filter(Quote.client_token == token).first()
    if not quote:
        raise HTTPException(404, "This link is invalid or has expired")

    now = _now()
    if quote.client_token_expires_at and quote.client_token_expires_at < now:
        raise HTTPException(410, "This quote link has expired. Please contact us for an updated link.")

    # Record first view
    if not quote.client_viewed_at:
        quote.client_viewed_at = now
        _add_event(db, quote, "client_viewed_quote", None, None, None)
        db.commit()

    # Build client-safe spec summary from snapshot
    spec_summary = None
    if quote.spec_snapshot:
        snap = quote.spec_snapshot
        spec_summary = {
            "width_m":      snap.get("width_m"),
            "length_m":     snap.get("length_m"),
            "wall_height_m": snap.get("wall_height_m"),
            "roof_type":    snap.get("roof_type"),
            "floor_area_m2": snap.get("floor_area_m2"),
            "openings":     snap.get("openings"),
        }

    return ClientQuoteOut(
        quote_id=quote.id,
        title=quote.title,
        quote_number=quote.quote_number,
        revision=quote.revision,
        client_name=quote.client_name,
        currency=quote.currency,
        total_ex_vat=float(quote.total_ex_vat) if quote.total_ex_vat else None,
        total_inc_vat=float(quote.total_inc_vat) if quote.total_inc_vat else None,
        deposit_percent=float(quote.deposit_percent) if quote.deposit_percent else None,
        deposit_amount=float(quote.deposit_amount) if quote.deposit_amount else None,
        status=quote.status,
        expires_at=quote.client_token_expires_at,
        notes=quote.notes,
        spec_summary=spec_summary,
        already_responded=bool(quote.client_responded_at),
        client_response=quote.client_response,
        client_viewed_at=quote.client_viewed_at,
    )


# ── Public: client responds ───────────────────────────────────────────────────

@router_public.post("/view/{token}/respond", response_model=ClientQuoteOut)
def client_respond(token: uuid.UUID, body: ClientRespondIn, db: Db):
    quote = db.query(Quote).filter(Quote.client_token == token).first()
    if not quote:
        raise HTTPException(404, "This link is invalid or has expired")

    now = _now()
    if quote.client_token_expires_at and quote.client_token_expires_at < now:
        raise HTTPException(410, "This quote link has expired.")

    if body.action not in VALID_RESPONSES:
        raise HTTPException(400, f"action must be one of: {', '.join(sorted(VALID_RESPONSES))}")

    quote.client_responded_at = now
    quote.client_response = body.action
    quote.client_response_note = body.note

    # Auto-transition quote status on acceptance
    if body.action == "accepted" and quote.status not in ("accepted", "converted"):
        quote.status = "accepted"
        if not quote.accepted_at:
            quote.accepted_at = now
        quote.accepted_revision_locked = True
        _add_event(db, quote, "accepted", quote.status, "accepted",
                   f"Client accepted quote via portal. {body.note or ''}", None)
    elif body.action == "declined":
        if quote.status not in ("lost",):
            quote.status = "lost"
            if not quote.lost_at:
                quote.lost_at = now
        _add_event(db, quote, "client_declined_quote", quote.status, quote.status,
                   f"Client declined via portal. {body.note or ''}", None)
    else:
        # changes_requested — stay in current status, just log
        _add_event(db, quote, "client_requested_changes", quote.status, quote.status,
                   f"Client requested changes via portal. {body.note or ''}", None)

    db.commit()
    db.refresh(quote)

    # Return updated view
    spec_summary = None
    if quote.spec_snapshot:
        snap = quote.spec_snapshot
        spec_summary = {k: snap.get(k) for k in
                        ("width_m", "length_m", "wall_height_m", "roof_type", "floor_area_m2", "openings")}

    return ClientQuoteOut(
        quote_id=quote.id,
        title=quote.title,
        quote_number=quote.quote_number,
        revision=quote.revision,
        client_name=quote.client_name,
        currency=quote.currency,
        total_ex_vat=float(quote.total_ex_vat) if quote.total_ex_vat else None,
        total_inc_vat=float(quote.total_inc_vat) if quote.total_inc_vat else None,
        deposit_percent=float(quote.deposit_percent) if quote.deposit_percent else None,
        deposit_amount=float(quote.deposit_amount) if quote.deposit_amount else None,
        status=quote.status,
        expires_at=quote.client_token_expires_at,
        notes=quote.notes,
        spec_summary=spec_summary,
        already_responded=True,
        client_response=quote.client_response,
        client_viewed_at=quote.client_viewed_at,
    )


# ── Helper ────────────────────────────────────────────────────────────────────

def _add_event(db, quote, event_type, old_status, note, created_by):
    db.add(QuoteEvent(
        quote_id=quote.id,
        event_type=event_type,
        old_status=old_status,
        new_status=quote.status,
        note=note,
        created_by=created_by,
    ))
