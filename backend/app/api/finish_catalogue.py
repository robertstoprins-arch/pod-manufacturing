"""
API: Finish & Furniture Catalogue

GET  /finish-catalogue                  list (filterable by category, customer_visible, is_active)
GET  /finish-catalogue/categories       list distinct category values
GET  /finish-catalogue/{id}             get single item
POST /finish-catalogue                  create item
PUT  /finish-catalogue/{id}             update item
DELETE /finish-catalogue/{id}           soft-delete (sets is_active=False)

Image visibility rule:
  Only items with image_approval_status in the APPROVED_STATUSES set have their
  image_url forwarded when the request comes from a customer-facing context.
  Internal admin endpoints always return the raw url.
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import FinishCatalogueItem

Db = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/finish-catalogue", tags=["finish-catalogue"])

# Only these statuses may supply an image_url in customer-facing contexts
CUSTOMER_SAFE_IMAGE_STATUSES = {
    "approved_for_customer_pdf",
    "own_photo",
    "licensed_stock",
    "generated_placeholder",
}

VALID_CATEGORIES = {
    "external_cladding", "internal_paint", "internal_timber_finish", "flooring",
    "sanitaryware", "toilet", "vanity_unit", "kitchenette", "furniture_set",
    "lighting", "heating_visible", "ventilation_visible", "cctv_data",
    "solar_battery", "delivery_install", "other",
}

VALID_IMAGE_SOURCE_TYPES = {
    "none", "placeholder", "generated_placeholder", "own_photo",
    "licensed_stock", "supplier_reference", "supplier_approved", "needs_review",
}

VALID_IMAGE_APPROVAL_STATUSES = {
    "missing", "internal_reference_only", "needs_approval",
    "approved_for_customer_pdf", "own_photo", "licensed_stock", "generated_placeholder",
}

VALID_QUANTITY_RULES = {
    "each", "per_m2_floor_area", "per_m2_wall_area", "per_m2_roof_area",
    "per_lm_perimeter", "manual", "package_fixed",
}


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class CatalogueItemOut(BaseModel):
    id: int
    code: str
    category: str
    name: str
    customer_name: Optional[str]
    customer_description: Optional[str]
    internal_description: Optional[str]
    supplier_name: Optional[str]
    manufacturer: Optional[str]
    supplier_url: Optional[str]
    specification_url: Optional[str]
    datasheet_url: Optional[str]
    image_url: Optional[str]
    image_alt_text: Optional[str]
    image_source_type: str
    image_approval_status: str
    unit: Optional[str]
    unit_cost: Optional[float]
    currency: Optional[str]
    price_type: Optional[str]
    default_quantity: Optional[float]
    quantity_rule: Optional[str]
    included_by_default: bool
    customer_visible: bool
    internal_only: bool
    specification_url_public: bool
    suitable_pod_types: Optional[list]
    package_tags: Optional[list]
    lead_time_note: Optional[str]
    notes: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


class CatalogueItemCustomerOut(BaseModel):
    """Stripped schema for customer-facing use — no internal/supplier details."""
    id: int
    code: str
    category: str
    customer_name: Optional[str]
    customer_description: Optional[str]
    image_url: Optional[str]              # None if not approved for customer use
    image_alt_text: Optional[str]
    specification_url: Optional[str]      # None unless specification_url_public=True
    unit: Optional[str]
    unit_cost: Optional[float]
    currency: Optional[str]
    default_quantity: Optional[float]
    quantity_rule: Optional[str]
    included_by_default: bool
    package_tags: Optional[list]
    lead_time_note: Optional[str]

    model_config = {"from_attributes": True}


class CatalogueItemIn(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    category: str
    name: str = Field(min_length=1, max_length=255)
    customer_name: Optional[str] = None
    customer_description: Optional[str] = None
    internal_description: Optional[str] = None
    supplier_name: Optional[str] = None
    manufacturer: Optional[str] = None
    supplier_url: Optional[str] = None
    specification_url: Optional[str] = None
    datasheet_url: Optional[str] = None
    image_url: Optional[str] = None
    image_alt_text: Optional[str] = None
    image_source_type: str = "none"
    image_approval_status: str = "missing"
    unit: Optional[str] = None
    unit_cost: Optional[float] = None
    currency: str = "EUR"
    price_type: str = "allowance"
    default_quantity: float = 1.0
    quantity_rule: str = "each"
    included_by_default: bool = False
    customer_visible: bool = True
    internal_only: bool = False
    specification_url_public: bool = False
    suitable_pod_types: Optional[list] = None
    package_tags: Optional[list] = None
    lead_time_note: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/categories")
def list_categories(db: Db):
    """Return all distinct categories that have at least one active item."""
    rows = (
        db.query(FinishCatalogueItem.category)
        .filter(FinishCatalogueItem.is_active == True)
        .distinct()
        .order_by(FinishCatalogueItem.category)
        .all()
    )
    return [r[0] for r in rows]


@router.get("", response_model=list[CatalogueItemOut])
def list_items(
    db: Db,
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    customer_visible: Optional[bool] = Query(None),
    internal_only: Optional[bool] = Query(None),
    package_tag: Optional[str] = Query(None, description="Filter by a single package_tags value"),
    search: Optional[str] = Query(None, description="Case-insensitive search across name, customer_name, supplier_name"),
):
    from sqlalchemy import or_, func
    q = db.query(FinishCatalogueItem)
    if is_active is not None:
        q = q.filter(FinishCatalogueItem.is_active == is_active)
    if category:
        q = q.filter(FinishCatalogueItem.category == category)
    if customer_visible is not None:
        q = q.filter(FinishCatalogueItem.customer_visible == customer_visible)
    if internal_only is not None:
        q = q.filter(FinishCatalogueItem.internal_only == internal_only)
    if search:
        term = f"%{search.lower()}%"
        q = q.filter(or_(
            func.lower(FinishCatalogueItem.name).like(term),
            func.lower(FinishCatalogueItem.customer_name).like(term),
            func.lower(FinishCatalogueItem.supplier_name).like(term),
            func.lower(FinishCatalogueItem.code).like(term),
        ))
    items = q.order_by(FinishCatalogueItem.category, FinishCatalogueItem.id).all()
    if package_tag:
        items = [i for i in items if i.package_tags and package_tag in i.package_tags]
    return items


@router.get("/customer", response_model=list[CatalogueItemCustomerOut])
def list_customer_items(
    db: Db,
    category: Optional[str] = Query(None),
    package_tag: Optional[str] = Query(None),
):
    """
    Customer-facing list. Returns only active, customer_visible, non-internal items.
    image_url is set to None unless image_approval_status is in CUSTOMER_SAFE_IMAGE_STATUSES.
    Supplier URLs and internal data are not included.
    """
    q = (
        db.query(FinishCatalogueItem)
        .filter(
            FinishCatalogueItem.is_active == True,
            FinishCatalogueItem.customer_visible == True,
            FinishCatalogueItem.internal_only == False,
        )
    )
    if category:
        q = q.filter(FinishCatalogueItem.category == category)
    items = q.order_by(FinishCatalogueItem.category, FinishCatalogueItem.id).all()
    if package_tag:
        items = [i for i in items if i.package_tags and package_tag in i.package_tags]

    out = []
    for item in items:
        safe_image = (
            item.image_url
            if item.image_approval_status in CUSTOMER_SAFE_IMAGE_STATUSES
            else None
        )
        # specification_url is only exposed to customers if explicitly marked public
        public_spec_url = item.specification_url if item.specification_url_public else None
        out.append(CatalogueItemCustomerOut(
            id=item.id,
            code=item.code,
            category=item.category,
            customer_name=item.customer_name or item.name,
            customer_description=item.customer_description,
            image_url=safe_image,
            image_alt_text=item.image_alt_text,
            specification_url=public_spec_url,
            unit=item.unit,
            unit_cost=item.unit_cost,
            currency=item.currency,
            default_quantity=item.default_quantity,
            quantity_rule=item.quantity_rule,
            included_by_default=item.included_by_default,
            package_tags=item.package_tags,
            lead_time_note=item.lead_time_note,
        ))
    return out


@router.get("/{item_id}", response_model=CatalogueItemOut)
def get_item(item_id: int, db: Db):
    item = db.get(FinishCatalogueItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Catalogue item not found.")
    return item


@router.post("", response_model=CatalogueItemOut, status_code=201)
def create_item(body: CatalogueItemIn, db: Db):
    if body.category not in VALID_CATEGORIES:
        raise HTTPException(400, f"Invalid category '{body.category}'.")
    if body.image_source_type not in VALID_IMAGE_SOURCE_TYPES:
        raise HTTPException(400, f"Invalid image_source_type '{body.image_source_type}'.")
    if body.image_approval_status not in VALID_IMAGE_APPROVAL_STATUSES:
        raise HTTPException(400, f"Invalid image_approval_status '{body.image_approval_status}'.")
    if body.quantity_rule not in VALID_QUANTITY_RULES:
        raise HTTPException(400, f"Invalid quantity_rule '{body.quantity_rule}'.")
    existing = db.query(FinishCatalogueItem).filter_by(code=body.code).first()
    if existing:
        raise HTTPException(400, f"An item with code '{body.code}' already exists.")
    item = FinishCatalogueItem(**body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=CatalogueItemOut)
def update_item(item_id: int, body: CatalogueItemIn, db: Db):
    item = db.get(FinishCatalogueItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Catalogue item not found.")
    if body.category not in VALID_CATEGORIES:
        raise HTTPException(400, f"Invalid category '{body.category}'.")
    if body.image_source_type not in VALID_IMAGE_SOURCE_TYPES:
        raise HTTPException(400, f"Invalid image_source_type '{body.image_source_type}'.")
    if body.image_approval_status not in VALID_IMAGE_APPROVAL_STATUSES:
        raise HTTPException(400, f"Invalid image_approval_status '{body.image_approval_status}'.")
    if body.quantity_rule not in VALID_QUANTITY_RULES:
        raise HTTPException(400, f"Invalid quantity_rule '{body.quantity_rule}'.")
    # Allow code change only if new code isn't taken by a different item
    if body.code != item.code:
        clash = db.query(FinishCatalogueItem).filter_by(code=body.code).first()
        if clash:
            raise HTTPException(400, f"An item with code '{body.code}' already exists.")
    for field, value in body.model_dump().items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def deactivate_item(item_id: int, db: Db):
    """Soft-delete: sets is_active=False. Hard delete is not exposed."""
    item = db.get(FinishCatalogueItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Catalogue item not found.")
    item.is_active = False
    db.commit()


# ── Draft / Research ──────────────────────────────────────────────────────────

class DraftCandidateIn(BaseModel):
    """Minimal input for a research candidate. Safe defaults applied automatically."""
    name: str = Field(min_length=1, max_length=255)
    category: str
    supplier_name: Optional[str] = None
    manufacturer: Optional[str] = None
    supplier_url: Optional[str] = None
    specification_url: Optional[str] = None
    image_url: Optional[str] = None
    unit_cost: Optional[float] = None
    currency: str = "EUR"
    unit: Optional[str] = None
    quantity_rule: str = "each"
    notes: Optional[str] = None
    # Research context
    market: Optional[str] = None        # e.g. "Sweden", "Finland"
    research_notes: Optional[str] = None  # stored in internal_description


@router.post("/draft", response_model=CatalogueItemOut, status_code=201)
def create_draft(body: DraftCandidateIn, db: Db):
    """
    Create a draft research candidate with safe defaults:
      - is_active = False
      - customer_visible = False
      - image_approval_status = needs_approval
      - image_source_type = supplier_reference (if image_url provided, else none)
      - internal_only = True

    Draft items do not appear in customer-facing endpoints until approved.
    """
    if body.category not in VALID_CATEGORIES:
        raise HTTPException(400, f"Invalid category '{body.category}'.")
    if body.quantity_rule not in VALID_QUANTITY_RULES:
        raise HTTPException(400, f"Invalid quantity_rule '{body.quantity_rule}'.")

    import re, time
    slug = re.sub(r'[^a-z0-9]+', '_', body.name.lower())[:40].strip('_')
    code = f"draft_{slug}_{int(time.time()) % 100000}"

    internal_desc = []
    if body.market:
        internal_desc.append(f"Market: {body.market}")
    if body.research_notes:
        internal_desc.append(body.research_notes)
    if body.notes:
        internal_desc.append(body.notes)

    item = FinishCatalogueItem(
        code=code,
        category=body.category,
        name=body.name,
        customer_name=None,
        customer_description=None,
        internal_description="\n".join(internal_desc) if internal_desc else None,
        supplier_name=body.supplier_name,
        manufacturer=body.manufacturer,
        supplier_url=body.supplier_url,
        specification_url=body.specification_url,
        datasheet_url=None,
        specification_url_public=False,
        image_url=body.image_url,
        image_alt_text=None,
        image_source_type="supplier_reference" if body.image_url else "none",
        image_approval_status="needs_approval" if body.image_url else "missing",
        unit=body.unit,
        unit_cost=body.unit_cost,
        currency=body.currency,
        price_type="allowance",
        default_quantity=1.0,
        quantity_rule=body.quantity_rule,
        included_by_default=False,
        customer_visible=False,
        internal_only=True,
        is_active=False,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{item_id}/approve", response_model=CatalogueItemOut)
def approve_draft(item_id: int, db: Db):
    """
    Mark a draft candidate as active + customer-visible.
    Does NOT change image_approval_status — images must be reviewed separately.
    Sets internal_only = False, is_active = True, customer_visible = True.
    The admin must separately verify image approval before the image will show in PDFs.
    """
    item = db.get(FinishCatalogueItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Catalogue item not found.")
    item.is_active = True
    item.customer_visible = True
    item.internal_only = False
    # Deliberately do NOT touch image_approval_status — must be reviewed manually
    db.commit()
    db.refresh(item)
    return item
