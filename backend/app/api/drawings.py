"""
API: Drawing endpoints

POST /drawings/floor-plan   — SVG floor plan (top-down view)
POST /drawings/wall/{face}  — SVG wall elevation for N / S / E / W
POST /drawings/all          — all five drawings as a JSON dict of SVG strings
"""
from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.skills.drawing_generator import (
    floor_plan_svg,
    generate_drawings,
    manufacture_plan_svg,
    wall_elevation_svg,
)
from app.skills.element_decomposer import DecompositionError, OpeningSpec, decompose_pod
from app.api.pods import OpeningIn, PodGeometryIn

router = APIRouter(prefix="/drawings", tags=["drawings"])

_SVG_MIME = "image/svg+xml; charset=utf-8"


class DrawingRequest(PodGeometryIn):
    stud_spacing_mm: int = 600
    wall_thick_m: float = 0.30
    pod_name: str = ""
    roof_openings: list | None = None
    wall_u_value: float | None = None
    floor_u_value: float | None = None
    roof_u_value: float | None = None


class ManufacturePlanRequest(DrawingRequest):
    project_name: str = ""
    client_project_id: str = ""
    drawn_by: str = ""
    checked_by: str = ""
    revision: str = "P1"
    drawing_number: str = ""
    status: str = "Preliminary"
    issue_date: str = ""
    scale_str: str = "1:50"
    disclaimer: str = "This drawing is indicative only. All dimensions to be verified on site."


# ── Shared helper ─────────────────────────────────────────────────────────────

def _decompose(body: DrawingRequest):
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
        return decompose_pod(
            width_m=body.width_m,
            length_m=body.length_m,
            wall_height_m=body.wall_height_m,
            roof_type=body.roof_type,
            roof_pitch_deg=body.roof_pitch_deg,
            openings=openings,
        )
    except DecompositionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ── POST /drawings/floor-plan ─────────────────────────────────────────────────

@router.post(
    "/floor-plan",
    summary="Generate SVG floor plan",
    description=(
        "Returns a schematic top-down SVG floor plan for the pod with compass "
        "orientation and opening indicators. Long axis is drawn horizontally, "
        "N wall at top. Pure calculation — no data is stored."
    ),
    response_class=Response,
)
def drawing_floor_plan(body: DrawingRequest):
    elements = _decompose(body)
    svg = generate_drawings(
        elements,
        width_m=body.width_m,
        length_m=body.length_m,
        wall_height_m=body.wall_height_m,
        stud_spacing_mm=body.stud_spacing_mm,
        wall_thick_m=body.wall_thick_m,
        pod_name=body.pod_name,
        roof_openings=body.roof_openings,
        wall_u_value=body.wall_u_value,
        floor_u_value=body.floor_u_value,
        roof_u_value=body.roof_u_value,
    )["floor_plan"]
    return Response(content=svg, media_type=_SVG_MIME)


# ── POST /drawings/wall/{face} ────────────────────────────────────────────────

@router.post(
    "/wall/{face}",
    summary="Generate SVG wall elevation",
    description=(
        "Returns a framing elevation SVG for one wall face (N/S/E/W). "
        "Shows studs, top/sole plates, openings with lintel lines, and "
        "dimension annotations. Stud positions are schematic when openings "
        "are present."
    ),
    response_class=Response,
)
def drawing_wall(
    face: Literal["N", "S", "E", "W"],
    body: DrawingRequest,
):
    elements = _decompose(body)
    drawings = generate_drawings(
        elements,
        width_m=body.width_m,
        length_m=body.length_m,
        wall_height_m=body.wall_height_m,
        stud_spacing_mm=body.stud_spacing_mm,
        wall_thick_m=body.wall_thick_m,
        pod_name=body.pod_name,
        roof_openings=body.roof_openings,
        wall_u_value=body.wall_u_value,
        floor_u_value=body.floor_u_value,
        roof_u_value=body.roof_u_value,
    )
    svg = drawings[f"wall_{face}"]
    return Response(content=svg, media_type=_SVG_MIME)


# ── POST /drawings/all ────────────────────────────────────────────────────────

@router.post(
    "/manufacture-plan",
    summary="Generate manufacture-suite floor plan",
    description=(
        "Returns a JSON object with the SVG string and drawing metadata. "
        "The SVG uses a fixed A3-landscape sheet with protected zones: "
        "sheet border, drawing viewport, and title block."
    ),
)
def drawing_manufacture_plan(body: ManufacturePlanRequest) -> dict:
    elements = _decompose(body)
    opening_elements = [e for e in elements if e.type == "Opening"]
    all_openings = []
    for oe in opening_elements:
        g = oe.geometry
        all_openings.append({
            "wall":          g["wall"],
            "type":          g["type"],
            "width_m":       g["width_m"],
            "height_m":      g["height_m"],
            "sill_height_m": g.get("sill_height_m", 0.0),
            "x_offset_m":    g.get("x_offset_m"),
            "shape":         g.get("shape", "rectangular"),
        })
    resolved_issue_date = body.issue_date or date.today().isoformat()
    svg = manufacture_plan_svg(
        width_m=body.width_m,
        length_m=body.length_m,
        openings=all_openings,
        wall_thick_m=body.wall_thick_m,
        pod_name=body.pod_name,
        project_name=body.project_name,
        client_project_id=body.client_project_id,
        drawn_by=body.drawn_by,
        checked_by=body.checked_by,
        revision=body.revision,
        drawing_number=body.drawing_number,
        status=body.status,
        issue_date=resolved_issue_date,
        scale_str=body.scale_str,
        disclaimer=body.disclaimer,
        roof_openings=body.roof_openings,
    )
    return {
        "svg":              svg,
        "drawing_type":     "manufacture_plan",
        "drawing_number":   body.drawing_number or "—",
        "drawing_title":    f"Floor Plan  {body.length_m:.2f}m × {body.width_m:.2f}m",
        "scale":            body.scale_str,
        "revision":         body.revision,
        "status":           body.status,
        "project_name":     body.project_name or body.pod_name,
        "client_project_id": body.client_project_id,
        "drawn_by":         body.drawn_by,
        "checked_by":       body.checked_by,
        "issue_date":       resolved_issue_date,
        "warnings":         [],
    }


@router.post(
    "/all",
    summary="Generate all five pod drawings",
    description=(
        "Returns all five drawings — floor plan + four wall elevations — "
        "as a JSON object with keys: floor_plan, wall_N, wall_S, wall_E, wall_W. "
        "Each value is an SVG string ready for browser rendering or file download."
    ),
)
def drawing_all(body: DrawingRequest) -> dict[str, str]:
    elements = _decompose(body)
    return generate_drawings(
        elements,
        width_m=body.width_m,
        length_m=body.length_m,
        wall_height_m=body.wall_height_m,
        stud_spacing_mm=body.stud_spacing_mm,
        wall_thick_m=body.wall_thick_m,
        pod_name=body.pod_name,
        roof_openings=body.roof_openings,
        wall_u_value=body.wall_u_value,
        floor_u_value=body.floor_u_value,
        roof_u_value=body.roof_u_value,
    )
