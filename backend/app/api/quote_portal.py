"""
Customer Quote Portal — public endpoints (no auth required)

POST /quotes/{quote_id}/client-link           generate / regenerate client token
GET  /quotes/view/{token}                     public — client fetches their quote summary
POST /quotes/view/{token}/respond             public — client accepts / declines / requests changes
GET  /quotes/view/{token}/quote.pdf           public — client downloads quote summary PDF
GET  /quotes/view/{token}/deposit-invoice.pdf public — client downloads deposit invoice PDF (accepted only)
"""
import io
import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AccountSettings, Quote, QuoteEvent

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
    # Only reset response tracking if the quote hasn't been responded to yet
    if not quote.client_responded_at:
        quote.client_viewed_at = None

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
        spec_summary = _build_spec_summary(quote.spec_snapshot)

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
def client_respond(token: uuid.UUID, body: ClientRespondIn, db: Db):  # noqa: C901
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

    # Block acceptance of unpriced quotes
    if body.action == "accepted":
        if not quote.total_inc_vat or float(quote.total_inc_vat) <= 0:
            raise HTTPException(400, "This quote has not been priced yet and cannot be accepted. Please wait for a priced quote.")

    # Auto-transition quote status on acceptance
    if body.action == "accepted" and quote.status not in ("accepted", "converted"):
        quote.status = "accepted"
        if not quote.accepted_at:
            quote.accepted_at = now
        quote.accepted_revision_locked = True
        _add_event(db, quote, "accepted", quote.status,
                   f"Client accepted quote via portal. {body.note or ''}", None)
    elif body.action == "declined":
        if quote.status not in ("lost",):
            quote.status = "lost"
            if not quote.lost_at:
                quote.lost_at = now
        _add_event(db, quote, "client_declined_quote", quote.status,
                   f"Client declined via portal. {body.note or ''}", None)
    else:
        # changes_requested — update status and log
        quote.status = "changes_requested"
        _add_event(db, quote, "client_requested_changes", quote.status,
                   f"Client requested changes via portal. {body.note or ''}", None)

    db.commit()
    db.refresh(quote)

    # Return updated view
    spec_summary = None
    if quote.spec_snapshot:
        spec_summary = _build_spec_summary(quote.spec_snapshot)

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _spec_fields(snap: dict | None) -> dict:
    """Extract flat spec fields from old flat snapshot or new nested questionnaire snapshot."""
    if not snap:
        return {}
    qa = snap.get("questionnaire_answers")
    if isinstance(qa, dict):
        return qa
    return snap


def _build_spec_summary(snap: dict | None) -> dict | None:
    """Build a client-safe spec summary from a spec_snapshot (handles both old and new format)."""
    if not snap:
        return None
    f = _spec_fields(snap)
    return {
        "pod_type":                f.get("pod_type"),
        "quantity":                f.get("quantity"),
        "width_m":                 f.get("width_m"),
        "length_m":                f.get("length_m"),
        "height_m":                f.get("height_m"),
        "wall_height_m":           f.get("wall_height_m"),
        "floor_area_m2":           f.get("floor_area_m2"),
        "door_count":              f.get("door_count"),
        "door_type":               f.get("door_type"),
        "window_count":            f.get("window_count"),
        "window_type":             f.get("window_type"),
        "rooflight_count":         f.get("rooflight_count"),
        "external_finish":         f.get("external_finish"),
        "internal_finish_package": f.get("internal_finish_package"),
        "heating_option":          f.get("heating_option"),
        "ventilation_option":      f.get("ventilation_option"),
        "electrical_package":      f.get("electrical_package"),
        "foundation_option":       f.get("foundation_option"),
        "delivery_install_option": f.get("delivery_install_option"),
        "location":                f.get("location"),
        "intended_use":            f.get("intended_use"),
        "timeline":                f.get("timeline"),
        # Legacy / manually-entered fields
        "roof_type":               f.get("roof_type"),
        "openings":                f.get("openings"),
    }


def _add_event(db, quote, event_type, old_status, note, created_by):
    db.add(QuoteEvent(
        quote_id=quote.id,
        event_type=event_type,
        old_status=old_status,
        new_status=quote.status,
        note=note,
        created_by=created_by,
    ))


# ── Public: client downloads PDFs ────────────────────────────────────────────

def _validate_token(token: uuid.UUID, db: Session) -> Quote:
    quote = db.query(Quote).filter(Quote.client_token == token).first()
    if not quote:
        raise HTTPException(404, "This link is invalid or has expired")
    now = datetime.now(timezone.utc)
    if quote.client_token_expires_at and quote.client_token_expires_at < now:
        raise HTTPException(410, "This quote link has expired. Please contact us for an updated link.")
    return quote


def _get_settings_dict(db: Session) -> dict:
    settings = db.query(AccountSettings).first()
    if not settings:
        return {}
    return {
        "company_name":       settings.company_name,
        "company_address":    settings.company_address,
        "company_email":      settings.company_email,
        "company_phone":      settings.company_phone,
        "vat_number":         settings.vat_number,
        "bank_name":          settings.bank_name,
        "bank_account_name":  settings.bank_account_name,
        "bank_iban":          settings.bank_iban,
        "bank_bic":           settings.bank_bic,
        "payment_terms_days": settings.payment_terms_days or 7,
        "vat_rate_percent":   settings.vat_rate_percent or 21.0,
    }


@router_public.get("/view/{token}/quote.pdf")
def get_client_quote_pdf(token: uuid.UUID, db: Db):
    from app.skills.pdf_deposit_invoice import build_deposit_invoice
    quote = _validate_token(token, db)
    settings_dict = _get_settings_dict(db)

    quote_dict = {
        "id":              str(quote.id),
        "title":           quote.title,
        "quote_number":    quote.quote_number,
        "client_name":     quote.client_name,
        "currency":        quote.currency,
        "total_ex_vat":    float(quote.total_ex_vat) if quote.total_ex_vat else None,
        "total_inc_vat":   float(quote.total_inc_vat) if quote.total_inc_vat else None,
        "deposit_percent": float(quote.deposit_percent) if quote.deposit_percent else None,
        "deposit_amount":  float(quote.deposit_amount) if quote.deposit_amount else None,
        "notes":           quote.notes,
        "spec_summary":    _build_spec_summary(quote.spec_snapshot),
    }

    pdf_bytes = build_deposit_invoice(quote_dict, settings_dict)
    filename = f"quote-{quote.quote_number or str(quote.id)[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router_public.get("/view/{token}/deposit-invoice.pdf")
def get_client_deposit_invoice_pdf(token: uuid.UUID, db: Db):
    from app.skills.pdf_deposit_invoice import build_deposit_invoice
    quote = _validate_token(token, db)

    if quote.client_response != "accepted":
        raise HTTPException(403, "Deposit invoice is only available after you accept the quote.")
    if not quote.total_ex_vat and not quote.deposit_amount:
        raise HTTPException(400, "This quote has not been priced yet.")

    settings_dict = _get_settings_dict(db)

    quote_dict = {
        "id":              str(quote.id),
        "title":           quote.title,
        "quote_number":    quote.quote_number,
        "client_name":     quote.client_name,
        "currency":        quote.currency,
        "total_ex_vat":    float(quote.total_ex_vat) if quote.total_ex_vat else None,
        "total_inc_vat":   float(quote.total_inc_vat) if quote.total_inc_vat else None,
        "deposit_percent": float(quote.deposit_percent) if quote.deposit_percent else None,
        "deposit_amount":  float(quote.deposit_amount) if quote.deposit_amount else None,
        "notes":           quote.notes,
        "spec_summary":    _build_spec_summary(quote.spec_snapshot),
    }

    pdf_bytes = build_deposit_invoice(quote_dict, settings_dict)
    filename = f"deposit-invoice-{quote.quote_number or str(quote.id)[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
