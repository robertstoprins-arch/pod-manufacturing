"""
Skill: MTO Resolver

Role-based material take-off. Dispatches each build-up layer to the correct
calculation method based on its role, producing MtoLine objects with raw quantity,
waste factor, and order quantity.

Methods
-------
board_area              — net area × waste
board_area_cladding     — net area × 1.12
membrane_area           — gross area × 1.10 (laps)
linear_vertical_centres — battens/studs at default spacing (lm)
framing_zone_split      — 2 output lines: C24 framing (lm) + insulation infill (m2)
"""
import math
from dataclasses import dataclass, field

# ── Role → method dispatch ────────────────────────────────────────────────────

ROLE_MTO_METHOD: dict[str, str] = {
    "internal_finish": "board_area",
    "sheathing":       "board_area",
    "insulation":      "board_area",
    "structure":       "board_area",
    "cladding":        "board_area_cladding",
    "external_finish": "board_area_cladding",
    "vcl":             "membrane_area",
    "breather":        "membrane_area",
    "airtight_layer":  "membrane_area",
    "framing_zone":    "framing_zone_split",
    "service_void":    "linear_vertical_centres",
    "cavity":          "linear_vertical_centres",
}

# Waste applied as: order_qty = raw × waste_factor
WASTE_BY_METHOD: dict[str, float] = {
    "board_area":              1.10,
    "board_area_cladding":     1.12,
    "membrane_area":           1.10,
    "linear_vertical_centres": 1.10,
    "framing_zone_timber":      1.10,
    "framing_zone_insulation":  1.08,
}

# Role overrides for insulation/concrete variants
WASTE_BY_ROLE: dict[str, float] = {
    "insulation": 1.08,   # PIR, EPS, mineral wool
    "structure":  1.03,   # concrete slab
}

DEFAULT_STUD_SPACING_M  = 0.600
DEFAULT_STUD_WIDTH_M    = 0.038   # 38mm face
DEFAULT_NOGGIN_ROWS     = 1
EXTRA_STUDS_PER_OPENING = 4


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class MtoInputLayer:
    name: str
    role: str
    thickness_mm: float
    framing_fraction: float = 0.15
    supplier_ref: str = ""
    properties: dict = field(default_factory=dict)


@dataclass
class WallGeometry:
    label: str           # "wall_N"
    length_m: float      # horizontal span of this wall face
    height_m: float      # eaves height (used for stud length)
    opening_count: int   # number of openings on this wall face
    gross_area_m2: float
    net_area_m2: float


@dataclass
class MtoLine:
    material_name: str
    role: str
    method: str
    raw_quantity: float
    waste_factor: float
    order_quantity: float
    unit: str             # "m2" | "lm"
    notes: str = ""


# ── Private helpers ───────────────────────────────────────────────────────────

def _is_concrete(layer: MtoInputLayer) -> bool:
    ref  = (layer.supplier_ref or "").upper()
    name = (layer.name or "").lower()
    return "CONCRETE" in ref or "concrete" in name


def _volume_from_area_thickness(area_m2: float, thickness_mm: float, waste: float) -> tuple[float, float]:
    thickness_m = thickness_mm / 1000.0
    raw   = round(area_m2 * thickness_m, 3)
    order = round(raw * waste, 3)
    return raw, order


def _waste(method: str, role: str) -> float:
    return WASTE_BY_ROLE.get(role, WASTE_BY_METHOD.get(method, 1.10))


def _studs_raw(length_m: float, height_m: float, opening_count: int) -> tuple[float, str]:
    base = math.floor(length_m / DEFAULT_STUD_SPACING_M) + 1
    extra = opening_count * EXTRA_STUDS_PER_OPENING
    total = base + extra
    raw = round(total * height_m, 3)
    note = f"{total} studs × {height_m}m"
    if extra:
        note += f" ({extra} extra for {opening_count} opening(s))"
    return raw, note


def _plates_raw(length_m: float) -> float:
    return round(length_m * 2.0, 3)   # top + bottom


def _noggins_raw(length_m: float) -> tuple[float, str]:
    stud_count = math.floor(length_m / DEFAULT_STUD_SPACING_M) + 1
    bay_count = max(stud_count - 1, 0)
    noggin_length = round(DEFAULT_STUD_SPACING_M - DEFAULT_STUD_WIDTH_M, 4)
    count = bay_count * DEFAULT_NOGGIN_ROWS
    raw = round(count * noggin_length, 3)
    return raw, f"{count} noggins × {noggin_length}m"


def _insulation_label(layer: MtoInputLayer) -> str:
    """Derive infill description: properties first, then layer name heuristic."""
    props_name = (layer.properties or {}).get("infill_name")
    if props_name:
        return props_name
    n = (layer.name or "").lower()
    if "pir" in n:
        return "PIR infill"
    if "mineral wool" in n or "rockwool" in n or "paroc" in n:
        return "Mineral wool infill"
    return "Insulation infill"


def _infill_supplier_ref(layer: MtoInputLayer) -> str:
    """Return the infill material supplier ref from properties or empty string."""
    return (layer.properties or {}).get("infill_material_ref", "")


def _framing_zone_split(layer: MtoInputLayer, walls: list[WallGeometry]) -> list[MtoLine]:
    """Produces 2 MtoLines: [0] C24 framing (lm), [1] insulation infill (m2)."""
    depth_m = layer.thickness_mm / 1000.0
    ff = max(layer.framing_fraction, 0.0) or 0.15

    total_studs = total_plates = total_noggins = 0.0
    for w in walls:
        s, _ = _studs_raw(w.length_m, w.height_m, w.opening_count)
        p    = _plates_raw(w.length_m)
        n, _ = _noggins_raw(w.length_m)
        total_studs   += s
        total_plates  += p
        total_noggins += n

    timber_raw   = round(total_studs + total_plates + total_noggins, 3)
    timber_order = round(timber_raw * 1.10, 3)
    vol_m3       = round(timber_raw * DEFAULT_STUD_WIDTH_M * depth_m, 4)

    total_net_m2  = sum(w.net_area_m2 for w in walls)
    infill_raw    = round(total_net_m2 * (1.0 - ff), 3)
    infill_order  = round(infill_raw * 1.08, 3)
    infill_pct    = round((1.0 - ff) * 100)
    infill_ref    = _infill_supplier_ref(layer)

    return [
        MtoLine(
            material_name=layer.name + " — C24 framing",
            role="framing_zone_timber",
            method="framing_zone_split_timber",
            raw_quantity=timber_raw,
            waste_factor=1.10,
            order_quantity=timber_order,
            unit="lm",
            notes=f"studs + plates + noggins; {vol_m3} m³ timber",
        ),
        MtoLine(
            material_name=layer.name + " — " + _insulation_label(layer),
            role="framing_zone_insulation",
            method="framing_zone_split_insulation",
            raw_quantity=infill_raw,
            waste_factor=1.08,
            order_quantity=infill_order,
            unit="m2",
            notes=f"net area × {infill_pct}% insulation fraction"
                  + (f"; ref: {infill_ref}" if infill_ref else ""),
        ),
    ]


# ── Public resolver ───────────────────────────────────────────────────────────

def resolve_mto(
    layers: list[MtoInputLayer],
    element_type: str,
    walls: list[WallGeometry],
    total_net_m2: float,
    total_gross_m2: float,
) -> list[MtoLine]:
    """
    Resolve MTO for a list of build-up layers.

    For ExternalWall: uses per-wall geometry for linear calculations.
    For Floor/Roof: framing_zone and linear roles fall back to board_area.
    """
    out: list[MtoLine] = []

    for layer in layers:

        # ── Concrete slab: volume override (before generic dispatch) ─────────
        if layer.role == "structure" and _is_concrete(layer):
            raw, order = _volume_from_area_thickness(total_net_m2, layer.thickness_mm, 1.03)
            out.append(MtoLine(
                material_name=layer.name,
                role=layer.role,
                method="volume_from_area_thickness",
                raw_quantity=raw,
                waste_factor=1.03,
                order_quantity=order,
                unit="m3",
                notes="area × thickness; concrete measured by volume",
            ))
            continue

        method = ROLE_MTO_METHOD.get(layer.role, "board_area")

        # ── Framing zone split (walls only) ──────────────────────────────────
        if method == "framing_zone_split" and element_type == "ExternalWall" and walls:
            out.extend(_framing_zone_split(layer, walls))

        # ── Membrane (gross area + laps) ─────────────────────────────────────
        elif method == "membrane_area":
            raw = round(total_gross_m2, 3)
            out.append(MtoLine(
                material_name=layer.name,
                role=layer.role,
                method=method,
                raw_quantity=raw,
                waste_factor=1.10,
                order_quantity=round(raw * 1.10, 3),
                unit="m2",
                notes="gross area + 10% laps",
            ))

        # ── Linear battens (walls only) ──────────────────────────────────────
        elif method == "linear_vertical_centres" and element_type == "ExternalWall" and walls:
            total_raw = 0.0
            for w in walls:
                count = math.floor(w.length_m / DEFAULT_STUD_SPACING_M) + 1
                total_raw += count * w.height_m
            total_raw = round(total_raw, 3)
            out.append(MtoLine(
                material_name=layer.name,
                role=layer.role,
                method=method,
                raw_quantity=total_raw,
                waste_factor=1.10,
                order_quantity=round(total_raw * 1.10, 3),
                unit="lm",
                notes=f"battens at {int(DEFAULT_STUD_SPACING_M * 1000)}mm centres",
            ))

        # ── Linear role on Roof — horizontal batten spacing ─────────────────
        elif method == "linear_vertical_centres" and element_type == "Roof":
            raw = round(total_net_m2 / DEFAULT_STUD_SPACING_M, 3)
            order = round(raw * 1.10, 3)
            out.append(MtoLine(
                material_name=layer.name,
                role=layer.role,
                method="linear_roof_battens",
                raw_quantity=raw,
                waste_factor=1.10,
                order_quantity=order,
                unit="lm",
                notes=f"roof area {total_net_m2:.1f} m² ÷ {int(DEFAULT_STUD_SPACING_M*1000)}mm spacing",
            ))

        # ── Linear role on other non-wall elements — area fallback ──────────
        elif method == "linear_vertical_centres":
            w = _waste("board_area", layer.role)
            raw = round(total_net_m2, 3)
            out.append(MtoLine(
                material_name=layer.name,
                role=layer.role,
                method="board_area",
                raw_quantity=raw,
                waste_factor=w,
                order_quantity=round(raw * w, 3),
                unit="m2",
                notes="linear MTO not applicable for this element type; area used as fallback",
            ))

        # ── Area (boards, insulation, cladding) ──────────────────────────────
        else:
            w = _waste(method, layer.role)
            raw = round(total_net_m2, 3)
            out.append(MtoLine(
                material_name=layer.name,
                role=layer.role,
                method=method,
                raw_quantity=raw,
                waste_factor=w,
                order_quantity=round(raw * w, 3),
                unit="m2",
            ))

    # ── Method/unit consistency guard ────────────────────────────────────────
    for line in out:
        if line.method == "volume_from_area_thickness" and line.unit != "m3":
            raise ValueError("volume_from_area_thickness must use unit m3")
        if "linear" in line.method and "fallback" not in line.notes and line.unit != "lm":
            raise ValueError(f"Invalid MTO output: {line.method} must use lm, got {line.unit}")
        if line.method in {"board_area", "board_area_cladding", "membrane_area"} and line.unit != "m2":
            raise ValueError(f"Invalid MTO output: {line.method} must use m2, got {line.unit}")

    return out
