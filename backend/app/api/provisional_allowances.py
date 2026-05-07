"""
API: Provisional Allowances

GET  /provisional-allowances          list all (sorted by sort_order)
PUT  /provisional-allowances/{id}     update rate, default_quantity, is_included_by_default
"""
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ProvisionalAllowance

router = APIRouter(tags=["provisional-allowances"])

Db = Annotated[Session, Depends(get_db)]


class AllowanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    category: str
    unit: str
    default_unit_rate: float
    currency: str
    quantity_source: str
    default_quantity: float
    is_included_by_default: bool
    is_client_discretion: bool
    cost_phase: str
    notes: Optional[str]
    sort_order: int
    updated_at: datetime


class AllowanceUpdate(BaseModel):
    default_unit_rate: Optional[float] = Field(default=None, gt=0)
    default_quantity: Optional[float] = Field(default=None, ge=0)
    is_included_by_default: Optional[bool] = None


@router.get("/provisional-allowances", response_model=list[AllowanceOut])
def list_allowances(db: Db):
    return (
        db.query(ProvisionalAllowance)
        .order_by(ProvisionalAllowance.sort_order, ProvisionalAllowance.id)
        .all()
    )


@router.put("/provisional-allowances/{allowance_id}", response_model=AllowanceOut)
def update_allowance(allowance_id: int, body: AllowanceUpdate, db: Db):
    pa = db.get(ProvisionalAllowance, allowance_id)
    if pa is None:
        raise HTTPException(status_code=404, detail="Provisional allowance not found.")
    if body.default_unit_rate is not None:
        pa.default_unit_rate = body.default_unit_rate
    if body.default_quantity is not None:
        pa.default_quantity = body.default_quantity
    if body.is_included_by_default is not None:
        pa.is_included_by_default = body.is_included_by_default
    db.commit()
    db.refresh(pa)
    return pa
