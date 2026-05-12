"""
API: Supplier Directory

GET    /suppliers                list (active only by default; ?include_archived=true for all)
POST   /suppliers                create (201)
GET    /suppliers/{id}           get
PUT    /suppliers/{id}           update
PATCH  /suppliers/{id}/archive   deactivate
PATCH  /suppliers/{id}/reactivate reactivate
DELETE /suppliers/{id}           hard delete (only if no linked materials — placeholder for now)
POST   /suppliers/import         bulk import from JSON rows (parsed from CSV/XLSX in browser)
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Supplier

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

Db = Annotated[Session, Depends(get_db)]

CATEGORIES = [
    "insulation", "structural_timber", "board_sheet", "cladding", "roofing",
    "membrane_vcl", "fixings_fasteners", "glazing_windows", "doors",
    "electrical", "plumbing", "finishes_flooring", "furniture_fittings",
    "tools_plant", "other",
]


# ── Schemas ───────────────────────────────────────────────────────────────────

class SupplierIn(BaseModel):
    name: str
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    category: str | None = None
    lead_time_days: int | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    currency: str = "EUR"
    notes: str | None = None


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    contact_name: str | None
    email: str | None
    phone: str | None
    website: str | None
    address: str | None
    category: str | None
    lead_time_days: int | None
    payment_terms: str | None
    delivery_terms: str | None
    currency: str
    notes: str | None
    is_active: bool


class ImportRowIn(BaseModel):
    name: str
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    category: str | None = None
    lead_time_days: int | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    currency: str = "EUR"
    notes: str | None = None
    is_active: bool = True


class ImportResultOut(BaseModel):
    created: int
    skipped_duplicates: int
    errors: list[str]
    suppliers: list[SupplierOut]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[SupplierOut])
def list_suppliers(db: Db, include_archived: bool = False):
    q = db.query(Supplier)
    if not include_archived:
        q = q.filter(Supplier.is_active == True)
    return q.order_by(Supplier.name).all()


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(body: SupplierIn, db: Db):
    supplier = Supplier(**body.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: uuid.UUID, db: Db):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(404, "Supplier not found")
    return s


@router.put("/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: uuid.UUID, body: SupplierIn, db: Db):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(404, "Supplier not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s


@router.patch("/{supplier_id}/archive", response_model=SupplierOut)
def archive_supplier(supplier_id: uuid.UUID, db: Db):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(404, "Supplier not found")
    s.is_active = False
    db.commit()
    db.refresh(s)
    return s


@router.patch("/{supplier_id}/reactivate", response_model=SupplierOut)
def reactivate_supplier(supplier_id: uuid.UUID, db: Db):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(404, "Supplier not found")
    s.is_active = True
    db.commit()
    db.refresh(s)
    return s


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: uuid.UUID, db: Db):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(404, "Supplier not found")
    db.delete(s)
    db.commit()
    return Response(status_code=204)


@router.post("/import", response_model=ImportResultOut, status_code=201)
def import_suppliers(rows: list[ImportRowIn], db: Db):
    created = []
    skipped = 0
    errors = []

    for i, row in enumerate(rows):
        if not row.name or not row.name.strip():
            errors.append(f"Row {i + 1}: name is required")
            continue

        # Duplicate detection by name (case-insensitive) or email
        existing = db.query(Supplier).filter(
            (Supplier.name.ilike(row.name.strip())) |
            (row.email is not None and Supplier.email == row.email)
        ).first()

        if existing:
            skipped += 1
            continue

        supplier = Supplier(**row.model_dump())
        db.add(supplier)
        try:
            db.flush()
            created.append(supplier)
        except Exception as e:
            db.rollback()
            errors.append(f"Row {i + 1} ({row.name}): {str(e)}")

    db.commit()
    for s in created:
        db.refresh(s)

    return ImportResultOut(
        created=len(created),
        skipped_duplicates=skipped,
        errors=errors,
        suppliers=created,
    )
