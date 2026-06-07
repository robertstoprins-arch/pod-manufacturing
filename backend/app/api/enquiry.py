"""
Public enquiry endpoints — no auth required.

GET  /enquiry/templates              list active product templates
GET  /enquiry/templates/{id}         full template schema (fields, options, constraints)
POST /enquiry                        submit a quote enquiry

POST /enquiry creates a Client record (or matches by email) and a Draft Quote.
The submitted questionnaire answers are stored as structured JSON in
spec_snapshot so they are available to the internal team and future
agentic processing.

Architecture note — future agentic onboarding:
  When a new manufacturer is onboarded, an onboarding agent will produce a
  draft ProductTemplate (see app/product_templates.py) from the manufacturer's
  survey, uploaded files, and/or website. After human approval, the template
  is added to TEMPLATES and activates this same questionnaire flow for that
  manufacturer's product range. See docs/agent/agentic_onboarding_architecture.md.
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Client, Quote, QuoteEvent
from app.product_templates import get_template, list_active_templates

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


# ── Template endpoints ────────────────────────────────────────────────────────

@router.get("/templates")
def list_templates():
    """List all active product templates. Used to build a product selector."""
    return list_active_templates()


@router.get("/templates/{template_id}")
def get_template_schema(template_id: str):
    """
    Return the full template schema for a product type.

    The frontend uses this to render the quote questionnaire dynamically.
    The onboarding agent uses this as the target schema to populate when
    extracting variables from manufacturer-provided documents.
    """
    template = get_template(template_id)
    if not template:
        raise HTTPException(404, f"Template '{template_id}' not found")
    return template


# ── Enquiry submission ────────────────────────────────────────────────────────

class EnquiryIn(BaseModel):
    # Contact fields — always required regardless of product template
    first_name:   str
    last_name:    str
    email:        str
    phone:        str | None = None
    company_name: str | None = None

    # Which product template this enquiry is for.
    # Defaults to office_pod so existing integrations keep working.
    product_template_id: str = "office_pod"

    # All questionnaire answers from step 2 onwards, keyed by field.key.
    # The template schema defines which keys are expected.
    # Extra keys are stored but not validated — they don't break submission.
    answers: dict = {}


class EnquiryOut(BaseModel):
    reference:  str
    client_id:  uuid.UUID
    quote_id:   uuid.UUID
    message:    str


@router.post("", response_model=EnquiryOut, status_code=201)
def submit_enquiry(body: EnquiryIn, db: Db):
    # Validate template exists
    template = get_template(body.product_template_id)
    if not template:
        raise HTTPException(400, f"Unknown product_template_id: '{body.product_template_id}'")

    # Validate required fields from template schema
    required_answer_keys = [
        f["key"] for f in template["fields"]
        if f.get("required") and f["step"] != "contact"
    ]
    missing = [k for k in required_answer_keys if not body.answers.get(k)]
    if missing:
        raise HTTPException(422, f"Missing required fields: {', '.join(missing)}")

    now = _now()

    # Find or create client by email
    client = db.query(Client).filter(Client.email == body.email).first()
    if not client:
        client = Client(
            name         = f"{body.first_name} {body.last_name}".strip(),
            company_name = body.company_name,
            email        = body.email,
            phone        = body.phone,
            source       = "website",
            client_type  = "lead",
        )
        db.add(client)
        db.flush()
    else:
        client.name = f"{body.first_name} {body.last_name}".strip()
        if body.phone:        client.phone        = body.phone
        if body.company_name: client.company_name = body.company_name

    # Build a readable title from template field option labels where possible
    answers = body.answers
    pod_type_val = answers.get("pod_type", "")
    pod_type_label = _option_label(template, "pod_type", pod_type_val) or template["name"]

    quantity   = int(answers.get("quantity", 1))
    location   = answers.get("location") or ""
    qty_str    = f" ×{quantity}" if quantity > 1 else ""
    loc_str    = f" — {location}" if location else ""
    title      = f"{pod_type_label}{qty_str}{loc_str}"

    # Build human-readable notes block for internal use
    note_parts = []
    size_opt = answers.get("size_option")
    if size_opt:
        size_label = _option_label(template, "size_option", size_opt) or size_opt
        note_parts.append(f"Size: {size_label}")
    w = answers.get("width_m")
    l = answers.get("length_m")
    if w and l:
        note_parts.append(f"Dimensions: {w}m × {l}m")
    use_val = answers.get("intended_use")
    if use_val:
        note_parts.append(f"Use: {_option_label(template, 'intended_use', use_val) or use_val}")
    tl_val = answers.get("timeline")
    if tl_val:
        note_parts.append(f"Timeline: {_option_label(template, 'timeline', tl_val) or tl_val}")
    if answers.get("notes"):
        note_parts.append(f"\n{answers['notes']}")
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
        # Structured snapshot — template_id + all answers stored together.
        # The onboarding agent and pricing engine read this to auto-populate
        # the pod spec when a manufacturer's template is activated.
        spec_snapshot = {
            "product_template_id":      body.product_template_id,
            "product_template_version": template.get("version", "1.0.0"),
            "questionnaire_answers":    answers,
            # Contact fields stored separately for quick access
            "contact": {
                "first_name":   body.first_name,
                "last_name":    body.last_name,
                "email":        body.email,
                "phone":        body.phone,
                "company_name": body.company_name,
            },
        },
    )
    db.add(quote)
    db.flush()

    db.add(QuoteEvent(
        quote_id   = quote.id,
        event_type = "enquiry_received",
        old_status = None,
        new_status = "draft",
        note       = f"Website enquiry from {body.email} via template '{body.product_template_id}'",
        created_by = "system",
    ))

    db.commit()

    return EnquiryOut(
        reference = ref,
        client_id = client.id,
        quote_id  = quote.id,
        message   = f"Thank you {body.first_name}, we've received your enquiry and will be in touch shortly.",
    )


def _option_label(template: dict, field_key: str, value: str) -> str | None:
    """Return the display label for a select option, or None if not found."""
    for field in template.get("fields", []):
        if field["key"] == field_key:
            for opt in field.get("options", []):
                if opt["value"] == value:
                    return opt["label"]
    return None
