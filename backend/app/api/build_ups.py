"""
API: Materials + Build-Up templates

GET    /materials                   list all materials
GET    /materials/{id}              single material
PATCH  /materials/{id}/evidence     update evidence fields (supplier, datasheet, DoP URLs)

POST   /build-ups/validate          validate unsaved editor state (no persist)
POST   /build-ups                   create build-up with layers
GET    /build-ups                   list all library templates
GET    /build-ups/{id}              retrieve with layers + computed result
PUT    /build-ups/{id}              update metadata + replace layers
DELETE /build-ups/{id}

All create/retrieve/update responses include the live-computed U-value result
(u_value, r_total, errors, warnings, targets, assumptions) so the frontend
never needs a separate validate call after save.
"""
from datetime import datetime, timezone, date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import BuildUp, BuildUpLayer, MaterialLibrary, Supplier
from app.skills.build_up_resolver import (
    ResolverLayer,
    ResolverResult,
    TargetResult,
    resolve,
)
from app.skills.u_value import LayerResult

router = APIRouter(tags=["build-ups"])

Db = Annotated[Session, Depends(get_db)]


# ── Pydantic models ───────────────────────────────────────────────────────────

class MaterialOut(BaseModel):
    id: int
    name: str
    manufacturer: str | None
    supplier_name: str | None
    supplier_ref: str | None
    supplier_url: str | None
    datasheet_url: str | None
    dop_url: str | None
    price_source_url: str | None
    price_checked_at: date | None
    evidence_status: str
    evidence_notes: str | None
    evidence_category: str
    lambda_W_mK: float | None
    density_kg_m3: float | None
    fire_euroclass: str | None
    spec_ref: str | None
    unit: str | None
    properties: dict | None
    preferred_supplier_id: str | None = None
    preferred_supplier_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


VALID_EVIDENCE_STATUSES = {"verified", "partial", "missing", "provisional"}

# Categories where a missing datasheet/DoP is expected and normal
_ASSEMBLY_CATEGORIES = {"generic_assembly", "provisional_allowance", "service_item"}


def _auto_evidence_status(mat) -> str:
    """Compute evidence status from category + available fields."""
    cat = getattr(mat, "evidence_category", "manufactured_product") or "manufactured_product"

    if cat in _ASSEMBLY_CATEGORIES:
        return "provisional"

    if cat == "raw_material":
        # Raw/site materials: partial if any supplier/spec source; missing otherwise
        has_any = bool(mat.supplier_url or mat.supplier_name or mat.datasheet_url)
        return "partial" if has_any else "missing"

    # Default: manufactured_product
    has_datasheet = bool(mat.datasheet_url)
    has_supplier  = bool(mat.supplier_url or mat.supplier_name)
    has_mfr       = bool(mat.manufacturer)
    if has_datasheet and has_mfr and has_supplier:
        return "verified"
    if has_datasheet or has_supplier:
        return "partial"
    return "missing"


class EvidenceIn(BaseModel):
    manufacturer: str | None = None
    supplier_name: str | None = None
    supplier_url: str | None = None
    datasheet_url: str | None = None
    dop_url: str | None = None
    fire_euroclass: str | None = None
    density_kg_m3: float | None = None
    price_source_url: str | None = None
    price_checked_at: str | None = None  # ISO date "YYYY-MM-DD"
    evidence_notes: str | None = None
    evidence_status_override: str | None = None  # manual override; None = auto-compute
    evidence_category: str | None = None  # manufactured_product | generic_assembly | raw_material | provisional_allowance | service_item
    preferred_supplier_id: str | None = None  # UUID of supplier from directory; empty string = clear


class LayerIn(BaseModel):
    material_id: int
    thickness_mm: float = Field(ge=0)   # resolver validates > 0 and reports user-friendly error
    position_order: int = Field(ge=1)
    role: str = ""
    framing_fraction: float = Field(default=0.0, ge=0.0, lt=1.0)
    include_in_u_value: bool = True
    sd_value_m: float | None = None
    # Composite framing zone properties
    infill_lambda_W_mK: float | None = None
    infill_type: str | None = None
    infill_name: str | None = None
    infill_material_ref: str | None = None


class LayerOut(BaseModel):
    id: int | None = None       # None for unsaved validate responses
    material_id: int
    material_name: str
    lambda_W_mK: float
    thickness_mm: float
    position_order: int
    role: str
    framing_fraction: float
    include_in_u_value: bool
    sd_value_m: float | None
    # Composite framing zone properties
    infill_lambda_W_mK: float | None = None
    infill_type: str | None = None
    infill_name: str | None = None
    infill_material_ref: str | None = None


class LayerResultOut(BaseModel):
    name: str
    thickness_mm: float
    lambda_effective: float
    r_value: float


class TargetResultOut(BaseModel):
    code: str
    element_type: str
    target_u_value: float
    passes: bool
    headroom: float
    label: str


class BuildUpIn(BaseModel):
    name: str
    element_type: str       # ExternalWall | Floor | Roof
    build_up_type: str = "closed_panel"
    scope: str = "library"
    status: str = "draft"
    notes: str | None = None
    layers: list[LayerIn]


class BuildUpOut(BaseModel):
    id: int | None = None
    name: str
    element_type: str | None
    build_up_type: str | None
    scope: str | None
    status: str | None
    notes: str | None
    created_at: datetime | None
    updated_at: datetime | None
    layers: list[LayerOut]
    # Computed result
    u_value: float
    r_total: float
    total_thickness_mm: float = 0.0
    display_total_thickness: str = ""
    layer_results: list[LayerResultOut]
    errors: list[str]
    warnings: list[str]
    targets: list[TargetResultOut]
    assumptions: list[str]


class BuildUpListItem(BaseModel):
    """Slim response for the build-up list — no layers, no full resolver output."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    element_type: str | None
    build_up_type: str | None
    scope: str | None
    status: str | None
    u_value: float | None


class ValidateIn(BaseModel):
    element_type: str
    layers: list[LayerIn]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch_material(db: Session, material_id: int) -> MaterialLibrary:
    mat = db.get(MaterialLibrary, material_id)
    if mat is None:
        raise HTTPException(status_code=422, detail=f"Material id={material_id} not found.")
    return mat


def _build_resolver_layers(db: Session, layers_in: list[LayerIn]) -> list[ResolverLayer]:
    result = []
    for l in sorted(layers_in, key=lambda x: x.position_order):
        mat = _fetch_material(db, l.material_id)
        result.append(ResolverLayer(
            name=mat.name,
            thickness_mm=l.thickness_mm,
            lambda_W_mK=mat.lambda_W_mK,
            role=l.role,
            framing_fraction=l.framing_fraction,
            include_in_u_value=l.include_in_u_value,
            sd_value_m=l.sd_value_m,
            infill_lambda_W_mK=l.infill_lambda_W_mK,
        ))
    return result


def _resolver_result_to_out(
    result: ResolverResult,
    persisted_layers: list[LayerOut],
    build_up: BuildUp | None = None,
) -> BuildUpOut:
    return BuildUpOut(
        id=build_up.id if build_up else None,
        name=build_up.name if build_up else "",
        element_type=build_up.element_type if build_up else None,
        build_up_type=build_up.build_up_type if build_up else None,
        scope=build_up.scope if build_up else None,
        status=build_up.status if build_up else None,
        notes=build_up.notes if build_up else None,
        created_at=build_up.created_at if build_up else None,
        updated_at=build_up.updated_at if build_up else None,
        layers=persisted_layers,
        u_value=result.u_value,
        r_total=result.r_total,
        total_thickness_mm=result.total_thickness_mm,
        display_total_thickness=f"{round(result.total_thickness_mm)} mm",
        layer_results=[
            LayerResultOut(
                name=lr.name,
                thickness_mm=lr.thickness_mm,
                lambda_effective=lr.lambda_effective,
                r_value=lr.r_value,
            )
            for lr in result.layers
        ],
        errors=result.errors,
        warnings=result.warnings,
        targets=[
            TargetResultOut(
                code=t.code,
                element_type=t.element_type,
                target_u_value=t.target_u_value,
                passes=t.passes,
                headroom=t.headroom,
                label=t.label,
            )
            for t in result.targets
        ],
        assumptions=result.assumptions,
    )


def _layers_out_from_orm(db: Session, orm_layers: list[BuildUpLayer]) -> list[LayerOut]:
    out = []
    for l in orm_layers:
        props = l.properties or {}
        mat = _fetch_material(db, l.material_id)
        out.append(LayerOut(
            id=l.id,
            material_id=l.material_id,
            material_name=mat.name,
            lambda_W_mK=mat.lambda_W_mK,
            thickness_mm=l.thickness_mm,
            position_order=l.position_order,
            role=props.get("role", ""),
            framing_fraction=props.get("framing_fraction", 0.0),
            include_in_u_value=props.get("include_in_u_value", True),
            sd_value_m=props.get("sd_value_m"),
            infill_lambda_W_mK=props.get("infill_lambda_W_mK"),
            infill_type=props.get("infill_type"),
            infill_name=props.get("infill_name"),
            infill_material_ref=props.get("infill_material_ref"),
        ))
    return out


def _layers_out_from_in(db: Session, layers_in: list[LayerIn]) -> list[LayerOut]:
    out = []
    for l in sorted(layers_in, key=lambda x: x.position_order):
        mat = _fetch_material(db, l.material_id)
        out.append(LayerOut(
            id=None,
            material_id=l.material_id,
            material_name=mat.name,
            lambda_W_mK=mat.lambda_W_mK,
            thickness_mm=l.thickness_mm,
            position_order=l.position_order,
            role=l.role,
            framing_fraction=l.framing_fraction,
            include_in_u_value=l.include_in_u_value,
            sd_value_m=l.sd_value_m,
            infill_lambda_W_mK=l.infill_lambda_W_mK,
            infill_type=l.infill_type,
            infill_name=l.infill_name,
            infill_material_ref=l.infill_material_ref,
        ))
    return out


def _compute_and_respond(
    db: Session,
    body: BuildUpIn | ValidateIn,
    build_up: BuildUp | None = None,
) -> BuildUpOut:
    resolver_layers = _build_resolver_layers(db, body.layers)
    result = resolve(resolver_layers, body.element_type)
    layers_out = _layers_out_from_in(db, body.layers)
    out = _resolver_result_to_out(result, layers_out, build_up)
    if build_up is not None:
        out.name = build_up.name
    else:
        out.name = getattr(body, "name", "")
    return out


# ── Materials endpoints ───────────────────────────────────────────────────────

def _enrich_material(mat: MaterialLibrary, db: Session) -> MaterialOut:
    out = MaterialOut.model_validate(mat, from_attributes=True)
    if mat.preferred_supplier_id:
        supplier = db.get(Supplier, mat.preferred_supplier_id)
        if supplier:
            out.preferred_supplier_id = str(mat.preferred_supplier_id)
            out.preferred_supplier_name = supplier.name
    return out


@router.get("/materials", response_model=list[MaterialOut])
def list_materials(db: Db):
    mats = db.query(MaterialLibrary).order_by(MaterialLibrary.id).all()
    return [_enrich_material(m, db) for m in mats]


@router.get("/materials/{material_id}", response_model=MaterialOut)
def get_material(material_id: int, db: Db):
    mat = db.get(MaterialLibrary, material_id)
    if mat is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    return _enrich_material(mat, db)


@router.patch("/materials/{material_id}/evidence", response_model=MaterialOut)
def update_material_evidence(material_id: int, body: EvidenceIn, db: Db):
    from datetime import date
    mat = db.get(MaterialLibrary, material_id)
    if mat is None:
        raise HTTPException(status_code=404, detail="Material not found.")

    if body.manufacturer     is not None: mat.manufacturer     = body.manufacturer or None
    if body.supplier_name    is not None: mat.supplier_name    = body.supplier_name or None
    if body.supplier_url     is not None: mat.supplier_url     = body.supplier_url or None
    if body.datasheet_url    is not None: mat.datasheet_url    = body.datasheet_url or None
    if body.dop_url          is not None: mat.dop_url          = body.dop_url or None
    if body.fire_euroclass   is not None: mat.fire_euroclass   = body.fire_euroclass or None
    if body.density_kg_m3    is not None: mat.density_kg_m3    = body.density_kg_m3
    if body.price_source_url is not None: mat.price_source_url = body.price_source_url or None
    if body.price_checked_at is not None:
        try:
            mat.price_checked_at = date.fromisoformat(body.price_checked_at)
        except ValueError:
            pass
    if body.evidence_notes is not None:
        mat.evidence_notes = body.evidence_notes or None
    if body.evidence_category is not None:
        mat.evidence_category = body.evidence_category

    # Preferred supplier link
    if body.preferred_supplier_id is not None:
        if body.preferred_supplier_id == '':
            mat.preferred_supplier_id = None
        else:
            import uuid as _uuid
            try:
                supplier_uuid = _uuid.UUID(body.preferred_supplier_id)
                supplier = db.get(Supplier, supplier_uuid)
                if supplier:
                    mat.preferred_supplier_id = supplier_uuid
                    # Auto-fill supplier_name and supplier_url from directory if not already set
                    if not mat.supplier_name:
                        mat.supplier_name = supplier.name
                    if not mat.supplier_url and supplier.website:
                        mat.supplier_url = supplier.website
            except ValueError:
                pass

    # Evidence status: manual override takes precedence over auto-compute
    if body.evidence_status_override is not None:
        override = body.evidence_status_override.lower()
        if override in VALID_EVIDENCE_STATUSES:
            mat.evidence_status = override
    else:
        mat.evidence_status = _auto_evidence_status(mat)

    db.commit()
    db.refresh(mat)

    # Build response — enrich with preferred supplier name
    out = MaterialOut.model_validate(mat, from_attributes=True)
    if mat.preferred_supplier_id:
        supplier = db.get(Supplier, mat.preferred_supplier_id)
        if supplier:
            out.preferred_supplier_id = str(mat.preferred_supplier_id)
            out.preferred_supplier_name = supplier.name
    return out


class MaterialCreateIn(BaseModel):
    name: str
    manufacturer: str | None = None
    supplier_name: str | None = None
    supplier_ref: str | None = None
    spec_ref: str | None = None
    lambda_W_mK: float | None = None
    density_kg_m3: float | None = None
    fire_euroclass: str | None = None
    supplier_url: str | None = None
    datasheet_url: str | None = None
    dop_url: str | None = None
    unit: str = "m2"
    currency: str = "EUR"
    properties: dict | None = None
    evidence_category: str = "manufactured_product"


@router.post("/materials", response_model=MaterialOut, status_code=201)
def create_material(body: MaterialCreateIn, db: Db):
    mat = MaterialLibrary(
        library_version_id = 1,
        name               = body.name,
        manufacturer       = body.manufacturer,
        supplier_name      = body.supplier_name,
        supplier_ref       = body.supplier_ref,
        spec_ref           = body.spec_ref,
        lambda_W_mK        = body.lambda_W_mK,
        density_kg_m3      = body.density_kg_m3,
        fire_euroclass     = body.fire_euroclass,
        supplier_url       = body.supplier_url,
        datasheet_url      = body.datasheet_url,
        dop_url            = body.dop_url,
        unit               = body.unit,
        currency           = body.currency,
        evidence_category  = body.evidence_category,
        properties         = body.properties or {},
    )
    mat.evidence_status = _auto_evidence_status(mat)
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return mat


@router.delete("/materials/{material_id}", status_code=204)
def delete_material(material_id: int, db: Db):
    mat = db.get(MaterialLibrary, material_id)
    if mat is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    # Check if used in any build-up layer
    from app.models import BuildUpLayer
    usage = db.query(BuildUpLayer).filter(BuildUpLayer.material_id == material_id).count()
    if usage:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete — material is used in {usage} build-up layer(s). Remove it from all build-ups first.",
        )
    db.delete(mat)
    db.commit()


# ── Build-up validate (no persist) ───────────────────────────────────────────

@router.post("/build-ups/validate", response_model=BuildUpOut)
def validate_build_up(body: ValidateIn, db: Db):
    """Validate unsaved editor state. Returns U-value + errors/warnings without persisting."""
    resolver_layers = _build_resolver_layers(db, body.layers)
    result = resolve(resolver_layers, body.element_type)
    layers_out = _layers_out_from_in(db, body.layers)
    out = _resolver_result_to_out(result, layers_out)
    out.element_type = body.element_type
    return out


# ── Build-up CRUD ─────────────────────────────────────────────────────────────

@router.post("/build-ups", response_model=BuildUpOut, status_code=201)
def create_build_up(body: BuildUpIn, db: Db):
    build_up = BuildUp(
        name=body.name,
        element_type=body.element_type,
        build_up_type=body.build_up_type,
        scope=body.scope,
        status=body.status,
        notes=body.notes,
    )
    db.add(build_up)
    db.flush()

    for l in body.layers:
        db.add(BuildUpLayer(
            build_up_id=build_up.id,
            material_id=l.material_id,
            thickness_mm=l.thickness_mm,
            position_order=l.position_order,
            properties={
                "role": l.role,
                "framing_fraction": l.framing_fraction,
                "include_in_u_value": l.include_in_u_value,
                "sd_value_m": l.sd_value_m,
                "infill_lambda_W_mK": l.infill_lambda_W_mK,
                "infill_type": l.infill_type,
                "infill_name": l.infill_name,
                "infill_material_ref": l.infill_material_ref,
            },
        ))

    resolver_layers = _build_resolver_layers(db, body.layers)
    result = resolve(resolver_layers, body.element_type)
    build_up.u_value = result.u_value
    db.commit()
    db.refresh(build_up)

    layers_out = _layers_out_from_orm(db, build_up.layers)
    return _resolver_result_to_out(result, layers_out, build_up)


@router.get("/build-ups", response_model=list[BuildUpListItem])
def list_build_ups(db: Db):
    return db.query(BuildUp).order_by(BuildUp.id).all()


@router.get("/build-ups/{build_up_id}", response_model=BuildUpOut)
def get_build_up(build_up_id: int, db: Db):
    bu = db.get(BuildUp, build_up_id)
    if bu is None:
        raise HTTPException(status_code=404, detail="Build-up not found.")
    layers_out = _layers_out_from_orm(db, bu.layers)
    resolver_layers = [
        ResolverLayer(
            name=lo.material_name,
            thickness_mm=lo.thickness_mm,
            lambda_W_mK=lo.lambda_W_mK,
            role=lo.role,
            framing_fraction=lo.framing_fraction,
            include_in_u_value=lo.include_in_u_value,
            sd_value_m=lo.sd_value_m,
        )
        for lo in layers_out
    ]
    result = resolve(resolver_layers, bu.element_type or "ExternalWall")
    return _resolver_result_to_out(result, layers_out, bu)


@router.put("/build-ups/{build_up_id}", response_model=BuildUpOut)
def update_build_up(build_up_id: int, body: BuildUpIn, db: Db):
    bu = db.get(BuildUp, build_up_id)
    if bu is None:
        raise HTTPException(status_code=404, detail="Build-up not found.")

    # Update metadata
    bu.name = body.name
    bu.element_type = body.element_type
    bu.build_up_type = body.build_up_type
    bu.scope = body.scope
    bu.status = body.status
    bu.notes = body.notes
    bu.updated_at = datetime.now(timezone.utc)

    # Replace layers
    for old_layer in list(bu.layers):
        db.delete(old_layer)
    db.flush()

    for l in body.layers:
        db.add(BuildUpLayer(
            build_up_id=bu.id,
            material_id=l.material_id,
            thickness_mm=l.thickness_mm,
            position_order=l.position_order,
            properties={
                "role": l.role,
                "framing_fraction": l.framing_fraction,
                "include_in_u_value": l.include_in_u_value,
                "sd_value_m": l.sd_value_m,
                "infill_lambda_W_mK": l.infill_lambda_W_mK,
                "infill_type": l.infill_type,
                "infill_name": l.infill_name,
                "infill_material_ref": l.infill_material_ref,
            },
        ))

    resolver_layers = _build_resolver_layers(db, body.layers)
    result = resolve(resolver_layers, body.element_type)
    bu.u_value = result.u_value
    db.commit()
    db.refresh(bu)

    layers_out = _layers_out_from_orm(db, bu.layers)
    return _resolver_result_to_out(result, layers_out, bu)


@router.delete("/build-ups/{build_up_id}", status_code=204)
def delete_build_up(build_up_id: int, db: Db):
    bu = db.get(BuildUp, build_up_id)
    if bu is None:
        raise HTTPException(status_code=404, detail="Build-up not found.")
    if bu.status == "approved" or bu.scope == "library":
        raise HTTPException(
            status_code=403,
            detail="Approved library build-ups cannot be deleted. Duplicate and edit instead.",
        )
    for layer in list(bu.layers):
        db.delete(layer)
    db.delete(bu)
    db.commit()
