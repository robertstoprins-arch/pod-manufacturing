"""
RFQ supplier response API

POST /quotes/{quote_id}/rfq/send          create rfq_request rows + return shareable links
GET  /quotes/{quote_id}/rfq/responses     list all requests + responses for a quote
GET  /rfq/respond/{token}                 public — supplier fetches items to price
POST /rfq/respond/{token}                 public — supplier submits prices
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Quote, RfqRequest, RfqResponseLine

router_quotes = APIRouter(prefix="/quotes", tags=["rfq"])
router_public = APIRouter(prefix="/rfq", tags=["rfq"])

Db = Annotated[Session, Depends(get_db)]


def _now():
    return datetime.now(timezone.utc)


# ── Schemas ───────────────────────────────────────────────────────────────────

class SendTargetIn(BaseModel):
    supplier_name: str
    supplier_email: str | None = None
    supplier_id: uuid.UUID | None = None
    items: list[dict]                   # subset of RFQ items for this supplier


class SendRfqIn(BaseModel):
    targets: list[SendTargetIn]
    expires_days: int = 14


class RfqRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quote_id: uuid.UUID
    supplier_name: str
    supplier_email: str | None
    token: uuid.UUID
    status: str
    items_json: list
    sent_at: datetime | None
    viewed_at: datetime | None
    responded_at: datetime | None
    expires_at: datetime | None
    response_notes: str | None
    response_currency: str | None
    response_valid_until: datetime | None
    response_total: float | None
    created_at: datetime | None
    response_lines: list["RfqResponseLineOut"]


class RfqResponseLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    line_id: str
    description: str | None
    unit_price: float | None
    quantity: float | None
    total_price: float | None
    currency: str | None
    lead_time_days: int | None
    availability: str | None
    substitute_offered: bool
    substitute_description: str | None
    notes: str | None


class SupplierResponseLineIn(BaseModel):
    line_id: str
    unit_price: float | None = None
    quantity: float | None = None
    total_price: float | None = None
    currency: str | None = None
    lead_time_days: int | None = None
    availability: str | None = None
    substitute_offered: bool = False
    substitute_description: str | None = None
    notes: str | None = None


class SupplierResponseIn(BaseModel):
    supplier_name: str | None = None   # override if supplier wants to correct
    notes: str | None = None
    currency: str | None = None
    valid_until: datetime | None = None
    lines: list[SupplierResponseLineIn]


class PublicRfqOut(BaseModel):
    rfq_request_id: uuid.UUID
    supplier_name: str
    quote_title: str
    quote_number: str | None
    client_name: str | None
    currency: str
    expires_at: datetime | None
    items: list[dict]
    already_responded: bool


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_404(db: Session, quote_id: uuid.UUID) -> Quote:
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(404, "Quote not found")
    return q


# ── Routes: quote-scoped ──────────────────────────────────────────────────────

@router_quotes.post("/{quote_id}/rfq/send", response_model=list[RfqRequestOut], status_code=201)
def send_rfq(quote_id: uuid.UUID, body: SendRfqIn, db: Db):
    quote = _get_or_404(db, quote_id)
    from datetime import timedelta

    now = _now()
    expires_at = now + timedelta(days=body.expires_days)
    created = []

    for target in body.targets:
        req = RfqRequest(
            quote_id=quote_id,
            supplier_id=target.supplier_id,
            supplier_name=target.supplier_name,
            supplier_email=target.supplier_email,
            token=uuid.uuid4(),
            status="pending",
            items_json=target.items,
            sent_at=now,
            expires_at=expires_at,
        )
        db.add(req)
        created.append(req)

    db.commit()
    for r in created:
        db.refresh(r)
    return created


@router_quotes.get("/{quote_id}/rfq/responses", response_model=list[RfqRequestOut])
def list_rfq_responses(quote_id: uuid.UUID, db: Db):
    _get_or_404(db, quote_id)
    return (
        db.query(RfqRequest)
        .filter(RfqRequest.quote_id == quote_id)
        .order_by(RfqRequest.created_at.desc())
        .all()
    )


@router_quotes.get("/{quote_id}/rfq/comparison")
def get_rfq_comparison(quote_id: uuid.UUID, db: Db):
    """
    Side-by-side comparison of all responded supplier RFQ requests for a quote.

    Returns:
    - lines: one row per original item, with each supplier's price/lead
    - suppliers: ordered list of responding supplier names + totals
    - cheapest_total: supplier name with lowest overall total
    - margin: if quote has total_ex_vat, shows diff vs cheapest total
    """
    quote = _get_or_404(db, quote_id)

    responded = (
        db.query(RfqRequest)
        .filter(RfqRequest.quote_id == quote_id, RfqRequest.status == "responded")
        .order_by(RfqRequest.responded_at)
        .all()
    )

    if not responded:
        return {
            "has_responses": False,
            "suppliers": [],
            "lines": [],
            "totals": {},
            "cheapest_total_supplier": None,
            "quote_total_ex_vat": float(quote.total_ex_vat) if quote.total_ex_vat else None,
            "margin": None,
        }

    # Build index: {line_id -> {supplier_name -> response_line}}
    all_line_ids: list[str] = []
    seen_line_ids: set[str] = set()
    supplier_names = [r.supplier_name for r in responded]

    # Collect all line_ids in order they appear across supplier items_json
    for req in responded:
        for item in (req.items_json or []):
            lid = str(item.get("line_id", ""))
            if lid and lid not in seen_line_ids:
                all_line_ids.append(lid)
                seen_line_ids.add(lid)

    # Build lookup: supplier_name -> {line_id -> RfqResponseLine}
    supplier_line_map: dict[str, dict[str, object]] = {}
    item_meta: dict[str, dict] = {}  # line_id -> {description, unit, element_type}

    for req in responded:
        supplier_line_map[req.supplier_name] = {
            line.line_id: line for line in req.response_lines
        }
        for item in (req.items_json or []):
            lid = str(item.get("line_id", ""))
            if lid and lid not in item_meta:
                item_meta[lid] = {
                    "description": item.get("description", ""),
                    "unit": item.get("unit", ""),
                    "quantity": item.get("quantity"),
                    "element_type": item.get("element_type", ""),
                    "estimated_unit_price": item.get("estimated_unit_price"),
                    "estimated_line_cost": item.get("estimated_line_cost"),
                    "currency": item.get("currency", quote.currency or "EUR"),
                }

    # Build line rows
    lines = []
    for lid in all_line_ids:
        meta = item_meta.get(lid, {})
        supplier_cells = {}
        prices = []
        for sname in supplier_names:
            rline = supplier_line_map.get(sname, {}).get(lid)
            if rline:
                cell = {
                    "unit_price": float(rline.unit_price) if rline.unit_price is not None else None,
                    "total_price": float(rline.total_price) if rline.total_price is not None else None,
                    "lead_time_days": rline.lead_time_days,
                    "availability": rline.availability,
                    "substitute_offered": rline.substitute_offered,
                    "notes": rline.notes,
                    "currency": rline.currency or quote.currency or "EUR",
                }
                if rline.unit_price is not None:
                    prices.append((sname, float(rline.unit_price)))
            else:
                cell = None
            supplier_cells[sname] = cell

        cheapest_supplier = min(prices, key=lambda x: x[1])[0] if len(prices) > 1 else None

        lines.append({
            "line_id": lid,
            "description": meta.get("description", ""),
            "unit": meta.get("unit", ""),
            "quantity": meta.get("quantity"),
            "element_type": meta.get("element_type", ""),
            "estimated_unit_price": meta.get("estimated_unit_price"),
            "estimated_line_cost": meta.get("estimated_line_cost"),
            "suppliers": supplier_cells,
            "cheapest_supplier": cheapest_supplier,
        })

    # Compute per-supplier totals
    totals: dict[str, float | None] = {}
    for req in responded:
        t = float(req.response_total) if req.response_total is not None else None
        if t is None:
            # Sum from response lines
            s = sum(
                float(l.total_price)
                for l in req.response_lines
                if l.total_price is not None
            )
            t = round(s, 2) if s else None
        totals[req.supplier_name] = t

    valid_totals = {k: v for k, v in totals.items() if v is not None}
    cheapest_total_supplier = min(valid_totals, key=lambda k: valid_totals[k]) if valid_totals else None
    cheapest_total = valid_totals.get(cheapest_total_supplier) if cheapest_total_supplier else None

    # Margin calculation
    margin = None
    if cheapest_total is not None and quote.total_ex_vat is not None:
        quoted = float(quote.total_ex_vat)
        margin = {
            "quoted_ex_vat": quoted,
            "cheapest_procurement_total": cheapest_total,
            "gross_margin": round(quoted - cheapest_total, 2),
            "gross_margin_pct": round((quoted - cheapest_total) / quoted * 100, 1) if quoted else None,
        }

    # Supplier summary rows
    supplier_summary = []
    for req in responded:
        supplier_summary.append({
            "supplier_name": req.supplier_name,
            "supplier_email": req.supplier_email,
            "status": req.status,
            "responded_at": req.responded_at.isoformat() if req.responded_at else None,
            "response_currency": req.response_currency or quote.currency or "EUR",
            "response_notes": req.response_notes,
            "response_valid_until": req.response_valid_until.isoformat() if req.response_valid_until else None,
            "total": totals.get(req.supplier_name),
            "is_cheapest": req.supplier_name == cheapest_total_supplier,
        })

    return {
        "has_responses": True,
        "suppliers": supplier_summary,
        "lines": lines,
        "totals": totals,
        "cheapest_total_supplier": cheapest_total_supplier,
        "quote_total_ex_vat": float(quote.total_ex_vat) if quote.total_ex_vat else None,
        "margin": margin,
    }


@router_quotes.delete("/{quote_id}/rfq/requests/{request_id}", status_code=204)
def delete_rfq_request(quote_id: uuid.UUID, request_id: uuid.UUID, db: Db):
    req = db.query(RfqRequest).filter(
        RfqRequest.id == request_id,
        RfqRequest.quote_id == quote_id,
    ).first()
    if not req:
        raise HTTPException(404, "RFQ request not found")
    db.delete(req)
    db.commit()


# ── Routes: public (no auth) ──────────────────────────────────────────────────

@router_public.get("/respond/{token}", response_model=PublicRfqOut)
def get_supplier_rfq(token: uuid.UUID, db: Db):
    req = db.query(RfqRequest).filter(RfqRequest.token == token).first()
    if not req:
        raise HTTPException(404, "This link is invalid or has expired")

    now = _now()
    if req.expires_at and req.expires_at < now:
        raise HTTPException(410, "This RFQ link has expired")

    if not req.viewed_at:
        req.viewed_at = now
        req.status = "viewed"
        db.commit()

    quote = db.query(Quote).filter(Quote.id == req.quote_id).first()

    return PublicRfqOut(
        rfq_request_id=req.id,
        supplier_name=req.supplier_name,
        quote_title=quote.title if quote else "",
        quote_number=quote.quote_number if quote else None,
        client_name=quote.client_name if quote else None,
        currency=quote.currency if quote else "EUR",
        expires_at=req.expires_at,
        items=req.items_json or [],
        already_responded=req.status == "responded",
    )


@router_public.post("/respond/{token}", response_model=RfqRequestOut)
def submit_supplier_response(token: uuid.UUID, body: SupplierResponseIn, db: Db):
    req = db.query(RfqRequest).filter(RfqRequest.token == token).first()
    if not req:
        raise HTTPException(404, "This link is invalid or has expired")

    now = _now()
    if req.expires_at and req.expires_at < now:
        raise HTTPException(410, "This RFQ link has expired")

    # Clear any previous response lines (allow resubmission)
    for line in req.response_lines:
        db.delete(line)

    for li in body.lines:
        # Auto-compute total if not provided
        total = li.total_price
        if total is None and li.unit_price is not None and li.quantity is not None:
            total = round(float(li.unit_price) * float(li.quantity), 2)

        db.add(RfqResponseLine(
            rfq_request_id=req.id,
            line_id=li.line_id,
            description=next(
                (i.get("description") for i in (req.items_json or []) if str(i.get("line_id")) == str(li.line_id)),
                None,
            ),
            unit_price=li.unit_price,
            quantity=li.quantity,
            total_price=total,
            currency=li.currency or body.currency or req.response_currency,
            lead_time_days=li.lead_time_days,
            availability=li.availability,
            substitute_offered=li.substitute_offered,
            substitute_description=li.substitute_description,
            notes=li.notes,
        ))

    # Compute response total
    response_total = sum(
        float(li.unit_price or 0) * float(li.quantity or 0)
        for li in body.lines
        if li.unit_price is not None
    ) or None

    req.responded_at = now
    req.status = "responded"
    if body.notes:
        req.response_notes = body.notes
    if body.currency:
        req.response_currency = body.currency
    if body.valid_until:
        req.response_valid_until = body.valid_until
    if response_total:
        req.response_total = round(response_total, 2)

    db.commit()
    db.refresh(req)
    return req
