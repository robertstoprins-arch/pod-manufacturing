"""
Seed 9 pre-made library build-ups: Standard / Enhanced / Light × Wall / Floor / Roof.

Run from the backend/ directory:
    python seeds/standard_build_ups.py

Idempotent — skips any build-up whose name already exists.
Requires standard materials to be seeded first:
    python seeds/standard_materials.py

Layer convention: INSIDE → OUTSIDE (position_order 1 = innermost warm layer).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db import engine
from app.models import BuildUp, BuildUpLayer, MaterialLibrary

# ── Notes per tier ────────────────────────────────────────────────────────────

_NOTE_STANDARD_WALL = (
    "Preliminary U-value profile target passed for BBR (SE) and TEK17 (NO) reference values. "
    "Suitable as a starting point for habitable pod design, subject to project-specific "
    "architect/engineer review and local professional approval. "
    "Simplified thermal calculation only — junctions, airtightness, and openings not included."
)

_NOTE_HYBRID_WALL = (
    "Cost-optimised standard wall. Mineral wool batts fill the stud zone (C24 @ 600 c/c) with "
    "a continuous PIR outboard layer to cut thermal bridging. Target U-value ≈ 0.159 W/m²K — "
    "passes BBR (SE) ≤ 0.18 and TEK17 (NO) ≤ 0.18 reference values. Suitable as a production "
    "default for habitable pod design, subject to project-specific architect/engineer review. "
    "Simplified thermal calculation — junctions, airtightness, and openings not included."
)

_NOTE_ENHANCED_WALL = (
    "High-performance all-PIR envelope. Continuous PIR outboard + PIR-filled stud zone delivers "
    "maximum thermal resistance in a compact wall depth. Intended as a premium / passive-house-"
    "direction option. Final performance depends on junctions, openings, airtightness, and "
    "whole-building PHPP or equivalent review. Preliminary — for professional review only."
)

_NOTE_LIGHT = (
    "Lightweight build-up for garden office, storage, or seasonal/non-habitable use only. "
    "Does not meet standard BBR/TEK17 U-value profile targets. Not suitable for habitable "
    "residential use without review, upgrade, and professional sign-off. "
    "Ground floor losses and perimeter effects (floor) / waterproofing and roof covering (roof) "
    "are not represented in this simplified thermal build-up."
)

_NOTE_STANDARD_FLOOR = (
    "Preliminary U-value passed for BBR (SE) reference values (≤0.15 W/m²K). "
    "Does not meet TEK17 (NO) floor target of ≤0.10 W/m²K — additional insulation required "
    "for Norwegian projects. Subject to project-specific engineer review and local professional "
    "approval. Simplified thermal calculation only — ground losses and edge effects not included."
)

_NOTE_ENHANCED_FLOOR = (
    "High-performance floor build-up meeting both BBR (SE) and TEK17 (NO) reference targets. "
    "Intended as a design starting point for low-energy or passive-house-direction projects. "
    "Final performance depends on ground conditions, edge insulation, and perimeter detailing. "
    "Preliminary — for professional review only."
)

_NOTE_STANDARD_ROOF = (
    "Preliminary U-value profile target passed for BBR (SE) and TEK17 (NO) reference values. "
    "Suitable as a starting point for habitable pod roof design, subject to project-specific "
    "architect/engineer review and local professional approval. "
    "Simplified thermal calculation only — junctions, airtightness, and roof coverings not included."
)

_NOTE_ENHANCED_ROOF = (
    "High-performance roof build-up with additional insulation headroom toward a low-energy "
    "specification. Intended as a design starting point for low-energy or passive-house-direction "
    "projects. Final performance depends on junctions, roof coverings, airtightness, and "
    "ventilation strategy. Preliminary — for professional review only."
)

# ── Build-up definitions ──────────────────────────────────────────────────────
# build_up_type is temporarily used as performance tier (standard/enhanced/light).
# TODO: replace with performance_tier field

BUILD_UPS = [
    # ── Walls ─────────────────────────────────────────────────────────────────
    {
        "name": "Nordic Standard Hybrid Wall — Closed Panel",
        "element_type": "ExternalWall",
        "build_up_type": "standard",
        "scope": "library",
        "status": "approved",
        "notes": _NOTE_HYBRID_WALL,
        "layers": [
            {"supplier_ref": "SGG-GYPROC-12.5",         "thickness_mm": 12.5,  "role": "internal_finish", "framing_fraction": 0.0,  "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "GENERIC-SVC-VOID-50",      "thickness_mm": 50.0,  "role": "service_void",    "framing_fraction": 0.0,  "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-VCL-STANDARD",     "thickness_mm": 0.2,   "role": "vcl",             "framing_fraction": 0.0,  "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-OSB3-11",          "thickness_mm": 11.0,  "role": "sheathing",       "framing_fraction": 0.0,  "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "GENERIC-C24-MW-140",       "thickness_mm": 140.0, "role": "framing_zone",    "framing_fraction": 0.15, "include_in_u_value": True,  "sd_value_m": None, "infill_type": "mineral_wool", "infill_lambda_W_mK": 0.034, "infill_material_ref": "GENERIC-MW-FRAMING-140", "infill_name": "Mineral Wool Infill"},
            {"supplier_ref": "GENERIC-PIR-OUTBOARD-100", "thickness_mm": 100.0, "role": "insulation",      "framing_fraction": 0.0,  "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "DUPONT-TYVEK-HOUSEWRAP",   "thickness_mm": 0.2,   "role": "breather",        "framing_fraction": 0.0,  "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-VENT-CAVITY-25",   "thickness_mm": 25.0,  "role": "cavity",          "framing_fraction": 0.0,  "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-FC-CLADDING-12",   "thickness_mm": 12.0,  "role": "cladding",        "framing_fraction": 0.0,  "include_in_u_value": True,  "sd_value_m": None},
        ],
    },
    {
        "name": "Nordic Standard Wall — Closed Panel",
        "element_type": "ExternalWall",
        "build_up_type": "standard",
        "scope": "library",
        "status": "approved",
        "notes": _NOTE_STANDARD_WALL,
        "layers": [
            {"supplier_ref": "SGG-GYPROC-12.5",         "thickness_mm": 12.5,  "role": "internal_finish", "framing_fraction": 0.0,  "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "GENERIC-SVC-VOID-50",      "thickness_mm": 50.0,  "role": "service_void",    "framing_fraction": 0.0,  "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-VCL-STANDARD",     "thickness_mm": 0.2,   "role": "vcl",             "framing_fraction": 0.0,  "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-OSB3-11",          "thickness_mm": 11.0,  "role": "sheathing",       "framing_fraction": 0.0,  "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "GENERIC-C24-PIR-140",      "thickness_mm": 140.0, "role": "framing_zone",    "framing_fraction": 0.15, "include_in_u_value": True,  "sd_value_m": None, "infill_material_ref": "GENERIC-PIR-FRAMING-140", "infill_name": "PIR Infill", "infill_type": "pir", "infill_lambda_W_mK": 0.023},
            {"supplier_ref": "GENERIC-PIR-OUTBOARD-50",  "thickness_mm": 50.0,  "role": "insulation",      "framing_fraction": 0.0,  "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "DUPONT-TYVEK-HOUSEWRAP",   "thickness_mm": 0.2,   "role": "breather",        "framing_fraction": 0.0,  "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-VENT-CAVITY-25",   "thickness_mm": 25.0,  "role": "cavity",          "framing_fraction": 0.0,  "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-FC-CLADDING-12",   "thickness_mm": 12.0,  "role": "cladding",        "framing_fraction": 0.0,  "include_in_u_value": True,  "sd_value_m": None},
        ],
    },
    {
        "name": "Nordic Enhanced PIR Wall — Closed Panel",
        "element_type": "ExternalWall",
        "build_up_type": "enhanced",
        "scope": "library",
        "status": "approved",
        "notes": _NOTE_ENHANCED_WALL,
        "layers": [
            {"supplier_ref": "SGG-GYPROC-12.5",         "thickness_mm": 12.5,  "role": "internal_finish", "framing_fraction": 0.0,  "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "GENERIC-SVC-VOID-50",      "thickness_mm": 50.0,  "role": "service_void",    "framing_fraction": 0.0,  "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "PROCLIMA-INTELLO-PLUS",    "thickness_mm": 0.2,   "role": "vcl",             "framing_fraction": 0.0,  "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-OSB3-11",          "thickness_mm": 11.0,  "role": "sheathing",       "framing_fraction": 0.0,  "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "GENERIC-C24-PIR-140",      "thickness_mm": 140.0, "role": "framing_zone",    "framing_fraction": 0.15, "include_in_u_value": True,  "sd_value_m": None, "infill_material_ref": "GENERIC-PIR-FRAMING-140", "infill_name": "PIR Infill", "infill_type": "pir", "infill_lambda_W_mK": 0.023},
            {"supplier_ref": "GENERIC-PIR-OUTBOARD-100", "thickness_mm": 100.0, "role": "insulation",      "framing_fraction": 0.0,  "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "DUPONT-TYVEK-HOUSEWRAP",   "thickness_mm": 0.2,   "role": "breather",        "framing_fraction": 0.0,  "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-VENT-CAVITY-25",   "thickness_mm": 25.0,  "role": "cavity",          "framing_fraction": 0.0,  "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-FC-CLADDING-12",   "thickness_mm": 12.0,  "role": "cladding",        "framing_fraction": 0.0,  "include_in_u_value": True,  "sd_value_m": None},
        ],
    },
    {
        "name": "Light Wall — Garden / Storage",
        "element_type": "ExternalWall",
        "build_up_type": "light",
        "scope": "library",
        "status": "approved",
        "notes": _NOTE_LIGHT,
        "layers": [
            {"supplier_ref": "SGG-GYPROC-12.5",         "thickness_mm": 12.5, "role": "internal_finish", "framing_fraction": 0.0,  "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "GENERIC-VCL-STANDARD",     "thickness_mm": 0.2,  "role": "vcl",             "framing_fraction": 0.0,  "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-OSB3-11",          "thickness_mm": 11.0, "role": "sheathing",       "framing_fraction": 0.0,  "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "GENERIC-C24-PIR-140",      "thickness_mm": 89.0, "role": "framing_zone",    "framing_fraction": 0.15, "include_in_u_value": True,  "sd_value_m": None, "infill_material_ref": "GENERIC-PIR-FRAMING-140", "infill_name": "PIR Infill", "infill_type": "pir", "infill_lambda_W_mK": 0.023},
            {"supplier_ref": "DUPONT-TYVEK-HOUSEWRAP",   "thickness_mm": 0.2,  "role": "breather",        "framing_fraction": 0.0,  "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-VENT-CAVITY-25",   "thickness_mm": 25.0, "role": "cavity",          "framing_fraction": 0.0,  "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-FC-CLADDING-12",   "thickness_mm": 12.0, "role": "cladding",        "framing_fraction": 0.0,  "include_in_u_value": True,  "sd_value_m": None},
        ],
    },
    # ── Floors ────────────────────────────────────────────────────────────────
    {
        "name": "Standard Floor — Slab + EPS",
        "element_type": "Floor",
        "build_up_type": "standard",   # TODO: replace with performance_tier field
        "scope": "library",
        "status": "approved",
        "notes": _NOTE_STANDARD_FLOOR,
        "layers": [
            {"supplier_ref": "GENERIC-CONCRETE-SLAB-150", "thickness_mm": 150.0, "role": "structure",   "framing_fraction": 0.0, "include_in_u_value": True, "sd_value_m": None},
            {"supplier_ref": "GENERIC-EPS-FLOOR-150",     "thickness_mm": 250.0, "role": "insulation",  "framing_fraction": 0.0, "include_in_u_value": True, "sd_value_m": None},
        ],
    },
    {
        "name": "Enhanced Floor — Slab + EPS / PIR",
        "element_type": "Floor",
        "build_up_type": "enhanced",   # TODO: replace with performance_tier field
        "scope": "library",
        "status": "approved",
        "notes": _NOTE_ENHANCED_FLOOR,
        "layers": [
            {"supplier_ref": "GENERIC-CONCRETE-SLAB-150", "thickness_mm": 150.0, "role": "structure",   "framing_fraction": 0.0, "include_in_u_value": True, "sd_value_m": None},
            {"supplier_ref": "GENERIC-EPS-FLOOR-150",     "thickness_mm": 300.0, "role": "insulation",  "framing_fraction": 0.0, "include_in_u_value": True, "sd_value_m": None},
            {"supplier_ref": "GENERIC-PIR-OUTBOARD-50",   "thickness_mm": 50.0,  "role": "insulation",  "framing_fraction": 0.0, "include_in_u_value": True, "sd_value_m": None},
        ],
    },
    {
        "name": "Light Floor — Garden / Storage",
        "element_type": "Floor",
        "build_up_type": "light",      # TODO: replace with performance_tier field
        "scope": "library",
        "status": "approved",
        "notes": _NOTE_LIGHT,
        "layers": [
            {"supplier_ref": "GENERIC-CONCRETE-SLAB-150", "thickness_mm": 150.0, "role": "structure",   "framing_fraction": 0.0, "include_in_u_value": True, "sd_value_m": None},
            {"supplier_ref": "GENERIC-EPS-FLOOR-150",     "thickness_mm": 100.0, "role": "insulation",  "framing_fraction": 0.0, "include_in_u_value": True, "sd_value_m": None},
        ],
    },
    # ── Roofs ─────────────────────────────────────────────────────────────────
    {
        "name": "Standard Roof — Mineral Wool",
        "element_type": "Roof",
        "build_up_type": "standard",
        "scope": "library",
        "status": "approved",
        "notes": _NOTE_STANDARD_ROOF,
        "layers": [
            {"supplier_ref": "SGG-GYPROC-12.5",       "thickness_mm": 12.5,  "role": "internal_finish", "framing_fraction": 0.0, "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "GENERIC-SVC-VOID-50",    "thickness_mm": 50.0,  "role": "service_void",    "framing_fraction": 0.0, "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-VCL-STANDARD",   "thickness_mm": 0.2,   "role": "vcl",             "framing_fraction": 0.0, "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-OSB3-11",        "thickness_mm": 11.0,  "role": "sheathing",       "framing_fraction": 0.0, "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "GENERIC-MW-ROOF-300",    "thickness_mm": 300.0, "role": "insulation",      "framing_fraction": 0.0, "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "DUPONT-TYVEK-HOUSEWRAP", "thickness_mm": 0.2,   "role": "breather",        "framing_fraction": 0.0, "include_in_u_value": False, "sd_value_m": None},
        ],
    },
    {
        "name": "Enhanced Roof — Mineral Wool",
        "element_type": "Roof",
        "build_up_type": "enhanced",
        "scope": "library",
        "status": "approved",
        "notes": _NOTE_ENHANCED_ROOF,
        "layers": [
            {"supplier_ref": "SGG-GYPROC-12.5",       "thickness_mm": 12.5,  "role": "internal_finish", "framing_fraction": 0.0, "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "GENERIC-SVC-VOID-50",    "thickness_mm": 50.0,  "role": "service_void",    "framing_fraction": 0.0, "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "PROCLIMA-INTELLO-PLUS",  "thickness_mm": 0.2,   "role": "vcl",             "framing_fraction": 0.0, "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-OSB3-11",        "thickness_mm": 11.0,  "role": "sheathing",       "framing_fraction": 0.0, "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "GENERIC-MW-ROOF-300",    "thickness_mm": 400.0, "role": "insulation",      "framing_fraction": 0.0, "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "DUPONT-TYVEK-HOUSEWRAP", "thickness_mm": 0.2,   "role": "breather",        "framing_fraction": 0.0, "include_in_u_value": False, "sd_value_m": None},
        ],
    },
    {
        "name": "Light Roof — Garden / Storage",
        "element_type": "Roof",
        "build_up_type": "light",
        "scope": "library",
        "status": "approved",
        "notes": _NOTE_LIGHT,
        "layers": [
            {"supplier_ref": "SGG-GYPROC-12.5",       "thickness_mm": 12.5,  "role": "internal_finish", "framing_fraction": 0.0, "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "GENERIC-VCL-STANDARD",   "thickness_mm": 0.2,   "role": "vcl",             "framing_fraction": 0.0, "include_in_u_value": False, "sd_value_m": None},
            {"supplier_ref": "GENERIC-OSB3-11",        "thickness_mm": 11.0,  "role": "sheathing",       "framing_fraction": 0.0, "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "GENERIC-MW-ROOF-300",    "thickness_mm": 150.0, "role": "insulation",      "framing_fraction": 0.0, "include_in_u_value": True,  "sd_value_m": None},
            {"supplier_ref": "DUPONT-TYVEK-HOUSEWRAP", "thickness_mm": 0.2,   "role": "breather",        "framing_fraction": 0.0, "include_in_u_value": False, "sd_value_m": None},
        ],
    },
]


# ── Core seed function ────────────────────────────────────────────────────────

def seed(db: Session) -> tuple[int, int]:
    """Seed standard build-ups into an open session. Caller is responsible for commit."""
    mat_by_ref: dict[str, MaterialLibrary] = {
        m.supplier_ref: m
        for m in db.query(MaterialLibrary).all()
        if m.supplier_ref
    }

    seeded = 0
    skipped = 0

    for defn in BUILD_UPS:
        existing = db.query(BuildUp).filter_by(name=defn["name"]).first()
        if existing:
            skipped += 1
            continue

        # Validate all required materials are present before inserting
        for layer_def in defn["layers"]:
            ref = layer_def["supplier_ref"]
            if ref not in mat_by_ref:
                raise RuntimeError(
                    f"ERROR: Material '{ref}' not found in material_library.\n"
                    "Run: python seeds/standard_materials.py"
                )

        bu = BuildUp(
            name=defn["name"],
            element_type=defn["element_type"],
            build_up_type=defn["build_up_type"],
            scope=defn["scope"],
            status=defn["status"],
            notes=defn["notes"],
        )
        db.add(bu)
        db.flush()

        for pos, layer_def in enumerate(defn["layers"], start=1):
            mat = mat_by_ref[layer_def["supplier_ref"]]
            props = {
                "role": layer_def["role"],
                "framing_fraction": layer_def["framing_fraction"],
                "include_in_u_value": layer_def["include_in_u_value"],
                "sd_value_m": layer_def["sd_value_m"],
            }
            for key in ("infill_type", "infill_lambda_W_mK", "infill_material_ref", "infill_name"):
                if key in layer_def:
                    props[key] = layer_def[key]
            db.add(BuildUpLayer(
                build_up_id=bu.id,
                material_id=mat.id,
                thickness_mm=layer_def["thickness_mm"],
                position_order=pos,
                properties=props,
            ))

        seeded += 1

    return seeded, skipped


# ── Entry point ───────────────────────────────────────────────────────────────

def run() -> None:
    with Session(engine) as db:
        seeded, skipped = seed(db)
        db.commit()
        print(f"Build-ups: seeded {seeded}, skipped {skipped} (already present).")


if __name__ == "__main__":
    run()
