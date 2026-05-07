"""
API: Material Prices

GET    /materials/{id}/prices              list all prices for a material
POST   /materials/{id}/prices              add a price record
PUT    /material-prices/{price_id}         update a price record
DELETE /material-prices/{price_id}         remove a price record
POST   /material-prices/{price_id}/set-default  make this the default price

Rules:
- Multiple prices per material (retail, trade, import benchmark, etc.)
- One default per material — enforced at application layer
- Missing prices must NOT break BOM — prices are purely informational
- price_type must be one of the defined enum values
- unit must be one of: m2, lm, m3, pcs
"""
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import MaterialLibrary, MaterialPrice

router = APIRouter(tags=["material-prices"])

Db = Annotated[Session, Depends(get_db)]

VALID_PRICE_TYPES = {
    "retail_lv",
    "trade_lv",
    "manufacturer_direct",
    "import_benchmark",
    "manual_override",
}

VALID_UNITS = {"m2", "lm", "m3", "pcs"}


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class PriceIn(BaseModel):
    price_type: str = Field(..., description="retail_lv | trade_lv | manufacturer_direct | import_benchmark | manual_override")
    price_per_unit: float = Field(..., gt=0)
    unit: str = Field(..., description="m2 | lm | m3 | pcs")
    currency: str = Field(default="EUR", max_length=3)
    supplier_ref: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    notes: Optional[str] = None
    is_default: bool = False


class PriceUpdate(BaseModel):
    price_type: Optional[str] = None
    price_per_unit: Optional[float] = Field(default=None, gt=0)
    unit: Optional[str] = None
    currency: Optional[str] = Field(default=None, max_length=3)
    supplier_ref: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    notes: Optional[str] = None
    is_default: Optional[bool] = None


class PriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    material_id: int
    price_type: str
    price_per_unit: float
    unit: str
    currency: str
    supplier_ref: Optional[str]
    valid_from: Optional[datetime]
    valid_to: Optional[datetime]
    notes: Optional[str]
    is_default: bool
    created_at: datetime
    updated_at: datetime


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_price_type(price_type: str) -> None:
    if price_type not in VALID_PRICE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"price_type must be one of: {', '.join(sorted(VALID_PRICE_TYPES))}",
        )


def _validate_unit(unit: str) -> None:
    if unit not in VALID_UNITS:
        raise HTTPException(
            status_code=422,
            detail=f"unit must be one of: {', '.join(sorted(VALID_UNITS))}",
        )


def _clear_defaults(material_id: int, db: Session) -> None:
    """Clear is_default on all prices for this material."""
    db.query(MaterialPrice).filter(
        MaterialPrice.material_id == material_id,
        MaterialPrice.is_default.is_(True),
    ).update({"is_default": False})


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/materials/{material_id}/prices", response_model=list[PriceOut])
def list_prices(material_id: int, db: Db):
    mat = db.get(MaterialLibrary, material_id)
    if mat is None:
        raise HTTPException(status_code=404, detail="Material not found")
    return db.query(MaterialPrice).filter(MaterialPrice.material_id == material_id).all()


@router.post("/materials/{material_id}/prices", response_model=PriceOut, status_code=201)
def add_price(material_id: int, body: PriceIn, db: Db):
    mat = db.get(MaterialLibrary, material_id)
    if mat is None:
        raise HTTPException(status_code=404, detail="Material not found")

    _validate_price_type(body.price_type)
    _validate_unit(body.unit)

    if body.is_default:
        _clear_defaults(material_id, db)

    price = MaterialPrice(
        material_id=material_id,
        price_type=body.price_type,
        price_per_unit=body.price_per_unit,
        unit=body.unit,
        currency=body.currency,
        supplier_ref=body.supplier_ref,
        valid_from=body.valid_from,
        valid_to=body.valid_to,
        notes=body.notes,
        is_default=body.is_default,
    )
    db.add(price)
    db.commit()
    db.refresh(price)
    return price


@router.put("/material-prices/{price_id}", response_model=PriceOut)
def update_price(price_id: int, body: PriceUpdate, db: Db):
    price = db.get(MaterialPrice, price_id)
    if price is None:
        raise HTTPException(status_code=404, detail="Price record not found")

    if body.price_type is not None:
        _validate_price_type(body.price_type)
        price.price_type = body.price_type

    if body.price_per_unit is not None:
        price.price_per_unit = body.price_per_unit

    if body.unit is not None:
        _validate_unit(body.unit)
        price.unit = body.unit

    if body.currency is not None:
        price.currency = body.currency

    if body.supplier_ref is not None:
        price.supplier_ref = body.supplier_ref

    if body.valid_from is not None:
        price.valid_from = body.valid_from

    if body.valid_to is not None:
        price.valid_to = body.valid_to

    if body.notes is not None:
        price.notes = body.notes

    if body.is_default is not None:
        if body.is_default:
            _clear_defaults(price.material_id, db)
        price.is_default = body.is_default

    db.commit()
    db.refresh(price)
    return price


@router.delete("/material-prices/{price_id}", status_code=204)
def delete_price(price_id: int, db: Db):
    price = db.get(MaterialPrice, price_id)
    if price is None:
        raise HTTPException(status_code=404, detail="Price record not found")
    db.delete(price)
    db.commit()


@router.post("/material-prices/{price_id}/set-default", response_model=PriceOut)
def set_default_price(price_id: int, db: Db):
    price = db.get(MaterialPrice, price_id)
    if price is None:
        raise HTTPException(status_code=404, detail="Price record not found")

    _clear_defaults(price.material_id, db)
    price.is_default = True
    db.commit()
    db.refresh(price)
    return price
