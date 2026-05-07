"""
Skill: Element Decomposer

Takes a parametric pod description and returns a typed list of building elements
(walls, roof, floor, openings) with gross/net areas and perimeters.

This is a pure function — no database access. The Celery task wrapper that persists
results to Element rows is in tasks/decompose.py (Week 5).

Coordinate convention
─────────────────────
  Width  runs E–W  (short dimension)
  Length runs N–S  (long dimension)

  N wall = long wall (length × height), far side
  S wall = long wall (length × height), near side
  E wall = short/gable wall (width × height), right side
  W wall = short/gable wall (width × height), left side

Roof types
──────────
  flat      — horizontal plane, area = width × length
  mono_pitch — single slope along width axis, rise at W wall
  duo_pitch  — symmetric ridge along length axis (most common pod roof)
"""
import math
from dataclasses import dataclass, field
from typing import Literal

RoofType  = Literal["flat", "mono_pitch", "duo_pitch"]
WallFace  = Literal["N", "S", "E", "W"]
OpeningType = Literal["window", "door", "french_door", "vent", "rooflights"]


OpeningShape = Literal["rectangular", "circular"]


@dataclass
class OpeningSpec:
    wall: WallFace
    type: OpeningType
    width_m: float
    height_m: float
    sill_height_m: float = 0.0
    x_offset_m: float | None = None   # from left edge; for circular = centre x
    shape: OpeningShape = "rectangular"

    @property
    def area_m2(self) -> float:
        if self.shape == "circular":
            r = self.width_m / 2.0
            return math.pi * r * r
        return self.width_m * self.height_m


@dataclass
class DecomposedElement:
    type: str           # ExternalWall | Floor | Roof | Opening
    label: str          # wall_N, wall_S, wall_E, wall_W, floor, roof, opening_window_1 …
    area_gross_m2: float
    area_net_m2: float
    perimeter_m: float
    geometry: dict = field(default_factory=dict)


class DecompositionError(ValueError):
    pass


def _validate_inputs(
    width_m: float,
    length_m: float,
    wall_height_m: float,
    roof_pitch_deg: float,
    openings: list[OpeningSpec],
) -> None:
    if width_m <= 0 or length_m <= 0 or wall_height_m <= 0:
        raise DecompositionError("width, length, and wall_height must be positive.")
    if not (0 <= roof_pitch_deg < 90):
        raise DecompositionError("roof_pitch_deg must be in [0, 90).")
    for o in openings:
        if o.width_m <= 0 or o.height_m <= 0:
            raise DecompositionError(f"Opening on wall {o.wall}: width and height must be positive.")
        if o.sill_height_m < 0:
            raise DecompositionError(f"Opening on wall {o.wall}: sill_height_m cannot be negative.")


def decompose_pod(
    width_m: float,
    length_m: float,
    wall_height_m: float,
    roof_type: RoofType = "duo_pitch",
    roof_pitch_deg: float = 15.0,
    openings: list[OpeningSpec] | None = None,
) -> list[DecomposedElement]:
    """
    Decompose a rectangular closed-panel pod into typed building elements.

    Parameters
    ----------
    width_m         Pod external width, E–W direction.
    length_m        Pod external length, N–S direction.
    wall_height_m   Eaves height (floor to underside of roof plate).
    roof_type       "flat" | "mono_pitch" | "duo_pitch".
    roof_pitch_deg  Slope angle in degrees (ignored for flat).
    openings        List of OpeningSpec objects describing windows, doors, vents.

    Returns
    -------
    List of DecomposedElement, always in this order:
      floor, roof, wall_N, wall_S, wall_E, wall_W, opening_* …
    """
    if openings is None:
        openings = []

    _validate_inputs(width_m, length_m, wall_height_m, roof_pitch_deg, openings)

    _span = {"N": length_m, "S": length_m, "E": width_m, "W": width_m}
    for o in openings:
        span = _span[o.wall]
        if o.x_offset_m is not None:
            right = o.x_offset_m + o.width_m
            if right > span + 0.001:
                # Clamp: shift left so opening fits within wall span
                o = OpeningSpec(
                    wall=o.wall, type=o.type, shape=o.shape,
                    width_m=min(o.width_m, span),
                    height_m=o.height_m,
                    sill_height_m=o.sill_height_m,
                    x_offset_m=max(0.0, span - o.width_m),
                )
        top = o.sill_height_m + o.height_m
        if top > wall_height_m + 0.001:
            # Clamp: reduce height so opening fits within wall height
            clamped_h = max(0.05, wall_height_m - o.sill_height_m)
            o = OpeningSpec(
                wall=o.wall, type=o.type, shape=o.shape,
                width_m=o.width_m,
                height_m=round(clamped_h, 4),
                sill_height_m=o.sill_height_m,
                x_offset_m=o.x_offset_m,
            )

    pitch_rad = math.radians(roof_pitch_deg)
    elements: list[DecomposedElement] = []

    # ── Roof geometry ───────────────────────────────────────────────────────
    if roof_type == "flat":
        roof_slope_area_m2   = width_m * length_m
        ridge_rise_m         = 0.0
        gable_triangle_area  = 0.0
        e_wall_total_h       = wall_height_m
        w_wall_total_h       = wall_height_m

    elif roof_type == "mono_pitch":
        # Single slope: W wall is the high side, E wall is low side
        # Rise runs across the full width
        ridge_rise_m        = width_m * math.tan(pitch_rad)
        slope_length_m      = width_m / math.cos(pitch_rad)
        roof_slope_area_m2  = slope_length_m * length_m
        gable_triangle_area = 0.5 * width_m * ridge_rise_m
        # Gable wall heights differ — E is eaves height, W is eaves + full rise
        e_wall_total_h      = wall_height_m
        w_wall_total_h      = wall_height_m + ridge_rise_m

    elif roof_type == "duo_pitch":
        # Symmetric ridge along N–S axis; each half-slope spans width/2
        half_width          = width_m / 2.0
        ridge_rise_m        = half_width * math.tan(pitch_rad)
        slope_length_m      = half_width / math.cos(pitch_rad)
        roof_slope_area_m2  = 2.0 * slope_length_m * length_m
        gable_triangle_area = 0.5 * width_m * ridge_rise_m  # per gable end
        e_wall_total_h      = wall_height_m + ridge_rise_m  # to ridge apex
        w_wall_total_h      = wall_height_m + ridge_rise_m

    else:
        raise DecompositionError(f"Unknown roof_type: {roof_type!r}")

    # ── Floor ───────────────────────────────────────────────────────────────
    floor_area = width_m * length_m
    elements.append(DecomposedElement(
        type="Floor",
        label="floor",
        area_gross_m2=floor_area,
        area_net_m2=floor_area,
        perimeter_m=2.0 * (width_m + length_m),
        geometry={
            "width_m": width_m,
            "length_m": length_m,
        },
    ))

    # ── Roof ────────────────────────────────────────────────────────────────
    elements.append(DecomposedElement(
        type="Roof",
        label="roof",
        area_gross_m2=roof_slope_area_m2,
        area_net_m2=roof_slope_area_m2,
        perimeter_m=2.0 * (width_m + length_m),  # plan perimeter
        geometry={
            "width_m": width_m,
            "length_m": length_m,
            "roof_type": roof_type,
            "pitch_deg": roof_pitch_deg,
            "ridge_rise_m": round(ridge_rise_m, 4),
            "slope_area_m2": round(roof_slope_area_m2, 4),
        },
    ))

    # ── Walls ────────────────────────────────────────────────────────────────
    # N and S: long walls — simple rectangles (gable triangle is on E/W)
    for face in ("N", "S"):
        gross = length_m * wall_height_m
        face_openings = [o for o in openings if o.wall == face]
        net = gross - sum(o.area_m2 for o in face_openings)
        elements.append(DecomposedElement(
            type="ExternalWall",
            label=f"wall_{face}",
            area_gross_m2=round(gross, 4),
            area_net_m2=round(net, 4),
            perimeter_m=round(2.0 * (length_m + wall_height_m), 4),
            geometry={
                "face": face,
                "width_m": length_m,
                "height_m": wall_height_m,
                "gable_triangle_area_m2": 0.0,
            },
        ))

    # E and W: short/gable walls — rectangle + gable triangle for pitched roofs
    for face, total_h in (("E", e_wall_total_h), ("W", w_wall_total_h)):
        rect_area  = width_m * wall_height_m
        tri_area   = gable_triangle_area if roof_type == "duo_pitch" else (
            gable_triangle_area if face == "W" and roof_type == "mono_pitch" else 0.0
        )
        gross = rect_area + tri_area
        face_openings = [o for o in openings if o.wall == face]
        net = gross - sum(o.area_m2 for o in face_openings)
        elements.append(DecomposedElement(
            type="ExternalWall",
            label=f"wall_{face}",
            area_gross_m2=round(gross, 4),
            area_net_m2=round(net, 4),
            perimeter_m=round(2.0 * (width_m + total_h), 4),
            geometry={
                "face": face,
                "width_m": width_m,
                "height_m": wall_height_m,
                "total_height_m": round(total_h, 4),
                "gable_triangle_area_m2": round(tri_area, 4),
            },
        ))

    # ── Openings ─────────────────────────────────────────────────────────────
    for i, o in enumerate(openings):
        elements.append(DecomposedElement(
            type="Opening",
            label=f"opening_{o.type}_{i + 1}",
            area_gross_m2=round(o.area_m2, 4),
            area_net_m2=round(o.area_m2, 4),
            perimeter_m=round(2.0 * (o.width_m + o.height_m), 4),
            geometry={
                "wall": o.wall,
                "type": o.type,
                "width_m": o.width_m,
                "height_m": o.height_m,
                "sill_height_m": o.sill_height_m,
                "x_offset_m": o.x_offset_m,
                "shape": o.shape,
            },
        ))

    return elements


def total_external_area(elements: list[DecomposedElement]) -> dict:
    """Convenience summary: gross and net envelope area."""
    walls = [e for e in elements if e.type == "ExternalWall"]
    roof  = next((e for e in elements if e.type == "Roof"),  None)
    floor = next((e for e in elements if e.type == "Floor"), None)
    return {
        "wall_gross_m2":  round(sum(e.area_gross_m2 for e in walls), 3),
        "wall_net_m2":    round(sum(e.area_net_m2   for e in walls), 3),
        "roof_m2":        round(roof.area_gross_m2,  3) if roof  else 0.0,
        "floor_m2":       round(floor.area_gross_m2, 3) if floor else 0.0,
        "opening_count":  sum(1 for e in elements if e.type == "Opening"),
    }
