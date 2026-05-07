"""
Skill: Material Take-off

Takes a list of DecomposedElement objects (from element_decomposer) plus
BuildUpSpec definitions, and returns material quantity lines with waste-adjusted
order quantities and a rolled-up summary grouped by material.

Pure function — no database access. Material name strings match MaterialLibrary.name
for DB lookup in the API layer.

Layer types
───────────
  board       — sheathing, lining, decking (m2)
  insulation  — batts, quilt, PIR (m2)
  membrane    — VCL, breather, DPM (m2)
  cladding    — external skin (m2)
  framing     — studs, joists, rafters (lm = linear metres)
  plate       — sole/top plate, rim joist (lm)

Framing calculation
───────────────────
  Walls:  studs are vertical → count = ceil(span / spacing) + 1 end stud
          span = geometry["width_m"] (horizontal wall span)
          stud height = geometry["height_m"] (eaves height)
  Floor:  joists span width_m, spaced along length_m
  Roof:   rafters span the slope length, spaced along length_m
          slope length calculated from geometry pitch_deg and roof_type
"""
import math
from dataclasses import dataclass, field
from typing import Literal

from app.skills.element_decomposer import DecomposedElement

LayerType = Literal["board", "insulation", "membrane", "cladding", "framing", "plate"]


@dataclass
class LayerSpec:
    material_name: str
    layer_type: LayerType
    thickness_mm: float = 0.0
    spacing_mm: float = 0.0       # centres — required for framing and plate layers
    waste_factor: float = 1.05    # 1.05 = 5% cut waste


@dataclass
class BuildUpSpec:
    applies_to: str               # "ExternalWall", "Floor", or "Roof"
    name: str
    layers: list[LayerSpec] = field(default_factory=list)


@dataclass
class MaterialLine:
    element_label: str
    element_type: str
    material_name: str
    layer_type: str
    quantity_net: float           # before waste
    quantity: float               # order quantity (net × waste_factor)
    unit: str                     # "m2" or "lm"
    waste_factor: float
    notes: str = ""


class TakeoffError(ValueError):
    pass


# ── Per-element-type calculators ──────────────────────────────────────────────

def _area_line(
    element: DecomposedElement,
    layer: LayerSpec,
) -> MaterialLine:
    net = element.area_gross_m2
    return MaterialLine(
        element_label=element.label,
        element_type=element.type,
        material_name=layer.material_name,
        layer_type=layer.layer_type,
        quantity_net=round(net, 3),
        quantity=round(net * layer.waste_factor, 3),
        unit="m2",
        waste_factor=layer.waste_factor,
    )


def _wall_lines(element: DecomposedElement, layers: list[LayerSpec]) -> list[MaterialLine]:
    span_m = element.geometry["width_m"]   # horizontal wall span
    height_m = element.geometry["height_m"]  # eaves height
    lines: list[MaterialLine] = []

    for layer in layers:
        if layer.layer_type in ("board", "insulation", "membrane", "cladding"):
            lines.append(_area_line(element, layer))

        elif layer.layer_type == "framing":
            if layer.spacing_mm <= 0:
                raise TakeoffError(
                    f"Layer '{layer.material_name}': spacing_mm must be > 0 for framing."
                )
            stud_count = math.ceil(span_m / (layer.spacing_mm / 1000)) + 1
            net = stud_count * height_m
            lines.append(MaterialLine(
                element_label=element.label,
                element_type=element.type,
                material_name=layer.material_name,
                layer_type="framing",
                quantity_net=round(net, 3),
                quantity=round(net * layer.waste_factor, 3),
                unit="lm",
                waste_factor=layer.waste_factor,
                notes=f"{stud_count} studs × {height_m:.2f}m",
            ))

        elif layer.layer_type == "plate":
            # Top plate + sole plate
            net = 2 * span_m
            lines.append(MaterialLine(
                element_label=element.label,
                element_type=element.type,
                material_name=layer.material_name,
                layer_type="plate",
                quantity_net=round(net, 3),
                quantity=round(net * layer.waste_factor, 3),
                unit="lm",
                waste_factor=layer.waste_factor,
                notes="top + sole plate",
            ))

    return lines


def _floor_lines(element: DecomposedElement, layers: list[LayerSpec]) -> list[MaterialLine]:
    width_m = element.geometry["width_m"]
    length_m = element.geometry["length_m"]
    lines: list[MaterialLine] = []

    for layer in layers:
        if layer.layer_type in ("board", "insulation", "membrane", "cladding"):
            lines.append(_area_line(element, layer))

        elif layer.layer_type == "framing":
            if layer.spacing_mm <= 0:
                raise TakeoffError(
                    f"Layer '{layer.material_name}': spacing_mm must be > 0 for framing."
                )
            # Joists span width_m, spaced along length_m
            joist_count = math.ceil(length_m / (layer.spacing_mm / 1000)) + 1
            net = joist_count * width_m
            lines.append(MaterialLine(
                element_label=element.label,
                element_type=element.type,
                material_name=layer.material_name,
                layer_type="framing",
                quantity_net=round(net, 3),
                quantity=round(net * layer.waste_factor, 3),
                unit="lm",
                waste_factor=layer.waste_factor,
                notes=f"{joist_count} joists × {width_m:.2f}m",
            ))

        elif layer.layer_type == "plate":
            # Rim/header joists — perimeter of the floor cassette
            net = 2 * (width_m + length_m)
            lines.append(MaterialLine(
                element_label=element.label,
                element_type=element.type,
                material_name=layer.material_name,
                layer_type="plate",
                quantity_net=round(net, 3),
                quantity=round(net * layer.waste_factor, 3),
                unit="lm",
                waste_factor=layer.waste_factor,
                notes="rim/header joists (perimeter)",
            ))

    return lines


def _roof_lines(element: DecomposedElement, layers: list[LayerSpec]) -> list[MaterialLine]:
    geom = element.geometry
    width_m = geom["width_m"]
    length_m = geom["length_m"]
    roof_type = geom["roof_type"]
    pitch_deg = geom["pitch_deg"]
    pitch_rad = math.radians(pitch_deg)
    lines: list[MaterialLine] = []

    for layer in layers:
        if layer.layer_type in ("board", "insulation", "membrane", "cladding"):
            # area_gross_m2 is already the slope area
            lines.append(_area_line(element, layer))

        elif layer.layer_type == "framing":
            if layer.spacing_mm <= 0:
                raise TakeoffError(
                    f"Layer '{layer.material_name}': spacing_mm must be > 0 for framing."
                )
            spacing_m = layer.spacing_mm / 1000

            if roof_type == "duo_pitch":
                # Two slopes; rafters spaced along length_m, spanning half-width slope
                half_w = width_m / 2.0
                rafter_span = half_w / math.cos(pitch_rad) if pitch_deg > 0 else half_w
                count_per_side = math.ceil(length_m / spacing_m) + 1
                net = 2 * count_per_side * rafter_span
                notes = f"{count_per_side}×2 rafters × {rafter_span:.2f}m"

            elif roof_type == "mono_pitch":
                rafter_span = width_m / math.cos(pitch_rad) if pitch_deg > 0 else width_m
                count = math.ceil(length_m / spacing_m) + 1
                net = count * rafter_span
                notes = f"{count} rafters × {rafter_span:.2f}m"

            else:  # flat — flat roof joists span width, spaced along length
                count = math.ceil(length_m / spacing_m) + 1
                net = count * width_m
                notes = f"{count} joists × {width_m:.2f}m (flat)"

            lines.append(MaterialLine(
                element_label=element.label,
                element_type=element.type,
                material_name=layer.material_name,
                layer_type="framing",
                quantity_net=round(net, 3),
                quantity=round(net * layer.waste_factor, 3),
                unit="lm",
                waste_factor=layer.waste_factor,
                notes=notes,
            ))

        elif layer.layer_type == "plate":
            # Ridge + eaves wall plates (approximation: 2 × length)
            net = 2 * length_m
            lines.append(MaterialLine(
                element_label=element.label,
                element_type=element.type,
                material_name=layer.material_name,
                layer_type="plate",
                quantity_net=round(net, 3),
                quantity=round(net * layer.waste_factor, 3),
                unit="lm",
                waste_factor=layer.waste_factor,
                notes="ridge + eaves plates",
            ))

    return lines


# ── Public API ────────────────────────────────────────────────────────────────

def takeoff(
    elements: list[DecomposedElement],
    build_ups: list[BuildUpSpec],
) -> list[MaterialLine]:
    """
    Calculate material quantities for all elements.

    Parameters
    ----------
    elements   Output from decompose_pod().
    build_ups  One BuildUpSpec per element type you want to quantify.
               Types with no matching BuildUpSpec are silently skipped.

    Returns
    -------
    Flat list of MaterialLine — one per (element, layer) combination.
    Openings are skipped (their void is already reflected in area_gross_m2
    of the host wall, which is used for continuous layers).
    """
    build_up_map = {b.applies_to: b for b in build_ups}
    lines: list[MaterialLine] = []

    for element in elements:
        if element.type == "Opening":
            continue

        spec = build_up_map.get(element.type)
        if spec is None:
            continue

        if element.type == "ExternalWall":
            lines.extend(_wall_lines(element, spec.layers))
        elif element.type == "Floor":
            lines.extend(_floor_lines(element, spec.layers))
        elif element.type == "Roof":
            lines.extend(_roof_lines(element, spec.layers))

    return lines


def takeoff_summary(lines: list[MaterialLine]) -> dict:
    """
    Roll up lines by material name.

    Returns a dict with:
      line_count  — total number of lines
      materials   — list of {material, unit, quantity} dicts, sorted by material name
    """
    by_mat: dict[str, dict] = {}
    for line in lines:
        key = line.material_name
        if key not in by_mat:
            by_mat[key] = {"material": key, "unit": line.unit, "quantity": 0.0}
        by_mat[key]["quantity"] = round(by_mat[key]["quantity"] + line.quantity, 3)

    return {
        "line_count": len(lines),
        "materials": sorted(by_mat.values(), key=lambda x: x["material"]),
    }


# ── Default Nordic closed-panel build-ups ─────────────────────────────────────
# Material names match MaterialLibrary.name in the database.
# These defaults represent a standard insulated closed-panel Nordic pod:
#   Wall:  47×147 KVH at 600 c/c, mineral wool, OSB sheathing, spruce cladding
#   Floor: 47×195 KVH at 400 c/c, mineral wool, OSB deck
#   Roof:  47×195 KVH at 600 c/c, Paroc rafter insulation, OSB deck

NORDIC_WALL = BuildUpSpec(
    applies_to="ExternalWall",
    name="Nordic Closed-Panel Wall (47×147, 600 c/c)",
    layers=[
        LayerSpec("Latvian Spruce Feather-edge 21mm",    "cladding",   thickness_mm=21.0,  waste_factor=1.10),
        LayerSpec("Tyvek Housewrap Breather",            "membrane",   thickness_mm=0.5,   waste_factor=1.10),
        LayerSpec("OSB/3 12mm (Egger)",                  "board",      thickness_mm=12.0,  waste_factor=1.05),
        LayerSpec("KVH C24 47×147 (Latvian)",            "framing",    thickness_mm=147.0, spacing_mm=600, waste_factor=1.10),
        LayerSpec("KVH C24 47×147 (Latvian)",            "plate",      thickness_mm=147.0, waste_factor=1.10),
        LayerSpec("Rockwool Flexi 100",                  "insulation", thickness_mm=100.0, waste_factor=1.05),
        LayerSpec("Siga Majrex 200 VCL",                 "membrane",   thickness_mm=0.2,   waste_factor=1.10),
        LayerSpec("Gyproc Standard 12.5mm",              "board",      thickness_mm=12.5,  waste_factor=1.05),
    ],
)

NORDIC_FLOOR = BuildUpSpec(
    applies_to="Floor",
    name="Nordic Floor Cassette (47×195, 400 c/c)",
    layers=[
        LayerSpec("OSB/3 18mm floor (Egger)",            "board",      thickness_mm=18.0,  waste_factor=1.05),
        LayerSpec("KVH C24 47×195 (Latvian)",            "framing",    thickness_mm=195.0, spacing_mm=400, waste_factor=1.10),
        LayerSpec("KVH C24 47×195 (Latvian)",            "plate",      thickness_mm=195.0, waste_factor=1.10),
        LayerSpec("Rockwool Flexi 100",                  "insulation", thickness_mm=100.0, waste_factor=1.05),
        LayerSpec("Siga Majrex 200 VCL",                 "membrane",   thickness_mm=0.2,   waste_factor=1.10),
    ],
)

NORDIC_ROOF = BuildUpSpec(
    applies_to="Roof",
    name="Nordic Roof Cassette (47×195, 600 c/c)",
    layers=[
        LayerSpec("OSB/3 12mm (Egger)",                  "board",      thickness_mm=12.0,  waste_factor=1.05),
        LayerSpec("KVH C24 47×195 (Latvian)",            "framing",    thickness_mm=195.0, spacing_mm=600, waste_factor=1.10),
        LayerSpec("Paroc eXtra 100 (between-rafter)",    "insulation", thickness_mm=100.0, waste_factor=1.05),
        LayerSpec("Siga Majrex 200 VCL",                 "membrane",   thickness_mm=0.2,   waste_factor=1.10),
        LayerSpec("Gyproc Standard 12.5mm",              "board",      thickness_mm=12.5,  waste_factor=1.05),
    ],
)

# Convenience preset: wall + floor + roof for a standard Nordic pod
NORDIC_STANDARD = [NORDIC_WALL, NORDIC_FLOOR, NORDIC_ROOF]
