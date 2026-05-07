"""
API: Account settings — markup, VAT, rounding.

GET  /settings        — return current settings (creates defaults if none)
PUT  /settings        — update settings, returns updated record
"""
import math
from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import AccountSettings

Db = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsOut(BaseModel):
    id: int
    default_markup_percent: float
    currency: str
    vat_rate_percent: float
    vat_mode: str
    round_to_nearest: int

    model_config = {"from_attributes": True}


class SettingsIn(BaseModel):
    default_markup_percent: float = Field(ge=0, le=500)
    currency: str = "EUR"
    vat_rate_percent: float = Field(ge=0, le=100)
    vat_mode: str = "excluded"
    round_to_nearest: int = Field(ge=0)


def _get_or_create(db) -> AccountSettings:
    s = db.query(AccountSettings).first()
    if s is None:
        s = AccountSettings(
            default_markup_percent=50.0,
            currency="EUR",
            vat_rate_percent=21.0,
            vat_mode="excluded",
            round_to_nearest=100,
        )
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


@router.get("", response_model=SettingsOut)
def get_settings(db: Db):
    return _get_or_create(db)


@router.put("", response_model=SettingsOut)
def update_settings(body: SettingsIn, db: Db):
    s = _get_or_create(db)
    s.default_markup_percent = body.default_markup_percent
    s.currency = body.currency
    s.vat_rate_percent = body.vat_rate_percent
    s.vat_mode = body.vat_mode
    s.round_to_nearest = body.round_to_nearest
    db.commit()
    db.refresh(s)
    return s


# ── Pure pricing helpers (used by BOM endpoint + PDF) ────────────────────────

def compute_selling_price(
    internal_cost: float,
    markup_percent: float,
    vat_rate_percent: float,
    round_to_nearest: int = 0,
) -> dict:
    """
    Returns a dict with all selling price fields.
    """
    markup_amount    = round(internal_cost * markup_percent / 100, 2)
    selling_ex_vat   = round(internal_cost + markup_amount, 2)
    vat_amount       = round(selling_ex_vat * vat_rate_percent / 100, 2)
    selling_inc_vat  = round(selling_ex_vat + vat_amount, 2)

    if round_to_nearest and round_to_nearest > 0:
        rounded = math.ceil(selling_inc_vat / round_to_nearest) * round_to_nearest
    else:
        rounded = selling_inc_vat

    return {
        "internal_cost":    round(internal_cost, 2),
        "markup_percent":   markup_percent,
        "markup_amount":    markup_amount,
        "selling_ex_vat":   selling_ex_vat,
        "vat_rate_percent": vat_rate_percent,
        "vat_amount":       vat_amount,
        "selling_inc_vat":  selling_inc_vat,
        "rounded_price":    rounded,
    }
