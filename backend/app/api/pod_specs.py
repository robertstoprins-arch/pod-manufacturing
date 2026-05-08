"""
API: Pod Specs — pod geometry linked to build-up assignments

GET    /pod-specs              list all
POST   /pod-specs              create
GET    /pod-specs/{id}         retrieve
PUT    /pod-specs/{id}         update
DELETE /pod-specs/{id}         delete (204)
GET    /pod-specs/{id}/bom     compute material schedule from geometry + assigned build-ups
"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict

from app.db import get_db
from app.models import BuildUp, BuildUpLayer, MaterialLibrary, MaterialPrice, PodSpec, ProvisionalAllowance
from app.skills.element_decomposer import OpeningSpec, decompose_pod
from app.skills.mto_resolver import MtoInputLayer, WallGeometry, resolve_mto
from sqlalchemy.orm import Session

router = APIRouter(tags=["pod-specs"])

Db = Annotated[Session, Depends(get_db)]


# ── Pydantic models ───────────────────────────────────────────────────────────

class FinishItemSelection(BaseModel):
    item_id: int
    quantity: float = 1.0
    unit_cost_override: float | None = None
    included: bool = True


class FinishPackageSelection(BaseModel):
    package_id: int
    quantity: float = 1.0


class FinishSelections(BaseModel):
    packages: list[FinishPackageSelection] = []
    items: list[FinishItemSelection] = []


class PodSpecIn(BaseModel):
    name: str
    geometry: dict
    wall_build_up_id: int | None = None
    floor_build_up_id: int | None = None
    roof_build_up_id: int | None = None
    status: str = "draft"
    client_project_id: str | None = None
    selected_finishes: FinishSelections | None = None


class BuildUpRef(BaseModel):
    id: int
    name: str
    element_type: str | None
    build_up_type: str | None
    status: str | None

    model_config = ConfigDict(from_attributes=True)


class PodSpecOut(BaseModel):
    id: int
    name: str
    geometry: dict
    wall_build_up_id: int | None
    floor_build_up_id: int | None
    roof_build_up_id: int | None
    status: str | None
    client_project_id: str | None = None
    selected_finishes: FinishSelections | None = None
    created_at: datetime | None
    updated_at: datetime | None
    wall_build_up: BuildUpRef | None = None
    floor_build_up: BuildUpRef | None = None
    roof_build_up: BuildUpRef | None = None

    model_config = ConfigDict(from_attributes=True)


class BomLineOut(BaseModel):
    element_type: str
    build_up_name: str
    position_order: int
    material_name: str
    supplier_ref: str
    role: str
    method: str
    thickness_mm: float
    raw_quantity: float
    waste_factor: float
    order_quantity: float
    area_m2: float            # kept for UI compatibility — equals raw_quantity
    unit: str
    notes: str = ""
    price_per_unit: float | None = None
    currency: str | None = None
    line_cost: float | None = None  # order_quantity × price_per_unit


class BomOut(BaseModel):
    spec_id: int
    spec_name: str
    areas: dict[str, float]          # ExternalWall, Floor, Roof
    opening_counts: dict[str, int]   # { "window": 2, "door": 1, "rooflights": 0 }
    lines: list[BomLineOut]
    total_cost: float | None = None  # sum of all line_costs where price available
    currency: str | None = None      # currency of the total (None if mixed)
    warnings: list[str] = []         # data quality and pricing warnings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _price_for_unit(material_id: int, unit: str, db: Session) -> MaterialPrice | None:
    """Return the best price for a material+unit combo.

    Priority: (1) unit-matched default, (2) any unit-matched price,
    (3) overall default, (4) any price.
    This handles framing_zone which produces both an lm line and an m2 line
    from the same material record.
    """
    prices = (
        db.query(MaterialPrice)
        .filter(MaterialPrice.material_id == material_id)
        .all()
    )
    if not prices:
        return None
    unit_match = [p for p in prices if p.unit == unit]
    if unit_match:
        default = next((p for p in unit_match if p.is_default), None)
        return default or unit_match[0]
    # No unit match — fall back to overall default
    default = next((p for p in prices if p.is_default), None)
    return default or prices[0]


def _to_out(spec: PodSpec) -> PodSpecOut:
    out = PodSpecOut.model_validate(spec)
    if spec.selected_finishes_json:
        try:
            out.selected_finishes = FinishSelections.model_validate(spec.selected_finishes_json)
        except Exception:
            pass
    return out


def _decompose_geometry(geom: dict):
    """Run element decomposer. Returns (areas_by_type, all_elements)."""
    openings_raw = geom.get("openings", [])
    openings = []
    for o in openings_raw:
        x_off = o.get("x_offset_m")
        openings.append(OpeningSpec(
            wall=o["wall"],
            type=o["type"],
            width_m=float(o["width_m"]),
            height_m=float(o["height_m"]) if o.get("shape") != "circular" else float(o["width_m"]),
            sill_height_m=float(o.get("sill_height_m", 0.0)),
            x_offset_m=None if (x_off is None or x_off == "") else float(x_off),
            shape=o.get("shape", "rectangular"),
        ))

    elements = decompose_pod(
        width_m=float(geom["width_m"]),
        length_m=float(geom["length_m"]),
        wall_height_m=float(geom["wall_height_m"]),
        roof_type=geom.get("roof_type", "duo_pitch"),
        roof_pitch_deg=float(geom.get("roof_pitch_deg", 15.0)),
        openings=openings,
    )

    areas: dict[str, float] = {"ExternalWall": 0.0, "Floor": 0.0, "Roof": 0.0}
    for el in elements:
        if el.type == "ExternalWall":
            areas["ExternalWall"] += el.area_net_m2
        elif el.type == "Floor":
            areas["Floor"] = el.area_net_m2
        elif el.type == "Roof":
            areas["Roof"] = el.area_gross_m2   # gross — rooflights don't reduce insulation run
    return areas, elements


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/pod-specs", response_model=list[PodSpecOut])
def list_pod_specs(db: Db):
    return db.query(PodSpec).order_by(PodSpec.id).all()


@router.post("/pod-specs", response_model=PodSpecOut, status_code=201)
def create_pod_spec(body: PodSpecIn, db: Db):
    spec = PodSpec(
        name=body.name,
        geometry=body.geometry,
        wall_build_up_id=body.wall_build_up_id,
        floor_build_up_id=body.floor_build_up_id,
        roof_build_up_id=body.roof_build_up_id,
        status=body.status,
        client_project_id=body.client_project_id,
        selected_finishes_json=body.selected_finishes.model_dump() if body.selected_finishes else None,
    )
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return _to_out(spec)


@router.get("/pod-specs/{spec_id}", response_model=PodSpecOut)
def get_pod_spec(spec_id: int, db: Db):
    spec = db.get(PodSpec, spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Pod spec not found.")
    return _to_out(spec)


@router.put("/pod-specs/{spec_id}", response_model=PodSpecOut)
def update_pod_spec(spec_id: int, body: PodSpecIn, db: Db):
    spec = db.get(PodSpec, spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Pod spec not found.")
    spec.name = body.name
    spec.geometry = body.geometry
    spec.wall_build_up_id = body.wall_build_up_id
    spec.floor_build_up_id = body.floor_build_up_id
    spec.roof_build_up_id = body.roof_build_up_id
    spec.status = body.status
    spec.client_project_id = body.client_project_id
    spec.selected_finishes_json = body.selected_finishes.model_dump() if body.selected_finishes else None
    spec.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(spec)
    return _to_out(spec)


@router.patch("/pod-specs/{spec_id}/finishes", response_model=PodSpecOut)
def update_finish_selections(spec_id: int, body: FinishSelections, db: Db):
    """Lightweight endpoint: update only finish selections without touching geometry."""
    spec = db.get(PodSpec, spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Pod spec not found.")
    spec.selected_finishes_json = body.model_dump()
    spec.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(spec)
    return _to_out(spec)


@router.delete("/pod-specs/{spec_id}", status_code=204)
def delete_pod_spec(spec_id: int, db: Db):
    spec = db.get(PodSpec, spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Pod spec not found.")
    db.delete(spec)
    db.commit()


@router.get("/pod-specs/{spec_id}/finish-cost")
def get_finish_cost(spec_id: int, db: Db):
    """
    Resolve the pod spec's selected_finishes_json into a priced line list.

    Returns:
      { "lines": [...], "total": float | null, "currency": str | null }

    Each line:
      { "source": "package" | "item",
        "package_id": int | null,
        "package_name": str | null,
        "item_id": int,
        "code": str,
        "name": str,
        "category": str,
        "cost_group": str,   # mapped from category
        "quantity": float,
        "unit": str | null,
        "unit_cost": float | null,
        "currency": str | null,
        "line_cost": float | null,
        "quantity_rule": str | null,
        "is_required": bool }
    """
    from app.models import FinishPackage, FinishPackageItem, FinishCatalogueItem

    spec = db.get(PodSpec, spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Pod spec not found.")

    raw = spec.selected_finishes_json or {"packages": [], "items": []}

    # Map category → cost group label
    COST_GROUP = {
        "external_cladding":       "Finishes",
        "internal_paint":          "Finishes",
        "internal_timber_finish":  "Finishes",
        "flooring":                "Finishes",
        "sanitaryware":            "Sanitaryware",
        "toilet":                  "Sanitaryware",
        "vanity_unit":             "Sanitaryware",
        "kitchenette":             "Kitchenette",
        "furniture_set":           "Furniture / Client Discretion",
        "lighting":                "Lighting",
        "heating_visible":         "Heating + Ventilation",
        "ventilation_visible":     "Heating + Ventilation",
        "cctv_data":               "CCTV / Data",
        "solar_battery":           "Solar / Battery",
        "delivery_install":        "Delivery / Install",
        "other":                   "Other",
    }

    def _line(ci: FinishCatalogueItem, qty: float, unit_cost_override: float | None,
              included: bool, source: str,
              pkg_id: int | None = None, pkg_name: str | None = None,
              is_required: bool = True) -> dict:
        uc = unit_cost_override if unit_cost_override is not None else ci.unit_cost
        lc = round(uc * qty, 2) if uc is not None else None
        return {
            "source":               source,
            "package_id":           pkg_id,
            "package_name":         pkg_name,
            "item_id":              ci.id,
            "code":                 ci.code,
            "name":                 ci.customer_name or ci.name,
            "customer_description": ci.customer_description,
            "category":             ci.category,
            "cost_group":           COST_GROUP.get(ci.category, "Other"),
            "quantity":             qty,
            "unit":                 ci.unit,
            "unit_cost":            uc,
            "currency":             ci.currency,
            "line_cost":            lc,
            "quantity_rule":        ci.quantity_rule,
            "included":             included,
            "is_required":          is_required,
            # Public spec link — only included if explicitly marked public by admin
            "specification_url":    ci.specification_url if ci.specification_url_public else None,
        }

    lines = []
    seen_item_ids: set[int] = set()

    # 1. Expand selected packages
    for pkg_sel in raw.get("packages", []):
        pkg_id = pkg_sel.get("package_id")
        pkg_qty = float(pkg_sel.get("quantity", 1))
        pkg = (
            db.query(FinishPackage)
            .filter(FinishPackage.id == pkg_id, FinishPackage.is_active == True)
            .first()
        )
        if pkg is None:
            continue
        for pi in pkg.items:
            ci = pi.catalogue_item
            if not ci.is_active:
                continue
            eff_qty = (pi.quantity_override if pi.quantity_override is not None else pi.quantity) * pkg_qty
            lines.append(_line(ci, eff_qty, None, True, "package",
                               pkg_id=pkg.id, pkg_name=pkg.customer_name or pkg.name,
                               is_required=pi.is_required))
            seen_item_ids.add(ci.id)

    # 2. Explicit item overrides / additions
    for item_sel in raw.get("items", []):
        item_id = item_sel.get("item_id")
        qty     = float(item_sel.get("quantity", 1))
        override_cost = item_sel.get("unit_cost_override")
        included = item_sel.get("included", True)
        ci = db.query(FinishCatalogueItem).filter(
            FinishCatalogueItem.id == item_id,
            FinishCatalogueItem.is_active == True,
        ).first()
        if ci is None:
            continue
        lines.append(_line(ci, qty, override_cost, included, "item", is_required=False))

    priced = [l for l in lines if l["line_cost"] is not None and l["included"]]
    total   = round(sum(l["line_cost"] for l in priced), 2) if priced else None
    currencies = {l["currency"] for l in priced if l["currency"]}
    currency = currencies.pop() if len(currencies) == 1 else None

    return {"lines": lines, "total": total, "currency": currency}


@router.get("/pod-specs/{spec_id}/bom", response_model=BomOut)
def get_pod_spec_bom(spec_id: int, db: Db):
    spec = db.get(PodSpec, spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Pod spec not found.")

    areas, all_elements = _decompose_geometry(spec.geometry)
    opening_elements = [el for el in all_elements if el.type == "Opening"]

    assignments = {
        "ExternalWall": spec.wall_build_up_id,
        "Floor":        spec.floor_build_up_id,
        "Roof":         spec.roof_build_up_id,
    }

    # Pre-fetch materials used for framing zone sub-line pricing so we don't
    # do repeated per-layer DB round-trips for these fixed references.
    _framing_price_refs = {
        "GENERIC-C24-TIMBER",
        "GENERIC-MW-FRAMING-140",
        "GENERIC-PIR-FRAMING-140",
    }
    framing_ref_mats: dict[str, MaterialLibrary] = {
        m.supplier_ref: m
        for m in db.query(MaterialLibrary).filter(
            MaterialLibrary.supplier_ref.in_(_framing_price_refs)
        ).all()
    }

    lines: list[BomLineOut] = []
    bom_warnings: list[str] = []
    # Track which build-ups have already fired the Intello warning (once per BU).
    _intello_warned: set[int] = set()

    for element_type, bu_id in assignments.items():
        if bu_id is None:
            continue
        bu = db.get(BuildUp, bu_id)
        if bu is None:
            continue

        total_net   = round(areas.get(element_type, 0.0), 3)
        total_gross = round(sum(
            el.area_gross_m2 for el in all_elements if el.type == element_type
        ), 3)

        wall_geoms: list[WallGeometry] = []
        if element_type == "ExternalWall":
            for el in all_elements:
                if el.type != "ExternalWall":
                    continue
                face = el.geometry.get("face", "")
                oc = sum(1 for oel in opening_elements if oel.geometry.get("wall") == face)
                wall_geoms.append(WallGeometry(
                    label=el.label,
                    length_m=float(el.geometry.get("width_m", 0.0)),
                    height_m=float(el.geometry.get("height_m", 0.0)),
                    opening_count=oc,
                    gross_area_m2=el.area_gross_m2,
                    net_area_m2=el.area_net_m2,
                ))

        for layer in bu.layers:
            mat   = db.get(MaterialLibrary, layer.material_id)
            props = layer.properties or {}
            role  = props.get("role", "")
            ff    = float(props.get("framing_fraction", 0.15))

            # Warn once per build-up if a premium airtight membrane is used
            # in what looks like a standard or light specification.
            if (
                mat.supplier_ref == "PROCLIMA-INTELLO-PLUS"
                and bu.id not in _intello_warned
                and "enhanced" not in bu.name.lower()
                and "premium" not in bu.name.lower()
            ):
                _intello_warned.add(bu.id)
                bom_warnings.append(
                    f"Build-up '{bu.name}' uses Intello Plus (premium airtight membrane) — "
                    f"standard/light specifications should use a standard VCL."
                )

            mto_input = MtoInputLayer(
                name=mat.name,
                role=role,
                thickness_mm=layer.thickness_mm,
                framing_fraction=ff,
                supplier_ref=mat.supplier_ref or "",
                properties=props,
            )
            mto_lines = resolve_mto(
                [mto_input],
                element_type,
                wall_geoms,
                total_net_m2=total_net,
                total_gross_m2=total_gross,
            )

            # Thickness-based price scaling:
            #   EPS materials — prices stored per 100mm basis (ref encodes nominal
            #     thickness but basis is always 100mm by convention)
            #   GENERIC-PIR-OUTBOARD-50 only — used at variable thicknesses in some
            #     legacy build-ups; thickness-specific refs (PIR-OUTBOARD-100) are
            #     priced at their exact thickness and must NOT be scaled.
            price_basis_mm: float | None = None
            if "EPS" in (mat.supplier_ref or "").upper():
                price_basis_mm = 100.0
            elif mat.supplier_ref == "GENERIC-PIR-OUTBOARD-50":
                price_basis_mm = 50.0

            for mto in mto_lines:
                # Route framing-zone sub-lines to the correct pricing material:
                #   framing_zone_timber    → GENERIC-C24-TIMBER (lm)
                #   framing_zone_insulation → infill material ref from layer props (m2)
                # Without this routing both lines would fall back to the composite
                # zone price (e.g. EUR 22/m²) applied per lm — wrong by ~6×.
                price_mat = mat
                line_supplier_ref = mat.supplier_ref or ""
                apply_thickness_scaling = True

                if mto.role == "framing_zone_timber":
                    c24 = framing_ref_mats.get("GENERIC-C24-TIMBER")
                    if c24:
                        price_mat = c24
                        line_supplier_ref = c24.supplier_ref or ""
                        apply_thickness_scaling = False
                    else:
                        bom_warnings.append(
                            "GENERIC-C24-TIMBER not found in material library — "
                            "C24 framing line is priced from the composite zone rate (inflated)"
                        )

                elif mto.role == "framing_zone_insulation":
                    infill_ref = props.get("infill_material_ref", "")
                    if infill_ref:
                        infill_mat = framing_ref_mats.get(infill_ref)
                        if infill_mat is None:
                            # Not in pre-fetch set — try a direct lookup
                            infill_mat = db.query(MaterialLibrary).filter(
                                MaterialLibrary.supplier_ref == infill_ref
                            ).first()
                        if infill_mat:
                            price_mat = infill_mat
                            line_supplier_ref = infill_mat.supplier_ref or ""
                            apply_thickness_scaling = False
                        else:
                            bom_warnings.append(
                                f"Infill material '{infill_ref}' not in material library — "
                                "insulation infill line priced from composite zone rate (may be inflated)"
                            )
                    else:
                        # Framing zone has no infill_material_ref stored in layer properties.
                        # Warn so the build-up definition can be corrected.
                        bom_warnings.append(
                            f"Build-up '{bu.name}' framing zone layer has no "
                            "'infill_material_ref' in properties — insulation infill "
                            "priced from composite zone rate. Add infill_material_ref to fix."
                        )

                price_per_unit: float | None = None
                currency: str | None = None
                line_cost: float | None = None

                matched_price = _price_for_unit(price_mat.id, mto.unit, db)
                if matched_price is not None:
                    base_price = matched_price.price_per_unit
                    if (
                        apply_thickness_scaling
                        and price_basis_mm
                        and layer.thickness_mm
                        and layer.thickness_mm != price_basis_mm
                    ):
                        base_price = round(base_price * (layer.thickness_mm / price_basis_mm), 4)
                    price_per_unit = base_price
                    currency = matched_price.currency
                    line_cost = round(mto.order_quantity * price_per_unit, 2)
                else:
                    bom_warnings.append(
                        f"Missing price: {mto.material_name} "
                        f"({line_supplier_ref or 'no ref'}, unit: {mto.unit}) — line cost excluded"
                    )

                lines.append(BomLineOut(
                    element_type=element_type,
                    build_up_name=bu.name,
                    position_order=layer.position_order,
                    material_name=mto.material_name,
                    supplier_ref=line_supplier_ref,
                    role=mto.role,
                    method=mto.method,
                    thickness_mm=layer.thickness_mm,
                    raw_quantity=mto.raw_quantity,
                    waste_factor=mto.waste_factor,
                    order_quantity=mto.order_quantity,
                    area_m2=mto.raw_quantity,
                    unit=mto.unit,
                    notes=mto.notes,
                    price_per_unit=price_per_unit,
                    currency=currency,
                    line_cost=line_cost,
                ))

    # ── Opening counts (for BomOut summary field) ─────────────────────────────
    opening_counts: dict[str, int] = {}
    for o in spec.geometry.get("openings", []):
        otype = o.get("type", "other")
        opening_counts[otype] = opening_counts.get(otype, 0) + 1
    roof_opening_count = sum(
        1 for ro in spec.geometry.get("roof_openings", [])
        if ro.get("selected", False)
    )
    if roof_opening_count:
        opening_counts["rooflight"] = roof_opening_count

    # ── Per-opening BOM rows with tags, dimensions, wall/roof location ────────
    # Each opening gets its own row: W1, W2…, D1…, RL1…
    # Costs are provisional allowances from ProvisionalAllowance table.
    OPENING_CFG: dict[str, tuple[str, str, str, int]] = {
        # type: (tag_prefix, pa_code, element_type, position_order)
        "window":      ("W",  "ENV_WINDOW",    "ExternalWall", 999),
        "door":        ("D",  "ENV_EXT_DOOR",  "ExternalWall", 1000),
        "french_door": ("D",  "ENV_EXT_DOOR",  "ExternalWall", 1000),
        "vent":        ("V",  "ENV_WINDOW",    "ExternalWall", 999),
    }
    type_counters: dict[str, int] = {}

    # Cache PA lookups to avoid redundant queries
    pa_cache: dict[str, ProvisionalAllowance | None] = {}

    def _get_pa(code: str) -> ProvisionalAllowance | None:
        if code not in pa_cache:
            pa_cache[code] = db.query(ProvisionalAllowance).filter(
                ProvisionalAllowance.code == code
            ).first()
        return pa_cache[code]

    for o in spec.geometry.get("openings", []):
        otype = o.get("type", "window")
        prefix, pa_code, el_type, pos_order = OPENING_CFG.get(
            otype, ("X", "ENV_WINDOW", "ExternalWall", 999)
        )
        type_counters[prefix] = type_counters.get(prefix, 0) + 1
        tag = f"{prefix}{type_counters[prefix]}"

        wall_face = o.get("wall", "?")
        w_mm = round(float(o.get("width_m", 0)) * 1000)
        h_mm = round(float(o.get("height_m", 0)) * 1000)
        type_label = otype.replace("_", " ").title()
        supplier_ref_str = f"ALLOWANCE-{otype.upper().replace('_', '-')}-GENERIC"

        pa = _get_pa(pa_code)
        unit_rate = pa.default_unit_rate if pa else 0.0
        curr      = pa.currency if pa else "EUR"

        bom_warnings.append(
            f"{tag} ({type_label} {w_mm}×{h_mm}mm — Wall {wall_face}): "
            "cost is provisional allowance — replace with supplier quote"
        )
        lines.append(BomLineOut(
            element_type=el_type,
            build_up_name="Openings",
            position_order=pos_order,
            material_name=f"{tag} — {type_label} {w_mm}×{h_mm}mm — Wall {wall_face}",
            supplier_ref=supplier_ref_str,
            role="opening",
            method="each",
            thickness_mm=0.0,
            raw_quantity=1.0,
            waste_factor=1.0,
            order_quantity=1.0,
            area_m2=float(o.get("width_m", 0)) * float(o.get("height_m", 0)),
            unit="each",
            notes="Provisional allowance — replace with supplier quote.",
            price_per_unit=unit_rate,
            currency=curr,
            line_cost=round(unit_rate, 2),
        ))

    # Rooflight rows
    rl_counter = 0
    pa_rl   = _get_pa("ENV_ROOFLIGHT")
    rl_rate = pa_rl.default_unit_rate if pa_rl else 0.0
    rl_curr = pa_rl.currency if pa_rl else "EUR"
    for ro in spec.geometry.get("roof_openings", []):
        if not ro.get("selected", False):
            continue
        rl_counter += 1
        tag  = f"RL{rl_counter}"
        w_mm = round(float(ro.get("width_m", 0.6)) * 1000)
        h_mm = round(float(ro.get("height_m", 0.8)) * 1000)

        bom_warnings.append(
            f"{tag} (Rooflight {w_mm}×{h_mm}mm — Roof/Ceiling): "
            "cost is provisional allowance — verify rooflight appears in roof/ceiling drawing and opening schedule"
        )
        lines.append(BomLineOut(
            element_type="Roof",
            build_up_name="Openings",
            position_order=999,
            material_name=f"{tag} — Rooflight {w_mm}×{h_mm}mm — Roof/Ceiling",
            supplier_ref="ALLOWANCE-ROOFLIGHT-GENERIC",
            role="opening",
            method="each",
            thickness_mm=0.0,
            raw_quantity=1.0,
            waste_factor=1.0,
            order_quantity=1.0,
            area_m2=float(ro.get("width_m", 0.6)) * float(ro.get("height_m", 0.8)),
            unit="each",
            notes="Provisional allowance — verify rooflight appears in roof/ceiling drawing and opening schedule.",
            price_per_unit=rl_rate,
            currency=rl_curr,
            line_cost=round(rl_rate, 2),
        ))

    # ── Grand total ───────────────────────────────────────────────────────────
    priced = [l for l in lines if l.line_cost is not None]
    total_cost: float | None = None
    total_currency: str | None = None
    if priced:
        total_cost = round(sum(l.line_cost for l in priced), 2)
        currencies = {l.currency for l in priced}
        total_currency = currencies.pop() if len(currencies) == 1 else None

    return BomOut(
        spec_id=spec_id,
        spec_name=spec.name,
        areas={k: round(v, 3) for k, v in areas.items()},
        opening_counts=opening_counts,
        lines=lines,
        total_cost=total_cost,
        currency=total_currency,
        warnings=bom_warnings,
    )


# ── Review Pack PDF ───────────────────────────────────────────────────────────

class ReviewPackIn(BaseModel):
    project_name: str = ""
    revision: str = "A"
    packages: dict = {}
    pkg_overrides: dict = {}
    # Markup / selling price (optional — if not provided, loaded from AccountSettings)
    markup_percent: float | None = None
    vat_rate_percent: float | None = None
    round_to_nearest: int | None = None


@router.post("/pod-specs/{spec_id}/generate-review-pack")
def generate_review_pack(spec_id: int, body: ReviewPackIn, db: Db):
    spec = db.get(PodSpec, spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Pod spec not found.")

    from app.skills.pdf_review_pack import ReviewPackData, ReviewPackPDF, _resolve_buildup
    from app.models import MaterialLibrary, AccountSettings
    from app.api.settings import _get_or_create as _get_settings, compute_selling_price

    # Resolve build-ups
    wall_bu  = _resolve_buildup(db.get(BuildUp, spec.wall_build_up_id),  db) if spec.wall_build_up_id  else None
    floor_bu = _resolve_buildup(db.get(BuildUp, spec.floor_build_up_id), db) if spec.floor_build_up_id else None
    roof_bu  = _resolve_buildup(db.get(BuildUp, spec.roof_build_up_id),  db) if spec.roof_build_up_id  else None

    # BOM — reuse existing get_pod_spec_bom logic by calling it directly
    bom = get_pod_spec_bom(spec_id, db)
    bom_lines = [l.model_dump() for l in bom.lines]

    # Materials
    materials_orm = db.query(MaterialLibrary).order_by(MaterialLibrary.id).all()
    from app.api.build_ups import MaterialOut
    materials = [MaterialOut.model_validate(m).model_dump() for m in materials_orm]

    # Provisional allowances
    allowances_orm = db.query(ProvisionalAllowance).all()
    allowances = [
        {"code": a.code, "name": a.name, "default_unit_rate": a.default_unit_rate,
         "currency": a.currency, "phase": a.cost_phase}
        for a in allowances_orm
    ]

    # Load account settings for markup / selling price calculation
    acc = _get_settings(db)
    markup_pct = body.markup_percent if body.markup_percent is not None else acc.default_markup_percent
    vat_pct    = body.vat_rate_percent if body.vat_rate_percent is not None else acc.vat_rate_percent
    rtn        = body.round_to_nearest if body.round_to_nearest is not None else acc.round_to_nearest

    data = ReviewPackData(
        spec_id=spec_id,
        spec_name=spec.name,
        revision=body.revision or "A",
        project_name=body.project_name or spec.name,
        generated_at=datetime.now(timezone.utc),
        geometry=spec.geometry,
        wall_bu=wall_bu,
        floor_bu=floor_bu,
        roof_bu=roof_bu,
        bom_lines=bom_lines,
        bom_areas=bom.areas,
        bom_opening_counts=bom.opening_counts,
        bom_total=bom.total_cost,
        materials=materials,
        allowances=allowances,
        packages=body.packages,
        pkg_overrides=body.pkg_overrides,
        markup_percent=markup_pct,
        vat_rate_percent=vat_pct,
        round_to_nearest=rtn,
    )

    pdf_bytes = ReviewPackPDF(data).generate()
    filename = f"pod-internal-technical-pack-{spec.name.lower().replace(' ', '-')}-rev{body.revision}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Client Quote PDF ──────────────────────────────────────────────────────────

class ClientQuoteIn(BaseModel):
    project_name: str = ""
    revision: str = "A"
    packages: dict = {}
    pkg_overrides: dict = {}
    customer_name: str = ""
    markup_percent: float | None = None
    vat_rate_percent: float | None = None
    round_to_nearest: int | None = None


@router.post("/pod-specs/{spec_id}/generate-client-quote")
def generate_client_quote(spec_id: int, body: ClientQuoteIn, db: Db):
    spec = db.get(PodSpec, spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Pod spec not found.")

    from app.skills.pdf_review_pack import ReviewPackData, _resolve_buildup
    from app.skills.pdf_client_quote import ClientQuotePDF
    from app.models import MaterialLibrary, AccountSettings
    from app.api.settings import _get_or_create as _get_settings

    wall_bu  = _resolve_buildup(db.get(BuildUp, spec.wall_build_up_id),  db) if spec.wall_build_up_id  else None
    floor_bu = _resolve_buildup(db.get(BuildUp, spec.floor_build_up_id), db) if spec.floor_build_up_id else None
    roof_bu  = _resolve_buildup(db.get(BuildUp, spec.roof_build_up_id),  db) if spec.roof_build_up_id  else None

    bom = get_pod_spec_bom(spec_id, db)

    acc = _get_settings(db)
    markup_pct = body.markup_percent if body.markup_percent is not None else acc.default_markup_percent
    vat_pct    = body.vat_rate_percent if body.vat_rate_percent is not None else acc.vat_rate_percent
    rtn        = body.round_to_nearest if body.round_to_nearest is not None else acc.round_to_nearest

    # Resolve finish catalogue selections
    finish_cost_data = get_finish_cost(spec_id, db)
    finish_lines = finish_cost_data.get("lines", []) if isinstance(finish_cost_data, dict) else []
    finish_total = finish_cost_data.get("total") or 0.0 if isinstance(finish_cost_data, dict) else 0.0

    data = ReviewPackData(
        spec_id=spec_id,
        spec_name=spec.name,
        revision=body.revision or "A",
        project_name=body.project_name or spec.name,
        generated_at=datetime.now(timezone.utc),
        geometry=spec.geometry,
        wall_bu=wall_bu,
        floor_bu=floor_bu,
        roof_bu=roof_bu,
        bom_lines=[l.model_dump() for l in bom.lines],
        bom_areas=bom.areas,
        bom_opening_counts=bom.opening_counts,
        bom_total=bom.total_cost,
        materials=[],
        allowances=[],
        packages=body.packages,
        pkg_overrides=body.pkg_overrides,
        finish_lines=finish_lines,
        finish_total=finish_total,
        markup_percent=markup_pct,
        vat_rate_percent=vat_pct,
        round_to_nearest=rtn,
    )

    pdf_bytes = ClientQuotePDF(data, customer_name=body.customer_name).generate()
    slug = (body.customer_name or spec.name).lower().replace(" ", "-")
    filename = f"pod-client-quote-{slug}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
