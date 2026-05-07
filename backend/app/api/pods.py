"""
API: Pod endpoints

POST /pods/decompose       — parametric decomposition, returns element list + envelope summary
POST /pods/takeoff         — decompose + material take-off with a build-up preset
POST /pods/u-value         — single-element U-value calculation against a target
POST /pods/u-value-check   — full pod U-value check for all elements against a jurisdiction
"""
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.skills.element_decomposer import (
    DecompositionError,
    OpeningSpec,
    decompose_pod,
    total_external_area,
)
from app.skills.material_takeoff import (
    TakeoffError,
    NORDIC_STANDARD,
    takeoff,
    takeoff_summary,
)
from app.skills.procurement_csv import (
    MATERIAL_PRICES,
    procurement_schedule,
    schedule_total,
    to_csv_string,
)
from app.skills.u_value import (
    JURISDICTION_TARGETS,
    THERMAL_PRESETS,
    UValueError,
    UValueLayer,
    UValueResult,
    calculate_u_value,
)

router = APIRouter(prefix="/pods", tags=["pods"])


# ── Shared request models ─────────────────────────────────────────────────────

class OpeningIn(BaseModel):
    wall: Literal["N", "S", "E", "W"]
    type: Literal["window", "door", "french_door", "vent", "rooflights"]
    width_m: float = Field(..., gt=0)
    height_m: float = Field(..., gt=0)
    sill_height_m: float = Field(0.0, ge=0)
    x_offset_m: float | None = Field(None, ge=0, description="Offset from left edge (m). For circular openings this is the centre x.")
    shape: Literal["rectangular", "circular"] = "rectangular"


class PodGeometryIn(BaseModel):
    width_m: float = Field(..., gt=0, description="External width, E–W direction (m)")
    length_m: float = Field(..., gt=0, description="External length, N–S direction (m)")
    wall_height_m: float = Field(..., gt=0, description="Eaves height (m)")
    roof_type: Literal["flat", "mono_pitch", "duo_pitch"] = "duo_pitch"
    roof_pitch_deg: float = Field(15.0, ge=0, lt=90, description="Roof slope angle (°)")
    openings: list[OpeningIn] = []


# ── Shared response models ────────────────────────────────────────────────────

class ElementOut(BaseModel):
    type: str
    label: str
    area_gross_m2: float
    area_net_m2: float
    perimeter_m: float
    geometry: dict


class DecomposeResponse(BaseModel):
    elements: list[ElementOut]
    summary: dict


# ── POST /pods/decompose ──────────────────────────────────────────────────────

@router.post(
    "/decompose",
    response_model=DecomposeResponse,
    summary="Decompose a pod into typed building elements",
    description=(
        "Takes a parametric pod description and returns a structured list of "
        "building elements (floor, roof, walls, openings) with gross/net areas "
        "and an envelope area summary. Pure calculation — no data is stored."
    ),
)
def decompose(body: PodGeometryIn):
    try:
        openings = [
            OpeningSpec(
                wall=o.wall,
                type=o.type,
                width_m=o.width_m,
                height_m=o.height_m,
                sill_height_m=o.sill_height_m,
                x_offset_m=o.x_offset_m,
                shape=o.shape,
            )
            for o in body.openings
        ]
        elements = decompose_pod(
            width_m=body.width_m,
            length_m=body.length_m,
            wall_height_m=body.wall_height_m,
            roof_type=body.roof_type,
            roof_pitch_deg=body.roof_pitch_deg,
            openings=openings,
        )
    except DecompositionError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=str(exc))

    return DecomposeResponse(
        elements=[
            ElementOut(
                type=e.type,
                label=e.label,
                area_gross_m2=e.area_gross_m2,
                area_net_m2=e.area_net_m2,
                perimeter_m=e.perimeter_m,
                geometry=e.geometry,
            )
            for e in elements
        ],
        summary=total_external_area(elements),
    )


# ── POST /pods/takeoff ────────────────────────────────────────────────────────

PRESETS = {
    "nordic_standard": NORDIC_STANDARD,
}


class TakeoffRequest(PodGeometryIn):
    build_up_preset: Literal["nordic_standard"] = Field(
        "nordic_standard",
        description="Named build-up preset to use for material quantities.",
    )


class MaterialLineOut(BaseModel):
    element_label: str
    element_type: str
    material_name: str
    layer_type: str
    quantity_net: float
    quantity: float
    unit: str
    waste_factor: float
    notes: str


class TakeoffResponse(BaseModel):
    elements: list[ElementOut]
    element_summary: dict
    lines: list[MaterialLineOut]
    material_summary: dict


@router.post(
    "/takeoff",
    response_model=TakeoffResponse,
    summary="Decompose and calculate material take-off quantities",
    description=(
        "Decomposes the pod into elements, then calculates material quantities "
        "per element using the specified build-up preset. Returns both the element "
        "list and a line-by-line material schedule with waste-adjusted order "
        "quantities. Pure calculation — no data is stored."
    ),
)
def pod_takeoff(body: TakeoffRequest):
    from fastapi import HTTPException

    try:
        openings = [
            OpeningSpec(
                wall=o.wall,
                type=o.type,
                width_m=o.width_m,
                height_m=o.height_m,
                sill_height_m=o.sill_height_m,
                x_offset_m=o.x_offset_m,
                shape=o.shape,
            )
            for o in body.openings
        ]
        elements = decompose_pod(
            width_m=body.width_m,
            length_m=body.length_m,
            wall_height_m=body.wall_height_m,
            roof_type=body.roof_type,
            roof_pitch_deg=body.roof_pitch_deg,
            openings=openings,
        )
    except DecompositionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    build_ups = PRESETS[body.build_up_preset]

    try:
        lines = takeoff(elements, build_ups)
    except TakeoffError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return TakeoffResponse(
        elements=[
            ElementOut(
                type=e.type,
                label=e.label,
                area_gross_m2=e.area_gross_m2,
                area_net_m2=e.area_net_m2,
                perimeter_m=e.perimeter_m,
                geometry=e.geometry,
            )
            for e in elements
        ],
        element_summary=total_external_area(elements),
        lines=[
            MaterialLineOut(
                element_label=l.element_label,
                element_type=l.element_type,
                material_name=l.material_name,
                layer_type=l.layer_type,
                quantity_net=l.quantity_net,
                quantity=l.quantity,
                unit=l.unit,
                waste_factor=l.waste_factor,
                notes=l.notes,
            )
            for l in lines
        ],
        material_summary=takeoff_summary(lines),
    )


# ── POST /pods/u-value ────────────────────────────────────────────────────────

class UValueLayerIn(BaseModel):
    name: str
    thickness_mm: float = Field(..., gt=0)
    lambda_W_mK: float = Field(..., gt=0)
    framing_fraction: float = Field(0.0, ge=0.0, lt=1.0)
    lambda_framing: float = Field(0.13, gt=0)


class UValueRequest(BaseModel):
    element_type: Literal["ExternalWall", "Floor", "Roof"]
    element_label: str = ""
    layers: list[UValueLayerIn]
    target_u: float = Field(..., gt=0, description="Jurisdiction U-value limit W/m²K")


class LayerResultOut(BaseModel):
    name: str
    thickness_mm: float
    lambda_effective: float
    r_value: float


class UValueResultOut(BaseModel):
    element_type: str
    element_label: str
    u_value: float
    r_total: float
    r_si: float
    r_se: float
    layers: list[LayerResultOut]
    target_u: float
    status: str
    margin: float


def _result_to_out(r: UValueResult) -> UValueResultOut:
    return UValueResultOut(
        element_type=r.element_type,
        element_label=r.element_label,
        u_value=r.u_value,
        r_total=r.r_total,
        r_si=r.r_si,
        r_se=r.r_se,
        layers=[LayerResultOut(
            name=lr.name,
            thickness_mm=lr.thickness_mm,
            lambda_effective=lr.lambda_effective,
            r_value=lr.r_value,
        ) for lr in r.layers],
        target_u=r.target_u,
        status=r.status,
        margin=r.margin,
    )


@router.post(
    "/u-value",
    response_model=UValueResultOut,
    summary="Calculate U-value for a single element",
    description=(
        "Calculates the U-value of a building element using ISO 6946 isothermal "
        "planes method. Supports bridged layers (framing + insulation fill) via "
        "the parallel path method. Returns PASS/FAIL against the supplied target."
    ),
)
def u_value(body: UValueRequest):
    from fastapi import HTTPException
    try:
        result = calculate_u_value(
            element_type=body.element_type,
            layers=[
                UValueLayer(
                    name=l.name,
                    thickness_mm=l.thickness_mm,
                    lambda_W_mK=l.lambda_W_mK,
                    framing_fraction=l.framing_fraction,
                    lambda_framing=l.lambda_framing,
                )
                for l in body.layers
            ],
            target_u=body.target_u,
            element_label=body.element_label,
        )
    except UValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _result_to_out(result)


# ── POST /pods/u-value-check ──────────────────────────────────────────────────

class UValueCheckRequest(BaseModel):
    build_up_preset: Literal["nordic_standard"] = "nordic_standard"
    jurisdiction: Literal["BBR_SE", "TEK17_NO"] = "BBR_SE"


class ElementCheckOut(BaseModel):
    element_type: str
    u_value: float
    target_u: float
    status: str
    margin: float
    r_total: float
    layers: list[LayerResultOut]


class UValueCheckResponse(BaseModel):
    jurisdiction: str
    build_up_preset: str
    overall_status: str           # "PASS" if all elements pass, else "FAIL"
    checks: list[ElementCheckOut]


@router.post(
    "/u-value-check",
    response_model=UValueCheckResponse,
    summary="Full pod U-value check against a jurisdiction profile",
    description=(
        "Runs U-value calculations for all three element types (wall, roof, floor) "
        "using a named build-up preset and compares each against the jurisdiction "
        "thermal targets. Returns PASS/FAIL per element and an overall status."
    ),
)
def u_value_check(body: UValueCheckRequest):
    from fastapi import HTTPException

    preset_layers = THERMAL_PRESETS.get(body.build_up_preset)
    if preset_layers is None:
        raise HTTPException(status_code=422, detail=f"Unknown build_up_preset: {body.build_up_preset!r}")

    targets = JURISDICTION_TARGETS[body.jurisdiction]
    checks: list[ElementCheckOut] = []

    for element_type in ("ExternalWall", "Floor", "Roof"):
        layers = preset_layers.get(element_type)
        if layers is None:
            continue
        target_u = targets[element_type]
        try:
            r = calculate_u_value(element_type, layers, target_u)
        except UValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        checks.append(ElementCheckOut(
            element_type=element_type,
            u_value=r.u_value,
            target_u=r.target_u,
            status=r.status,
            margin=r.margin,
            r_total=r.r_total,
            layers=[LayerResultOut(
                name=lr.name,
                thickness_mm=lr.thickness_mm,
                lambda_effective=lr.lambda_effective,
                r_value=lr.r_value,
            ) for lr in r.layers],
        ))

    overall = "PASS" if all(c.status == "PASS" for c in checks) else "FAIL"
    return UValueCheckResponse(
        jurisdiction=body.jurisdiction,
        build_up_preset=body.build_up_preset,
        overall_status=overall,
        checks=checks,
    )


# ── POST /pods/procurement-csv ────────────────────────────────────────────────

class ProcurementRequest(TakeoffRequest):
    jurisdiction: Literal["BBR_SE", "TEK17_NO"] = "BBR_SE"


@router.post(
    "/procurement-csv",
    summary="Generate a procurement schedule CSV",
    description=(
        "Decomposes the pod, runs the material take-off, and returns a "
        "downloadable CSV procurement schedule with order quantities, supplier "
        "references, unit prices, and estimated costs. "
        "Prices are indicative (from the materials library defaults)."
    ),
    response_class=Response,
)
def procurement_csv(body: ProcurementRequest):
    from fastapi import HTTPException

    try:
        openings = [
            OpeningSpec(
                wall=o.wall, type=o.type,
                width_m=o.width_m, height_m=o.height_m,
                sill_height_m=o.sill_height_m,
                x_offset_m=o.x_offset_m,
                shape=o.shape,
            )
            for o in body.openings
        ]
        elements = decompose_pod(
            width_m=body.width_m, length_m=body.length_m,
            wall_height_m=body.wall_height_m, roof_type=body.roof_type,
            roof_pitch_deg=body.roof_pitch_deg, openings=openings,
        )
    except DecompositionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    build_ups = PRESETS[body.build_up_preset]
    try:
        lines = takeoff(elements, build_ups)
    except TakeoffError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    rows = procurement_schedule(lines, pricing=MATERIAL_PRICES)
    pod_spec = {
        "width_m":        body.width_m,
        "length_m":       body.length_m,
        "wall_height_m":  body.wall_height_m,
        "roof_type":      body.roof_type,
        "roof_pitch_deg": body.roof_pitch_deg,
    }
    csv_content = to_csv_string(rows, pod_spec, build_up_preset=body.build_up_preset)

    filename = (
        f"procurement_{body.width_m}x{body.length_m}m"
        f"_{body.roof_type}_{body.build_up_preset}.csv"
    )
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
