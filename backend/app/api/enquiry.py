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
from app.models import AccountSettings, Client, PodSpec, Quote, QuoteEvent
from app.api.email_service import send_email
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

    # Extract totals from estimate to populate the Quote price columns directly.
    # Without this the dashboard sees EUR— even when an estimate was calculated.
    total_ex_vat  = None
    total_inc_vat = None
    if pricing_estimate and pricing_estimate.get("status") == "estimated":
        total_ex_vat  = pricing_estimate.get("total_ex_vat")
        total_inc_vat = pricing_estimate.get("total_inc_vat")

    # Create a minimal PodSpec so the quote has pod_spec_id populated.
    # This enables the RFQ tab, prevents "No pod spec" dashboard warnings,
    # and gives the internal team a starting point to add build-ups.
    _w_f = float(w) if w else None
    _l_f = float(l) if l else None
    _h_f = float(h) if h else None
    pod_spec = PodSpec(
        name   = title,
        geometry = {
            "width_m":  _w_f,
            "length_m": _l_f,
            "height_m": _h_f,
            "source":   "enquiry",
        },
        status = "draft",
    )
    db.add(pod_spec)
    db.flush()

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
        total_ex_vat  = total_ex_vat,
        total_inc_vat = total_inc_vat,
        pod_spec_id  = pod_spec.id,
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
        event_type = "quote_created_from_enquiry",
        old_status = None,
        new_status = "draft",
        note       = f"Website enquiry from {body.email} via template '{body.product_template_id}'",
        created_by = "system",
    ))

    db.commit()

    # ── Emails ───────────────────────────────────────────────────────────────
    settings = db.query(AccountSettings).first()
    company_name = (settings and settings.company_name) or "Top-R Solutions"

    # Acknowledgement to client
    send_email(
        to=body.email,
        subject=f"We've received your enquiry — {title}",
        html=(
            f"<p>Hi {body.first_name},</p>"
            f"<p>Thanks for reaching out to {company_name}. We've received your enquiry "
            f"for a <strong>{title}</strong> and will review it and get back to you shortly.</p>"
            f"<p>Your reference number is <strong>{ref}</strong>. Please quote this in any correspondence with us.</p>"
            f"<p>Best regards,<br>{company_name}</p>"
        ),
    )

    # Internal new-lead alert
    if settings and settings.notify_email:
        phone_line = f"<br>Phone: {body.phone}" if body.phone else ""
        company_line = f"<br>Company: {body.company_name}" if body.company_name else ""
        send_email(
            to=settings.notify_email,
            subject=f"[NEW ENQUIRY] {body.first_name} {body.last_name} — {title}",
            html=(
                f"<p>A new enquiry has been submitted via the website.</p>"
                f"<p><strong>Client:</strong> {body.first_name} {body.last_name}"
                f"<br>Email: {body.email}{phone_line}{company_line}</p>"
                f"<p><strong>Product:</strong> {title}<br>"
                f"<strong>Reference:</strong> {ref}</p>"
            ),
        )
    # ─────────────────────────────────────────────────────────────────────────

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
    Returns status='incomplete' if dimensions are missing.
    Returns status='estimated' with full provisional_breakdown on success.

    provisional_breakdown is a list of line items covering every priced
    component — structure: {code, category, description, qty, unit,
    unit_rate_ex_vat, subtotal_ex_vat}.  The internal team sees this as
    the indicative BOM; the client portal shows descriptions only.
    """
    pe = template.get("pricing_estimates")
    if not pe:
        return None

    w = answers.get("width_m")
    l = answers.get("length_m")
    if not w or not l:
        return {
            "status":     "incomplete",
            "reason":     "Dimensions not provided — estimate cannot be calculated.",
            "disclaimer": pe.get("disclaimer", ""),
        }

    try:
        w   = float(w)
        l   = float(l)
        h   = float(answers.get("height_m") or 2.5)
        qty = int(answers.get("quantity") or 1)

        floor_area = round(w * l, 2)
        base_rate  = pe["base_rate_per_m2_ex_vat"]
        addons     = pe.get("addons", {})

        breakdown: list[dict] = []

        def _line(code, category, description, line_qty, unit, unit_rate):
            sub = round(line_qty * unit_rate, 2)
            breakdown.append({
                "code":             code,
                "category":         category,
                "description":      description,
                "qty":              round(line_qty, 3),
                "unit":             unit,
                "unit_rate_ex_vat": round(unit_rate, 2),
                "subtotal_ex_vat":  sub,
            })
            return sub

        total = _line(
            "pod_base", "structure",
            f"Pod base structure ({w}m × {l}m)",
            floor_area, "m²", base_rate,
        )

        # Height premium
        hp = addons.get("height_premium")
        if hp and h > hp["threshold_m"]:
            total += _line("height_premium", "structure",
                           f"Height premium (>{hp['threshold_m']}m)",
                           1, "set", hp["flat"])

        # External finish
        ext_finish = answers.get("external_finish")
        if ext_finish:
            addon = addons.get(ext_finish)
            if addon:
                rate = addon.get("per_m2", 0)
                flat = addon.get("flat", 0)
                label = addon.get("label", ext_finish)
                if rate:
                    total += _line(f"ext_{ext_finish}", "external_finish",
                                   label, floor_area, "m²", rate)
                elif flat:
                    total += _line(f"ext_{ext_finish}", "external_finish",
                                   label, 1, "set", flat)

        # Internal finish (uplifts above basic)
        int_finish = answers.get("internal_finish_package")
        if int_finish == "standard":
            a = addons.get("internal_standard")
            if a:
                total += _line("int_standard", "internal_finish",
                               a.get("label", "Standard Internal Finish"),
                               floor_area, "m²", a["per_m2"])
        elif int_finish == "premium":
            a = addons.get("internal_premium")
            if a:
                total += _line("int_premium", "internal_finish",
                               a.get("label", "Premium Internal Finish"),
                               floor_area, "m²", a["per_m2"])

        # Doors
        door_count = int(answers.get("door_count") or 0)
        door_type  = answers.get("door_type") or ""
        if door_count > 0:
            door_key = {
                "single":  "door_single",
                "double":  "door_double",
                "sliding": "door_sliding",
                "bi_fold": "door_bi_fold",
            }.get(door_type, "door_default")
            a = addons.get(door_key, addons.get("door_default", {}))
            rate = a.get("per_unit", 700)
            label = a.get("label", addons.get("door_default", {}).get("label", "Door"))
            total += _line("doors", "openings", label, door_count, "each", rate)

        # Windows
        window_count = int(answers.get("window_count") or 0)
        window_type  = answers.get("window_type") or ""
        if window_count > 0:
            win_key = {
                "fixed":     "window_fixed",
                "casement":  "window_casement",
                "tilt_turn": "window_tilt_turn",
            }.get(window_type, "window_default")
            a = addons.get(win_key, addons.get("window_default", {}))
            rate = a.get("per_unit", 420)
            label = a.get("label", addons.get("window_default", {}).get("label", "Window"))
            total += _line("windows", "openings", label, window_count, "each", rate)

        # Rooflights
        rooflight_count = int(answers.get("rooflight_count") or 0)
        if rooflight_count > 0:
            a = addons.get("rooflight_unit", {})
            rate = a.get("per_unit", 780)
            total += _line("rooflights", "openings",
                           a.get("label", "Rooflight / Skylight"),
                           rooflight_count, "each", rate)

        # Heating
        heating = answers.get("heating_option")
        if heating == "underfloor":
            a = addons.get("underfloor_heating", {})
            total += _line("heating_ufh", "services",
                           a.get("label", "Underfloor Heating"),
                           floor_area, "m²", a.get("per_m2", 80))
        elif heating == "air_source":
            a = addons.get("air_source_heat_pump", {})
            total += _line("heating_ashp", "services",
                           a.get("label", "Air Source Heat Pump"),
                           1, "set", a.get("flat", 3000))

        # Ventilation
        if answers.get("ventilation_option") == "mvhr":
            a = addons.get("mvhr", {})
            total += _line("ventilation_mvhr", "services",
                           a.get("label", "MVHR Ventilation Unit"),
                           1, "set", a.get("flat", 1500))

        # Electrical
        electrical = answers.get("electrical_package")
        if electrical == "standard":
            a = addons.get("standard_electrical", {})
            total += _line("electrical_std", "services",
                           a.get("label", "Standard Electrical Package"),
                           1, "set", a.get("flat", 250))
        elif electrical == "full":
            a = addons.get("full_electrical", {})
            total += _line("electrical_full", "services",
                           a.get("label", "Full Electrical Package"),
                           1, "set", a.get("flat", 500))

        # Foundation
        foundation = answers.get("foundation_option")
        if foundation == "screw_pile":
            a = addons.get("screw_pile", {})
            total += _line("foundation_screw_pile", "foundation",
                           a.get("label", "Screw Pile Foundation"),
                           1, "set", a.get("flat", 2500))
        elif foundation == "groundworks":
            a = addons.get("foundation_groundworks", {})
            total += _line("foundation_groundworks", "foundation",
                           a.get("label", "Concrete Pad / Groundworks"),
                           1, "set", a.get("flat", 3500))
        elif foundation == "pad_stone":
            a = addons.get("foundation_pad_stone", {})
            total += _line("foundation_pad_stone", "foundation",
                           a.get("label", "Pad Stone / Timber Frame"),
                           1, "set", a.get("flat", 1200))

        # Delivery & install
        delivery = answers.get("delivery_install_option")
        if delivery == "supply_install":
            a = addons.get("supply_install", {})
            total += _line("delivery_install", "delivery",
                           a.get("label", "Supply & Install"),
                           1, "set", a.get("flat", 2000))
        elif delivery == "turnkey":
            a = addons.get("turnkey", {})
            total += _line("delivery_turnkey", "delivery",
                           a.get("label", "Turnkey Package"),
                           1, "set", a.get("flat", 5000))

        # Multiply by quantity (all breakdown lines are per-unit; multiply totals)
        total_unit  = total
        total_total = total * qty
        vat_rate    = pe["vat_rate"]
        vat         = total_total * vat_rate

        # Build human-readable addons_applied list (backward compat with dashboard display)
        addons_applied = [
            f"{ln['description']}: €{ln['subtotal_ex_vat']:,.0f}"
            for ln in breakdown
            if ln["code"] != "pod_base"
        ]

        return {
            "status":              "estimated",
            "floor_area_m2":       floor_area,
            "quantity":            qty,
            "unit_ex_vat":         round(total_unit, 2),
            "total_ex_vat":        round(total_total, 2),
            "total_inc_vat":       round(total_total + vat, 2),
            "vat_amount":          round(vat, 2),
            "vat_rate":            vat_rate,
            "provisional_breakdown": breakdown,
            "addons_applied":      addons_applied,
            "calculation_notes":   f"€{base_rate}/m² base × {floor_area}m² × {qty} unit(s)",
            "disclaimer":          pe.get("disclaimer", ""),
        }

    except (TypeError, ValueError) as exc:
        return {"status": "error", "reason": str(exc)}
