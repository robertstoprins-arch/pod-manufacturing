"""
API: Finish Packages

GET  /finish-packages                   list packages (filterable)
GET  /finish-packages/categories        distinct category values
GET  /finish-packages/{id}              single package with full item list
GET  /finish-packages/{id}/items        item list for a package
POST /finish-packages                   create package (no items)
PUT  /finish-packages/{id}              update package header fields
DELETE /finish-packages/{id}            soft-delete (is_active=False)

POST /finish-packages/{id}/items        add item to package
PUT  /finish-packages/{id}/items/{item_id}    update line item
DELETE /finish-packages/{id}/items/{item_id}  remove line item

GET  /finish-packages/customer          customer-safe list (filters internal, enforces image gate)
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import FinishPackage, FinishPackageItem, FinishCatalogueItem
from app.api.finish_catalogue import CUSTOMER_SAFE_IMAGE_STATUSES

Db = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/finish-packages", tags=["finish-packages"])

VALID_PACKAGE_CATEGORIES = {
    "office", "guest_sleep", "studio_living", "bathroom",
    "external_finish", "internal_finish", "furniture", "lighting",
    "solar", "cctv", "custom",
}


# ── Schemas ────────────────────────────────────────────────────────────────────

class PackageItemOut(BaseModel):
    id: int
    finish_catalogue_item_id: int
    catalogue_code: str
    catalogue_name: str
    customer_name: Optional[str]
    category: str
    unit: Optional[str]
    unit_cost: Optional[float]
    currency: Optional[str]
    quantity: float
    quantity_override: Optional[float]
    effective_quantity: float           # quantity_override ?? quantity
    quantity_rule: Optional[str]
    is_required: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


class PackageOut(BaseModel):
    id: int
    code: str
    name: str
    customer_name: Optional[str]
    customer_description: Optional[str]
    internal_description: Optional[str]
    pod_type: Optional[str]
    package_category: str
    image_url: Optional[str]
    image_approval_status: str
    default_selected: bool
    customer_visible: bool
    is_active: bool
    sort_order: int
    items: list[PackageItemOut] = []

    model_config = {"from_attributes": True}


class PackageCustomerOut(BaseModel):
    """Customer-safe package — no internal_description, image gated."""
    id: int
    code: str
    package_category: str
    customer_name: Optional[str]
    customer_description: Optional[str]
    image_url: Optional[str]
    pod_type: Optional[str]
    default_selected: bool
    sort_order: int
    items: list[PackageItemOut] = []

    model_config = {"from_attributes": True}


class PackageIn(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    customer_name: Optional[str] = None
    customer_description: Optional[str] = None
    internal_description: Optional[str] = None
    pod_type: Optional[str] = None
    package_category: str
    image_url: Optional[str] = None
    image_approval_status: str = "missing"
    default_selected: bool = False
    customer_visible: bool = True
    is_active: bool = True
    sort_order: int = 0


class PackageItemIn(BaseModel):
    finish_catalogue_item_id: int
    quantity: float = Field(default=1.0, gt=0)
    quantity_override: Optional[float] = None
    is_required: bool = True
    notes: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_package(pkg_id: int, db: Session) -> FinishPackage:
    pkg = (
        db.query(FinishPackage)
        .options(
            joinedload(FinishPackage.items)
            .joinedload(FinishPackageItem.catalogue_item)
        )
        .filter(FinishPackage.id == pkg_id)
        .first()
    )
    if pkg is None:
        raise HTTPException(404, "Package not found.")
    return pkg


def _item_to_out(pi: FinishPackageItem) -> PackageItemOut:
    ci = pi.catalogue_item
    eff_qty = pi.quantity_override if pi.quantity_override is not None else pi.quantity
    return PackageItemOut(
        id=pi.id,
        finish_catalogue_item_id=ci.id,
        catalogue_code=ci.code,
        catalogue_name=ci.name,
        customer_name=ci.customer_name,
        category=ci.category,
        unit=ci.unit,
        unit_cost=ci.unit_cost,
        currency=ci.currency,
        quantity=pi.quantity,
        quantity_override=pi.quantity_override,
        effective_quantity=eff_qty,
        quantity_rule=ci.quantity_rule,
        is_required=pi.is_required,
        notes=pi.notes,
    )


def _pkg_to_out(pkg: FinishPackage) -> PackageOut:
    return PackageOut(
        id=pkg.id,
        code=pkg.code,
        name=pkg.name,
        customer_name=pkg.customer_name,
        customer_description=pkg.customer_description,
        internal_description=pkg.internal_description,
        pod_type=pkg.pod_type,
        package_category=pkg.package_category,
        image_url=pkg.image_url,
        image_approval_status=pkg.image_approval_status,
        default_selected=pkg.default_selected,
        customer_visible=pkg.customer_visible,
        is_active=pkg.is_active,
        sort_order=pkg.sort_order,
        items=[_item_to_out(pi) for pi in pkg.items],
    )


def _pkg_to_customer_out(pkg: FinishPackage) -> PackageCustomerOut:
    safe_img = (
        pkg.image_url
        if pkg.image_approval_status in CUSTOMER_SAFE_IMAGE_STATUSES
        else None
    )
    return PackageCustomerOut(
        id=pkg.id,
        code=pkg.code,
        package_category=pkg.package_category,
        customer_name=pkg.customer_name or pkg.name,
        customer_description=pkg.customer_description,
        image_url=safe_img,
        pod_type=pkg.pod_type,
        default_selected=pkg.default_selected,
        sort_order=pkg.sort_order,
        items=[_item_to_out(pi) for pi in pkg.items],
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/categories")
def list_categories(db: Db):
    rows = (
        db.query(FinishPackage.package_category)
        .filter(FinishPackage.is_active == True)
        .distinct()
        .order_by(FinishPackage.package_category)
        .all()
    )
    return [r[0] for r in rows]


@router.get("/customer", response_model=list[PackageCustomerOut])
def list_customer_packages(
    db: Db,
    category: Optional[str] = Query(None),
    pod_type: Optional[str] = Query(None),
):
    """
    Customer-facing list. Returns only active, customer_visible packages.
    Image URL gated by image_approval_status.
    """
    q = (
        db.query(FinishPackage)
        .options(
            joinedload(FinishPackage.items)
            .joinedload(FinishPackageItem.catalogue_item)
        )
        .filter(
            FinishPackage.is_active == True,
            FinishPackage.customer_visible == True,
        )
        .order_by(FinishPackage.sort_order, FinishPackage.id)
    )
    if category:
        q = q.filter(FinishPackage.package_category == category)
    if pod_type:
        q = q.filter(
            (FinishPackage.pod_type == pod_type) | (FinishPackage.pod_type == None)
        )
    return [_pkg_to_customer_out(p) for p in q.all()]


@router.get("", response_model=list[PackageOut])
def list_packages(
    db: Db,
    category: Optional[str] = Query(None),
    pod_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    customer_visible: Optional[bool] = Query(None),
):
    q = (
        db.query(FinishPackage)
        .options(
            joinedload(FinishPackage.items)
            .joinedload(FinishPackageItem.catalogue_item)
        )
        .order_by(FinishPackage.sort_order, FinishPackage.id)
    )
    if is_active is not None:
        q = q.filter(FinishPackage.is_active == is_active)
    if category:
        q = q.filter(FinishPackage.package_category == category)
    if pod_type:
        q = q.filter(
            (FinishPackage.pod_type == pod_type) | (FinishPackage.pod_type == None)
        )
    if customer_visible is not None:
        q = q.filter(FinishPackage.customer_visible == customer_visible)
    return [_pkg_to_out(p) for p in q.all()]


@router.get("/{pkg_id}", response_model=PackageOut)
def get_package(pkg_id: int, db: Db):
    return _pkg_to_out(_load_package(pkg_id, db))


@router.get("/{pkg_id}/items", response_model=list[PackageItemOut])
def get_package_items(pkg_id: int, db: Db):
    pkg = _load_package(pkg_id, db)
    return [_item_to_out(pi) for pi in pkg.items]


@router.post("", response_model=PackageOut, status_code=201)
def create_package(body: PackageIn, db: Db):
    if body.package_category not in VALID_PACKAGE_CATEGORIES:
        raise HTTPException(400, f"Invalid package_category '{body.package_category}'.")
    if db.query(FinishPackage).filter_by(code=body.code).first():
        raise HTTPException(400, f"A package with code '{body.code}' already exists.")
    pkg = FinishPackage(**body.model_dump())
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return _pkg_to_out(_load_package(pkg.id, db))


@router.put("/{pkg_id}", response_model=PackageOut)
def update_package(pkg_id: int, body: PackageIn, db: Db):
    pkg = db.get(FinishPackage, pkg_id)
    if pkg is None:
        raise HTTPException(404, "Package not found.")
    if body.package_category not in VALID_PACKAGE_CATEGORIES:
        raise HTTPException(400, f"Invalid package_category '{body.package_category}'.")
    if body.code != pkg.code:
        if db.query(FinishPackage).filter_by(code=body.code).first():
            raise HTTPException(400, f"A package with code '{body.code}' already exists.")
    for field, value in body.model_dump().items():
        setattr(pkg, field, value)
    db.commit()
    return _pkg_to_out(_load_package(pkg_id, db))


@router.delete("/{pkg_id}", status_code=204)
def deactivate_package(pkg_id: int, db: Db):
    pkg = db.get(FinishPackage, pkg_id)
    if pkg is None:
        raise HTTPException(404, "Package not found.")
    pkg.is_active = False
    db.commit()


# ── Package item management ────────────────────────────────────────────────────

@router.post("/{pkg_id}/items", response_model=PackageItemOut, status_code=201)
def add_item(pkg_id: int, body: PackageItemIn, db: Db):
    pkg = db.get(FinishPackage, pkg_id)
    if pkg is None:
        raise HTTPException(404, "Package not found.")
    cat = db.get(FinishCatalogueItem, body.finish_catalogue_item_id)
    if cat is None:
        raise HTTPException(404, f"Catalogue item {body.finish_catalogue_item_id} not found.")
    pi = FinishPackageItem(finish_package_id=pkg_id, **body.model_dump())
    db.add(pi)
    db.commit()
    db.refresh(pi)
    # re-load with relationship
    pi = db.query(FinishPackageItem).options(
        joinedload(FinishPackageItem.catalogue_item)
    ).filter(FinishPackageItem.id == pi.id).first()
    return _item_to_out(pi)


@router.put("/{pkg_id}/items/{item_id}", response_model=PackageItemOut)
def update_item(pkg_id: int, item_id: int, body: PackageItemIn, db: Db):
    pi = db.query(FinishPackageItem).filter_by(id=item_id, finish_package_id=pkg_id).first()
    if pi is None:
        raise HTTPException(404, "Package line item not found.")
    cat = db.get(FinishCatalogueItem, body.finish_catalogue_item_id)
    if cat is None:
        raise HTTPException(404, f"Catalogue item {body.finish_catalogue_item_id} not found.")
    for field, value in body.model_dump().items():
        setattr(pi, field, value)
    db.commit()
    pi = db.query(FinishPackageItem).options(
        joinedload(FinishPackageItem.catalogue_item)
    ).filter(FinishPackageItem.id == item_id).first()
    return _item_to_out(pi)


@router.delete("/{pkg_id}/items/{item_id}", status_code=204)
def remove_item(pkg_id: int, item_id: int, db: Db):
    pi = db.query(FinishPackageItem).filter_by(id=item_id, finish_package_id=pkg_id).first()
    if pi is None:
        raise HTTPException(404, "Package line item not found.")
    db.delete(pi)
    db.commit()
