"""
Public enquiry endpoints — no auth required.

GET  /enquiry/templates              list active product templates
GET  /enquiry/templates/{id}         full template schema (fields, options, constraints)
POST /enquiry                        submit a quote enquiry

POST /enquiry creates a Client record (or matches by email) and a Draft Quote.
The submitted questionnaire answers are stored as structured JSON in
spec_snapshot so they are available to the internal team and future
agentic processing.
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
    """List all active product templates."""
    return list_active_templates()


@router.get("/templates/{template_id}")
def get_template_schema(template_id: str):
    """Return the full template schema for a product type."""
    template = get_template(template_id)
    if not template:
        raise HTTPException(404, f"Template '{template_id}' not found")
    return template


# ── Enquiry submission ────────────────────────────────────────────────────────

class EnquiryIn(BaseModel):
    first_name:   str
    last_name:    str
    email:        str
    phone:        str | None = None
    company_name: str | None = None
    product_template_id: str = "office_pod"
    answers: dict = {}


class EnquiryOut(BaseModel):
    reference:  str
    client_id:  uuid.UUID
    quote_id:   uuid.UUID
    message:    str


@router.post("", response_model=EnquiryOut, status_code=201)
def submit_enquiry(body: EnquiryIn, db: Db):
    template = get_template(body.product_template_id)
    if not template:
        raise HTTPException(400, f"Unknown product_template_id: '{body.product_template_id}'")

    required_answer_keys = [
        f["key"] for f in template["fields"]
        if f.get("required") and f["step"] != "contact"
    ]
    missing = [k for k in required_answer_keys if not body.answers.get(k)]
    if missing:
        raise HTTPException(422, f"Missing required fields: {', '.join(missing)}")

    now = _now()

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

    answers = body.answers
    pod_type_val   = answers.get("pod_type", "")
    pod_type_label = _option_label(template, "pod_type", pod_type_val) or template["name"]
    quantity   = int(answers.get("quantity", 1))
    location   = answers.get("location") or ""
    qty_str    = f" ×{quantity}" if quantity > 1 else ""
    loc_str    = f" — {location}" if location else ""
    title      = f"{pod_type_label}{qty_str}{loc_str}"

    # Build human-readable internal notes from all answered fields
    note_parts = []

    # Dimensions
    w = answers.get("width_m")
    l = answers.get("length_m")
    h = answers.get("height_m")
    if w and l:
        dim = f"Dimensions: {w}m × {l}m"
        if h:
            dim += f" × {h}m (H)"
        note_parts.append(dim)

    # Openings
    door_count   = answers.get("door_count")
    door_type    = answers.get("door_type")
    window_count = answers.get("window_count")
    window_type  = answers.get("window_type")
    rooflight    = answers.get("rooflight_count")
    if door_count is not None:
        dt = _option_label(template, "door_type", door_type or "") or door_type or ""
        note_parts.append(f"Doors: {door_count}" + (f" ({dt})" if dt else ""))
    if window_count is not None:
        wt = _option_label(template, "window_type", window_type or "") or window_type or ""
        note_parts.append(f"Windows: {window_count}" + (f" ({wt})" if wt else ""))
    if rooflight:
        note_parts.append(f"Rooflights: {rooflight}")

    # Finishes
    ext_finish = answers.get("external_finish")
    int_finish = answers.get("internal_finish_package")
    if ext_finish:
        note_parts.append(f"External finish: {_option_label(template, 'external_finish', ext_finish) or ext_finish}")
    if int_finish:
        note_parts.append(f"Internal finish: {_option_label(template, 'internal_finish_package', int_finish) or int_finish}")

    # Services
    heating = answers.get("heating_option")
    ventilation = answers.get("ventilation_option")
    electrical = answers.get("electrical_package")
    if heating:
        note_parts.append(f"Heating: {_option_label(template, 'heating_option', heating) or heating}")
    if ventilation:
        note_parts.append(f"Ventilation: {_option_label(template, 'ventilation_option', ventilation) or ventilation}")
    if electrical:
        note_parts.append(f"Electrical: {_option_label(template, 'electrical_package', electrical) or electrical}")

    # Foundation & delivery
    foundation = answers.get("foundation_option")
    delivery   = answers.get("delivery_install_option")
    if foundation:
        note_parts.append(f"Foundation: {_option_label(template, 'foundation_option', foundation) or foundation}")
    if delivery:
        note_parts.append(f"Delivery: {_option_label(template, 'delivery_install_option', delivery) or delivery}")

    # Project context
    use_val = answers.get("intended_use")
    if use_val:
        note_parts.append(f"Use: {_option_label(template, 'intended_use', use_val) or use_val}")
    tl_val = answers.get("timeline")
    if tl_val:
        note_parts.append(f"Timeline: {_option_label(template, 'timeline', tl_val) or tl_val}")
    if answers.get("notes"):
        note_parts.append(f"\n{answers['notes']}")

    notes_text = "\n".join(note_parts) if note_parts else None

    # Compute pricing estimate
    pricing_estimate = _estimate_price(template, answers)

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
        spec_snapshot = {
            "product_template_id":      body.product_template_id,
            "product_template_version": template.get("version", "2.0.0"),
            "questionnaire_answers":    answers,
            "pricing_estimate":         pricing_estimate,
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _option_label(template: dict, field_key: str, value: str) -> str | None:
    """Return the display label for a select option, or None if not found."""
    for field in template.get("fields", []):
        if field["key"] == field_key:
            for opt in field.get("options", []):
                if opt["value"] == value:
                    return opt["label"]
    return None


def _estimate_price(template: dict, answers: dict) -> dict | None:
    """
    Compute an indicative pricing estimate from questionnaire answers.
    Returns None if the template has no pricing_estimates config.
    Returns a dict with status='incomplete' if dimensions are missing.
    """
    pe = template.get("pricing_estimates")
    if not pe:
        return None

    w = answers.get("width_m")
    l = answers.get("length_m")
    if not w or not l:
        return {
            "status": "incomplete",
            "reason": "Dimensions not provided — estimate cannot be calculated.",
            "disclaimer": pe.get("disclaimer", ""),
        }

    try:
        w   = float(w)
        l   = float(l)
        h   = float(answers.get("height_m") or 2.5)
        qty = int(answers.get("quantity") or 1)
        floor_area   = round(w * l, 2)
        base_rate    = pe["base_rate_per_m2_ex_vat"]
        total        = floor_area * base_rate
        addons_applied: list[str] = []
        addons = pe.get("addons", {})

        # External finish
        ext_finish = answers.get("external_finish")
        if ext_finish and ext_finish in addons:
            addon = addons[ext_finish]
            cost  = floor_area * addon.get("per_m2", 0) + addon.get("flat", 0)
            if cost:
                total += cost
                addons_applied.append(f"{ext_finish}: +€{cost:,.0f}")

        # Height premium
        hp = addons.get("height_premium")
        if hp and h > hp["threshold_m"]:
            total += hp["flat"]
            addons_applied.append(f"Height >{hp['threshold_m']}m: +€{hp['flat']:,.0f}")

        # Heating
        heating = answers.get("heating_option")
        if heating == "underfloor" and "underfloor_heating" in addons:
            cost = floor_area * addons["underfloor_heating"]["per_m2"]
            total += cost
            addons_applied.append(f"Underfloor heating: +€{cost:,.0f}")
        elif heating == "air_source" and "air_source_heat_pump" in addons:
            cost = addons["air_source_heat_pump"]["flat"]
            total += cost
            addons_applied.append(f"Air source heat pump: +€{cost:,.0f}")

        # MVHR
        if answers.get("ventilation_option") == "mvhr" and "mvhr" in addons:
            cost = addons["mvhr"]["flat"]
            total += cost
            addons_applied.append(f"MVHR: +€{cost:,.0f}")

        # Electrical
        if answers.get("electrical_package") == "full" and "full_electrical" in addons:
            cost = addons["full_electrical"]["flat"]
            total += cost
            addons_applied.append(f"Full electrical package: +€{cost:,.0f}")

        # Delivery
        delivery = answers.get("delivery_install_option")
        if delivery == "supply_install" and "supply_install" in addons:
            cost = addons["supply_install"]["flat"]
            total += cost
            addons_applied.append(f"Supply & install: +€{cost:,.0f}")
        elif delivery == "turnkey" and "turnkey" in addons:
            cost = addons["turnkey"]["flat"]
            total += cost
            addons_applied.append(f"Turnkey package: +€{cost:,.0f}")

        # Foundation
        if answers.get("foundation_option") == "screw_pile" and "screw_pile" in addons:
            cost = addons["screw_pile"]["flat"]
            total += cost
            addons_applied.append(f"Screw pile foundation: +€{cost:,.0f}")

        # Multiply by quantity
        total_unit = total
        total      = total * qty
        vat_rate   = pe["vat_rate"]
        vat        = total * vat_rate

        return {
            "status":             "estimated",
            "floor_area_m2":      floor_area,
            "quantity":           qty,
            "unit_ex_vat":        round(total_unit, 2),
            "total_ex_vat":       round(total, 2),
            "total_inc_vat":      round(total + vat, 2),
            "vat_amount":         round(vat, 2),
            "vat_rate":           vat_rate,
            "addons_applied":     addons_applied,
            "calculation_notes":  f"€{base_rate}/m² base × {floor_area}m² × {qty} unit(s)",
            "disclaimer":         pe.get("disclaimer", ""),
        }

    except (TypeError, ValueError) as exc:
        return {"status": "error", "reason": str(exc)}
