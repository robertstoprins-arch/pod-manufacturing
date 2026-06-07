"""
API: Quotes — commercial pipeline

GET    /quotes                          list all (filter: ?status= ?client_id= ?pod_spec_id=)
POST   /quotes                          create (201)
GET    /quotes/{id}                     get
PUT    /quotes/{id}                     update
DELETE /quotes/{id}                     delete (204)
PATCH  /quotes/{id}/status              status transition with auto-logic
GET    /quotes/{id}/events              event history
POST   /quotes/{id}/events              add manual event/note
GET    /quotes/{id}/email-preview       build default email draft (generates portal token if missing)
POST   /quotes/{id}/send-to-client      send quote email, update status to "sent"
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AccountSettings, Quote, QuoteEvent
from app.api.email_service import send_email

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
    client_token: uuid.UUID | None
    client_token_expires_at: datetime | None
    client_viewed_at: datetime | None
    client_last_viewed_at: datetime | None
    client_view_count: int = 0
    client_responded_at: datetime | None
    client_response: str | None
    client_response_note: str | None
    spec_snapshot: dict | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _spec_fields(snap: dict | None) -> dict:
    """Extract flat spec fields from old flat snapshot or new nested questionnaire snapshot."""
    if not snap:
        return {}
    qa = snap.get("questionnaire_answers")
    if isinstance(qa, dict):
        return qa
    return snap

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


@router.get("/{quote_id}/rfq")
def get_quote_rfq(quote_id: uuid.UUID, db: Db):
    """
    Generate a standard RFQ package for a quote.

    Calls the BOM endpoint internally, groups lines by preferred/named supplier,
    and returns the standard rfq_request JSON (schema v0.1).

    Available for any quote with a linked pod_spec_id — not restricted to accepted only
    so manufacturers can preview before sending.
    """
    from app.api.pod_specs import get_pod_spec_bom

    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(404, "Quote not found")
    if not quote.pod_spec_id:
        raise HTTPException(400, "Quote has no linked pod spec — cannot generate RFQ")

    bom = get_pod_spec_bom(quote.pod_spec_id, db)

    rfq_id = f"RFQ-{str(quote_id)[:8].upper()}"
    currency = quote.currency or bom.currency or "EUR"

    # Group BOM lines:
    # 1. role="opening" → __openings__ (provisional allowances, separate package)
    # 2. preferred_supplier_id set → confirmed supplier group (keyed by supplier UUID)
    # 3. supplier_name text only → suggested supplier group (keyed by name)
    # 4. neither → __unassigned__
    _groups: dict[str, dict] = {}  # internal key → {name, confirmed, suggested, is_openings, lines}

    for line in bom.lines:
        if line.role == "opening":
            key = "__openings__"
            if key not in _groups:
                _groups[key] = {"name": "Openings (Provisional)", "confirmed": False, "suggested": False, "is_openings": True, "lines": []}
        elif line.preferred_supplier_id:
            key = f"confirmed__{line.preferred_supplier_id}"
            if key not in _groups:
                _groups[key] = {"name": line.preferred_supplier_name or "Confirmed Supplier", "confirmed": True, "suggested": False, "is_openings": False, "lines": []}
        elif line.supplier_name:
            key = f"suggested__{line.supplier_name}"
            if key not in _groups:
                _groups[key] = {"name": line.supplier_name, "confirmed": False, "suggested": True, "is_openings": False, "lines": []}
        else:
            key = "__unassigned__"
            if key not in _groups:
                _groups[key] = {"name": "Unassigned", "confirmed": False, "suggested": False, "is_openings": False, "lines": []}
        _groups[key]["lines"].append(line)

    # Build per-supplier RFQ items
    rfq_suppliers = []
    line_counter = 1
    for group in _groups.values():
        items = []
        for line in group["lines"]:
            # Skip zero-quantity framing sub-lines
            if line.order_quantity == 0:
                continue
            items.append({
                "line_id": str(line_counter),
                "description": line.material_name,
                "category": line.element_type.lower(),
                "quantity": round(line.order_quantity, 3),
                "unit": line.unit,
                "supplier_ref": line.supplier_ref or None,
                "acceptable_substitutes": True,
                "required_evidence": _required_evidence(line),
                "element_type": line.element_type,
                "build_up_name": line.build_up_name,
                "evidence_status": line.evidence_status,
                "estimated_unit_price": line.price_per_unit,
                "estimated_line_cost": line.line_cost,
                "currency": line.currency or currency,
                "datasheet_url": line.datasheet_url or None,
                "dop_url": line.dop_url or None,
                "material_id": line.material_id,
                "price_source": line.price_source,
                "role": line.role,
            })
            line_counter += 1

        if items:
            rfq_suppliers.append({
                "supplier_name": group["name"],
                "confirmed": group["confirmed"],
                "suggested": group["suggested"],
                "is_openings": group["is_openings"],
                "items": items,
                "estimated_subtotal": round(
                    sum(i["estimated_line_cost"] for i in items if i["estimated_line_cost"]), 2
                ) or None,
            })

    # RFQ readiness: Blocked if any error-severity warning; Needs Attention if any warning; else Ready
    _has_errors   = any(w.get("severity") == "error"   for w in bom.warnings)
    _has_warnings = any(w.get("severity") == "warning" for w in bom.warnings)
    rfq_readiness = "Blocked" if _has_errors else ("Needs Attention" if _has_warnings else "Ready")

    rfq = {
        "message_type": "rfq_request",
        "version": "0.1",
        "rfq_id": rfq_id,
        "generated_at": _now().isoformat(),
        "rfq_readiness": rfq_readiness,
        "buyer": {
            "company_name": "Top-R Solutions",
            "contact_email": "",
        },
        "project": {
            "quote_id": str(quote.id),
            "quote_number": quote.quote_number or "",
            "title": quote.title,
            "client_name": quote.client_name or "",
            "currency": currency,
            "required_by": quote.expires_at.date().isoformat() if quote.expires_at else None,
        },
        "rfq": {
            "valid_response_required_by": None,
            "allow_substitutes": True,
            "currency": currency,
        },
        "spec_summary": {
            "spec_id": bom.spec_id,
            "spec_name": bom.spec_name,
            "areas": bom.areas,
            "opening_counts": bom.opening_counts,
            "estimated_total": bom.total_cost,
            "has_estimates": bom.has_estimates,
            "warnings": bom.warnings,
        },
        "supplier_groups": rfq_suppliers,
        "total_items": line_counter - 1,
        "total_suppliers": len(rfq_suppliers),
    }

    return rfq


def _required_evidence(line) -> list[str]:
    # Openings and provisional assemblies don't require product evidence
    if line.role == "opening":
        return []
    ev = line.evidence_status or "missing"
    if ev in ("verified", "provisional"):
        return []
    needed = []
    if not line.datasheet_url:
        needed.append("datasheet")
    if not line.dop_url:
        needed.append("DoP")
    return needed


# ── Deposit invoice PDF ───────────────────────────────────────────────────────

@router.get("/{quote_id}/deposit-invoice.pdf")
def get_deposit_invoice(quote_id: uuid.UUID, db: Db):
    from fastapi.responses import StreamingResponse
    import io
    from app.models import AccountSettings
    from app.skills.pdf_deposit_invoice import build_deposit_invoice

    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(404, "Quote not found")
    if not quote.total_ex_vat and not quote.deposit_amount:
        raise HTTPException(400, "Quote has no pricing — add total and deposit before generating invoice")

    settings = db.query(AccountSettings).first()
    settings_dict = {}
    if settings:
        settings_dict = {
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
        "spec_summary":    _spec_fields(quote.spec_snapshot),
    }

    pdf_bytes = build_deposit_invoice(quote_dict, settings_dict)

    filename = f"deposit-invoice-{quote.quote_number or str(quote.id)[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Payment status ────────────────────────────────────────────────────────────

VALID_PAYMENT_STATUSES = {"awaiting_deposit", "deposit_received", "paid_in_full", "overdue"}


class PaymentStatusIn(BaseModel):
    payment_status: str
    note: str | None = None


@router.patch("/{quote_id}/payment", response_model=QuoteOut)
def update_payment_status(quote_id: uuid.UUID, body: PaymentStatusIn, db: Db):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(404, "Quote not found")
    if body.payment_status not in VALID_PAYMENT_STATUSES:
        raise HTTPException(400, f"payment_status must be one of: {', '.join(sorted(VALID_PAYMENT_STATUSES))}")

    old_status = quote.payment_status
    quote.payment_status = body.payment_status

    note = body.note or f"Payment status set to: {body.payment_status}"
    if body.payment_status == "deposit_received" and old_status != "deposit_received":
        note = body.note or "Deposit received — production can proceed"

    _add_event(db, quote, "payment_status_updated", quote.status, quote.status, note, "internal")
    db.commit()
    db.refresh(quote)
    return quote


# ── Quote Email ───────────────────────────────────────────────────────────────

FRONTEND_URL_DEFAULT = "https://pod-manufacturing.vercel.app"


def _ensure_client_token(quote: Quote, db: Session) -> uuid.UUID:
    """Generate a 30-day client portal token if the quote doesn't already have one."""
    if not quote.client_token or (
        quote.client_token_expires_at and quote.client_token_expires_at < _now()
    ):
        quote.client_token = uuid.uuid4()
        quote.client_token_expires_at = _now() + timedelta(days=30)
        db.add(QuoteEvent(
            quote_id=quote.id,
            event_type="client_link_generated",
            old_status=quote.status,
            new_status=quote.status,
            note="Client portal token auto-generated for email send",
            created_by="system",
        ))
    return quote.client_token


def _build_portal_url(token: uuid.UUID) -> str:
    base = os.environ.get("FRONTEND_URL", FRONTEND_URL_DEFAULT).rstrip("/")
    return f"{base}/quote-view/{token}"


def _get_settings(db: Session) -> AccountSettings | None:
    return db.query(AccountSettings).first()


def _build_email_html(quote: Quote, body_text: str, portal_url: str, settings: AccountSettings | None) -> str:
    company_name  = (settings and settings.company_name)  or "Top-R Solutions"
    company_email = (settings and settings.company_email) or ""
    company_phone = (settings and settings.company_phone) or ""

    # Backend URL for direct PDF download link.
    # Render sets RENDER_EXTERNAL_URL automatically; BACKEND_URL can override it.
    _backend_base = (
        os.environ.get("BACKEND_URL")
        or os.environ.get("RENDER_EXTERNAL_URL")
        or ""
    ).rstrip("/")
    pdf_url = f"{_backend_base}/quotes/view/{quote.client_token}/client-quote.pdf" if _backend_base else None

    price_line = ""
    if quote.total_inc_vat and float(quote.total_inc_vat) > 0:
        currency = quote.currency or "EUR"
        price_line = f"""
        <tr>
          <td style="padding:8px 0;border-top:1px solid #e5e7eb;">
            <strong>Total (inc. VAT):</strong> {currency} {float(quote.total_inc_vat):,.2f}
          </td>
        </tr>"""
    elif quote.spec_snapshot and quote.spec_snapshot.get("pricing_estimate", {}).get("status") == "estimated":
        pe = quote.spec_snapshot["pricing_estimate"]
        currency = quote.currency or "EUR"
        price_line = f"""
        <tr>
          <td style="padding:8px 0;border-top:1px solid #e5e7eb;">
            <em>Indicative estimate: {currency} {pe.get('total_inc_vat', 0):,.0f} inc. VAT</em>
          </td>
        </tr>"""

    # Build a brief product spec summary from the snapshot
    spec_rows = ""
    if quote.spec_snapshot:
        f = _spec_fields(quote.spec_snapshot)
        _POD_LABELS = {"office": "Office Pod", "garden": "Garden Pod", "studio": "Studio", "custom": "Custom"}
        pod_type = _POD_LABELS.get(f.get("pod_type", ""), f.get("pod_type", ""))
        w, l, h = f.get("width_m"), f.get("length_m"), f.get("height_m") or f.get("wall_height_m")
        dims = (f"{w} m × {l} m" + (f" × {h} m H" if h else "")) if w and l else None
        qty  = f.get("quantity")
        location = f.get("location")
        rows = []
        if pod_type:
            rows.append(("Product", pod_type))
        if dims:
            rows.append(("Dimensions", dims))
        if qty and int(qty) > 1:
            rows.append(("Quantity", str(qty)))
        if location:
            rows.append(("Location", location))
        if rows:
            inner = "".join(
                f"<tr><td style='padding:4px 8px 4px 0;color:#6b7280;font-size:13px;white-space:nowrap;'>{k}</td>"
                f"<td style='padding:4px 0;font-size:13px;color:#111;'>{v}</td></tr>"
                for k, v in rows
            )
            spec_rows = f"""
        <tr><td style="padding:16px 0 8px 0;">
          <table cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:6px;padding:12px 16px;width:100%;background:#f9fafb;">
            <tr><td colspan="2" style="padding-bottom:8px;font-size:11px;font-weight:bold;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em;">Your Specification</td></tr>
            {inner}
          </table>
        </td></tr>"""

    body_html = body_text.replace("\n", "<br>")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#111;background:#f9fafb;margin:0;padding:0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;border:1px solid #e5e7eb;padding:32px;">
        <tr><td style="border-bottom:2px solid #16a34a;padding-bottom:16px;margin-bottom:16px;">
          <h2 style="color:#16a34a;margin:0;">{company_name}</h2>
        </td></tr>
        <tr><td style="padding:24px 0 8px 0;">
          <p style="margin:0 0 16px 0;">{body_html}</p>
        </td></tr>
        <tr><td>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="padding:8px 0;">
                <strong>Quote Reference:</strong> {quote.quote_number or str(quote.id)[:8].upper()}
              </td>
            </tr>
            {price_line}
          </table>
        </td></tr>
        {spec_rows}
        <tr><td style="padding:24px 0 12px 0;text-align:center;">
          <a href="{portal_url}"
             style="background:#16a34a;color:#fff;padding:14px 32px;border-radius:6px;text-decoration:none;font-weight:bold;display:inline-block;">
            View Your Quote
          </a>
        </td></tr>
        {f'''<tr><td style="padding:0 0 16px 0;text-align:center;">
          <a href="{pdf_url}" style="font-size:13px;color:#16a34a;text-decoration:underline;">
            Download Quote PDF
          </a>
        </td></tr>''' if pdf_url else ''}
        <tr><td style="padding:16px 0 0 0;font-size:12px;color:#6b7280;border-top:1px solid #e5e7eb;">
          <p style="margin:4px 0;">{company_name}</p>
          {"<p style='margin:4px 0;'>" + company_email + "</p>" if company_email else ""}
          {"<p style='margin:4px 0;'>" + company_phone + "</p>" if company_phone else ""}
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _default_subject(quote: Quote) -> str:
    ref = quote.quote_number or str(quote.id)[:8].upper()
    name = f" for {quote.client_name}" if quote.client_name else ""
    return f"Your Quote{name} — {ref}"


def _default_body(quote: Quote, portal_url: str) -> str:
    name = quote.client_name or "there"
    ref  = quote.quote_number or str(quote.id)[:8].upper()

    has_price = quote.total_inc_vat and float(quote.total_inc_vat) > 0
    pe = (quote.spec_snapshot or {}).get("pricing_estimate", {})
    has_estimate = pe.get("status") == "estimated"

    if has_price:
        currency = quote.currency or "EUR"
        price_note = f"The total price is {currency} {float(quote.total_inc_vat):,.2f} inc. VAT."
    elif has_estimate:
        currency = quote.currency or "EUR"
        price_note = f"We have included an indicative estimate of {currency} {pe.get('total_inc_vat', 0):,.0f} inc. VAT based on your specification. A firm price will follow once we confirm all details."
    else:
        price_note = "We are reviewing your specification and will confirm pricing shortly."

    return (
        f"Hi {name},\n\n"
        f"Thank you for your enquiry. Please find your quote ({ref}) at the link below.\n\n"
        f"{price_note}\n\n"
        f"You can review and respond to the quote using the button below. "
        f"If you have any questions, please don't hesitate to get in touch.\n\n"
        f"Best regards"
    )


class EmailPreviewOut(BaseModel):
    to: str | None
    subject: str
    body: str
    html_preview: str
    client_portal_url: str
    has_price: bool
    is_indicative: bool
    quote_ref: str | None


class SendToClientIn(BaseModel):
    subject: str
    body: str
    follow_up_days: int = 3


class SendToClientOut(BaseModel):
    ok: bool
    quote_id: uuid.UUID
    status: str
    sent_at: datetime | None
    email_status: str
    email_message: str
    client_portal_url: str


@router.get("/{quote_id}/email-preview", response_model=EmailPreviewOut)
def email_preview(quote_id: uuid.UUID, db: Db):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(404, "Quote not found")

    token = _ensure_client_token(quote, db)
    db.commit()
    db.refresh(quote)

    portal_url = _build_portal_url(token)
    settings   = _get_settings(db)
    subject    = _default_subject(quote)
    body       = _default_body(quote, portal_url)
    html       = _build_email_html(quote, body, portal_url, settings)

    has_price    = bool(quote.total_inc_vat and float(quote.total_inc_vat) > 0)
    pe_status    = (quote.spec_snapshot or {}).get("pricing_estimate", {}).get("status")
    is_indicative = (not has_price) and pe_status == "estimated"

    return EmailPreviewOut(
        to=quote.client_email,
        subject=subject,
        body=body,
        html_preview=html,
        client_portal_url=portal_url,
        has_price=has_price,
        is_indicative=is_indicative,
        quote_ref=quote.quote_number,
    )


@router.post("/{quote_id}/send-to-client", response_model=SendToClientOut)
def send_to_client(quote_id: uuid.UUID, body: SendToClientIn, db: Db):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(404, "Quote not found")
    if not quote.client_email:
        raise HTTPException(400, "Quote has no client email address. Add one before sending.")

    token = _ensure_client_token(quote, db)
    portal_url = _build_portal_url(token)
    settings   = _get_settings(db)
    html       = _build_email_html(quote, body.body, portal_url, settings)

    result = send_email(
        to=quote.client_email,
        subject=body.subject,
        html_body=html,
        text_body=body.body,
        reply_to=(settings and settings.company_email) or None,
    )

    now = _now()
    old_status = quote.status
    quote.sent_at = now
    quote.follow_up_at = now + timedelta(days=body.follow_up_days)
    if quote.status not in ("accepted", "converted"):
        quote.status = "sent"

    note = (
        f"Quote emailed to {quote.client_email}. "
        f"Email status: {result.status}. "
        f"Subject: {body.subject}"
    )
    if result.message_id:
        note += f" (message_id: {result.message_id})"

    _add_event(db, quote, "quote_sent", old_status, quote.status, note, "internal")
    db.commit()
    db.refresh(quote)

    return SendToClientOut(
        ok=True,
        quote_id=quote.id,
        status=quote.status,
        sent_at=quote.sent_at,
        email_status=result.status,
        email_message=result.message,
        client_portal_url=portal_url,
    )
