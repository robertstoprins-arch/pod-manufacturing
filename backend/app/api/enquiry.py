"""
Public enquiry endpoint — no auth required.

POST /enquiry   — website quote hook
  Creates a Client record (or matches by email) and a draft Quote.
  Returns a reference number so the visitor knows their request landed.
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Client, Quote, QuoteEvent

router = APIRouter(prefix="/enquiry", tags=["enquiry"])

Db = Annotated[Session, Depends(get_db)]


def _now():
    return datetime.now(timezone.utc)


def _next_quote_number(db: Session) -> str:
    year = _now().year
    prefix = f"ENQ-{year}-"
    last = (
        db.query(Quote)
        .filter(Quote.quote_number.like(f"{prefix}%"))
        .order_by(Quote.quote_number.desc())
        .first()
    )
    if last and last.quote_number:
        try:
            n = int(last.quote_number.replace(prefix, "")) + 1
        except ValueError:
            n = 1
    else:
        n = 1
    return f"{prefix}{n:03d}"


# ── Schema ────────────────────────────────────────────────────────────────────

class EnquiryIn(BaseModel):
    # Contact
    first_name:   str
    last_name:    str
    email:        EmailStr
    phone:        str | None = None
    company_name: str | None = None

    # Pod requirements
    pod_type:     str              # bathroom | shower | wc | office | kitchen | custom
    quantity:     int = 1
    size_option:  str | None = None   # small | medium | large | custom
    width_m:      float | None = None
    length_m:     float | None = None

    # Project context
    location:     str | None = None
    intended_use: str | None = None   # hotel | residential | student | healthcare | office | other
    timeline:     str | None = None   # asap | 3months | 6months | 12months
    budget_range: str | None = None

    # Free text
    notes:        str | None = None


class EnquiryOut(BaseModel):
    reference:    str
    client_id:    uuid.UUID
    quote_id:     uuid.UUID
    message:      str


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("", response_model=EnquiryOut, status_code=201)
def submit_enquiry(body: EnquiryIn, db: Db):
    now = _now()

    # Find or create client by email
    client = db.query(Client).filter(Client.email == body.email).first()
    if not client:
        client = Client(
            name=f"{body.first_name} {body.last_name}".strip(),
            company_name=body.company_name,
            email=body.email,
            phone=body.phone,
            source="website",
            client_type="lead",
        )
        db.add(client)
        db.flush()  # get client.id before quote creation
    else:
        # Update contact details if they've changed
        client.name = f"{body.first_name} {body.last_name}".strip()
        if body.phone:        client.phone        = body.phone
        if body.company_name: client.company_name = body.company_name

    # Build a readable title
    pod_labels = {
        "bathroom": "Bathroom Pod",
        "shower":   "Shower Pod",
        "wc":       "WC Pod",
        "office":   "Office Pod",
        "kitchen":  "Kitchen Pod",
        "custom":   "Custom Pod",
    }
    pod_label = pod_labels.get(body.pod_type, "Pod")
    qty_str   = f" ×{body.quantity}" if body.quantity > 1 else ""
    loc_str   = f" — {body.location}" if body.location else ""
    title     = f"{pod_label}{qty_str}{loc_str}"

    # Build notes block from structured fields
    note_parts = []
    if body.size_option:  note_parts.append(f"Size: {body.size_option}")
    if body.width_m and body.length_m:
        note_parts.append(f"Dimensions: {body.width_m}m × {body.length_m}m")
    if body.intended_use: note_parts.append(f"Use: {body.intended_use}")
    if body.timeline:     note_parts.append(f"Timeline: {body.timeline}")
    if body.budget_range: note_parts.append(f"Budget: {body.budget_range}")
    if body.notes:        note_parts.append(f"\n{body.notes}")
    notes_text = "\n".join(note_parts) if note_parts else None

    ref = _next_quote_number(db)

    quote = Quote(
        client_id    = client.id,
        client_name  = client.name,
        client_email = body.email,
        title        = title,
        quote_number = ref,
        status       = "draft",
        lead_source  = "website",
        currency     = "EUR",
        notes        = notes_text,
        spec_snapshot= {
            "pod_type":     body.pod_type,
            "quantity":     body.quantity,
            "size_option":  body.size_option,
            "width_m":      body.width_m,
            "length_m":     body.length_m,
            "intended_use": body.intended_use,
            "timeline":     body.timeline,
            "budget_range": body.budget_range,
            "location":     body.location,
        },
    )
    db.add(quote)
    db.flush()

    db.add(QuoteEvent(
        quote_id   = quote.id,
        event_type = "enquiry_received",
        old_status = None,
        new_status = "draft",
        note       = f"Website enquiry from {body.email}",
        created_by = "system",
    ))

    db.commit()

    return EnquiryOut(
        reference  = ref,
        client_id  = client.id,
        quote_id   = quote.id,
        message    = f"Thank you {body.first_name}, we've received your enquiry and will be in touch shortly.",
    )
