"""
One-time production data correction script.

Fixes data that was seeded before the following issues were resolved:
  1. Service void price stored as m2 (8.00) — now corrected to lm (0.90)
  2. Standard/light build-ups used Intello Plus VCL — now use GENERIC-VCL-STANDARD
  3. Hybrid wall used PIR-OUTBOARD-50 at 70mm — now uses PIR-OUTBOARD-100 at 100mm
  4. Enhanced wall used PIR-OUTBOARD-50 at 100mm — now uses PIR-OUTBOARD-100 at 100mm
  5. Standard/enhanced walls had no infill_material_ref — now added
  6. EPS floor price stored at 14.00/m2 — corrected to 8.00/m2 (100mm basis for scaling)
  7. C24 timber price unit was "m" — corrected to "lm" to match mto_resolver output
  8. Batten prices were "m" — corrected to "lm"

Safe to run multiple times (idempotent).

Run from backend/:
    python seeds/correct_production.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import MaterialLibrary, MaterialPrice, BuildUp, BuildUpLayer

# ── Helpers ───────────────────────────────────────────────────────────────────

def _mat(db: Session, ref: str) -> MaterialLibrary | None:
    return db.query(MaterialLibrary).filter(MaterialLibrary.supplier_ref == ref).first()


def _upsert_price(
    db: Session,
    mat: MaterialLibrary,
    unit: str,
    price: float,
    currency: str,
    notes: str,
) -> str:
    """
    Ensure material has exactly one default import_benchmark price for this unit.
    Clears any existing import_benchmark price for this unit first, then creates a fresh one.
    Returns "updated" | "created".
    """
    existing = [
        p for p in mat.prices
        if p.price_type == "import_benchmark" and p.unit == unit
    ]
    for p in existing:
        db.delete(p)
    db.flush()
    db.add(MaterialPrice(
        material_id=mat.id,
        price_type="import_benchmark",
        price_per_unit=price,
        unit=unit,
        currency=currency,
        notes=notes,
        is_default=True,
    ))
    return "updated" if existing else "created"


def _add_material_if_missing(db: Session, defn: dict) -> tuple[MaterialLibrary, str]:
    """Insert material if supplier_ref not already present. Returns (mat, status)."""
    mat = _mat(db, defn["supplier_ref"])
    if mat:
        return mat, "exists"
    from app.models import LibraryVersion
    lv = db.get(LibraryVersion, 1)
    if lv is None:
        lv = LibraryVersion(id=1, version="v1.0", notes="Standard material library")
        db.add(lv)
        db.flush()
    mat = MaterialLibrary(library_version_id=lv.id, **defn)
    db.add(mat)
    db.flush()
    return mat, "created"


# ── Material definitions for new materials ────────────────────────────────────

NEW_MATERIALS = [
    {
        "name": "Standard Polythene VCL (0.2mm)",
        "manufacturer": None,
        "lambda_W_mK": 0.17,
        "density_kg_m3": None,
        "supplier_ref": "GENERIC-VCL-STANDARD",
        "unit": "m2",
        "properties": {
            "category": "vcl",
            "default_role": "vcl",
            "default_thickness_mm": 0.2,
            "include_in_u_value": False,
            "sd_value_m": 50.0,
        },
    },
    {
        "name": "PIR Insulation Board (Outboard, 100mm)",
        "manufacturer": None,
        "lambda_W_mK": 0.023,
        "density_kg_m3": 32.0,
        "supplier_ref": "GENERIC-PIR-OUTBOARD-100",
        "unit": "m2",
        "properties": {
            "category": "insulation",
            "default_role": "insulation",
            "default_thickness_mm": 100.0,
            "include_in_u_value": True,
            "sd_value_m": 100.0,
        },
    },
]

# ── Price corrections ─────────────────────────────────────────────────────────
# (supplier_ref, unit, price, currency, notes)
PRICE_CORRECTIONS = [
    # Service void: was 8.00 m2, corrected to 0.90 lm (matches mto_resolver lm output)
    ("GENERIC-SVC-VOID-50",          "lm",  0.90,  "EUR", "25×50 service void batten per lm, indicative — corrected from m2"),
    # EPS floor: was 14.00 m2, corrected to 8.00 m2 at 100mm basis (BOM scales by thickness)
    ("GENERIC-EPS-FLOOR-150",        "m2",  8.00,  "EUR", "EPS floor insulation, 100mm basis (BOM scales by thickness)"),
    # C24 timber: was 3.50 m, corrected to 3.50 lm (matches mto_resolver lm output)
    ("GENERIC-C24-TIMBER",           "lm",  3.50,  "EUR", "C24 structural timber per lm, trade supply"),
    # Battens: were "m", corrected to "lm"
    ("GENERIC-BATTEN-25X50",         "lm",  0.80,  "EUR", "25×50 treated batten per lm, trade supply"),
    ("GENERIC-COUNTER-BATTEN-38X50", "lm",  1.20,  "EUR", "38×50 treated counter-batten per lm, trade supply"),
    # New materials
    ("GENERIC-VCL-STANDARD",         "m2",  1.50,  "EUR", "Standard 0.2mm polythene VCL, trade supply"),
    ("GENERIC-PIR-OUTBOARD-100",     "m2",  32.00, "EUR", "PIR board 100mm outboard, trade supply"),
]

# ── Build-up layer corrections ────────────────────────────────────────────────
# For each build-up name, which layer changes to apply.
# Changes are applied by matching the current material supplier_ref on the layer.

BUILDUPS_VCL_TO_STANDARD = [
    "Nordic Standard Hybrid Wall — Closed Panel",
    "Nordic Standard Wall — Closed Panel",
    "Light Wall — Garden / Storage",
    "Standard Roof — Mineral Wool",
    "Light Roof — Garden / Storage",
]

BUILDUPS_PIR_OUTBOARD_TO_100 = [
    # (build_up_name, old_ref, old_thickness_mm, new_ref, new_thickness_mm)
    ("Nordic Standard Hybrid Wall — Closed Panel", "GENERIC-PIR-OUTBOARD-50", 70.0,  "GENERIC-PIR-OUTBOARD-100", 100.0),
    ("Nordic Enhanced PIR Wall — Closed Panel",    "GENERIC-PIR-OUTBOARD-50", 100.0, "GENERIC-PIR-OUTBOARD-100", 100.0),
]

# Build-ups that need infill_material_ref added to their framing zone layer
BUILDUPS_ADD_INFILL_REF = [
    # (build_up_name, zone_mat_ref, infill_ref, infill_name, infill_type, infill_lambda)
    ("Nordic Standard Wall — Closed Panel",    "GENERIC-C24-PIR-140", "GENERIC-PIR-FRAMING-140", "PIR Infill",          "pir",          0.023),
    ("Nordic Enhanced PIR Wall — Closed Panel","GENERIC-C24-PIR-140", "GENERIC-PIR-FRAMING-140", "PIR Infill",          "pir",          0.023),
    ("Light Wall — Garden / Storage",          "GENERIC-C24-PIR-140", "GENERIC-PIR-FRAMING-140", "PIR Infill",          "pir",          0.023),
]


def run():
    db = SessionLocal()
    try:
        log = []

        # 1. Ensure new materials exist
        for defn in NEW_MATERIALS:
            mat, status = _add_material_if_missing(db, defn)
            log.append(f"  Material {defn['supplier_ref']}: {status}")
        db.flush()

        # 2. Apply price corrections
        for ref, unit, price, currency, notes in PRICE_CORRECTIONS:
            mat = _mat(db, ref)
            if mat is None:
                log.append(f"  WARN: material '{ref}' not found — price correction skipped")
                continue
            status = _upsert_price(db, mat, unit, price, currency, notes)
            log.append(f"  Price {ref} ({unit}): {status} ->{price} {currency}")
        db.flush()

        # 3. Swap Intello Plus VCL ->Standard VCL in standard/light build-ups
        vcl_std = _mat(db, "GENERIC-VCL-STANDARD")
        intello  = _mat(db, "PROCLIMA-INTELLO-PLUS")
        if vcl_std and intello:
            for bu_name in BUILDUPS_VCL_TO_STANDARD:
                bu = db.query(BuildUp).filter(BuildUp.name == bu_name).first()
                if bu is None:
                    log.append(f"  WARN: build-up '{bu_name}' not found — VCL swap skipped")
                    continue
                changed = 0
                for layer in bu.layers:
                    if layer.material_id == intello.id:
                        layer.material_id = vcl_std.id
                        changed += 1
                log.append(
                    f"  Build-up '{bu_name}': swapped {changed} VCL layer(s) "
                    f"Intello Plus ->Standard VCL"
                )
        else:
            log.append("  WARN: VCL swap skipped — GENERIC-VCL-STANDARD or PROCLIMA-INTELLO-PLUS not found")

        # 4. Swap PIR outboard thickness/ref in hybrid+enhanced walls
        for bu_name, old_ref, old_mm, new_ref, new_mm in BUILDUPS_PIR_OUTBOARD_TO_100:
            bu = db.query(BuildUp).filter(BuildUp.name == bu_name).first()
            if bu is None:
                log.append(f"  WARN: build-up '{bu_name}' not found — PIR swap skipped")
                continue
            old_mat = _mat(db, old_ref)
            new_mat = _mat(db, new_ref)
            if old_mat is None or new_mat is None:
                log.append(
                    f"  WARN: '{bu_name}' PIR swap skipped — "
                    f"material {old_ref!r} or {new_ref!r} not found"
                )
                continue
            changed = 0
            for layer in bu.layers:
                if layer.material_id == old_mat.id and abs(layer.thickness_mm - old_mm) < 0.5:
                    layer.material_id = new_mat.id
                    layer.thickness_mm = new_mm
                    changed += 1
            log.append(
                f"  Build-up '{bu_name}': updated {changed} PIR layer(s) "
                f"{old_ref} {old_mm:.0f}mm ->{new_ref} {new_mm:.0f}mm"
            )

        # 5. Add infill_material_ref to framing zone layers where missing
        for bu_name, zone_ref, infill_ref, infill_name, infill_type, infill_lambda in BUILDUPS_ADD_INFILL_REF:
            bu = db.query(BuildUp).filter(BuildUp.name == bu_name).first()
            if bu is None:
                log.append(f"  WARN: build-up '{bu_name}' not found — infill ref skipped")
                continue
            zone_mat = _mat(db, zone_ref)
            if zone_mat is None:
                log.append(f"  WARN: zone material '{zone_ref}' not found — infill ref skipped")
                continue
            changed = 0
            for layer in bu.layers:
                if layer.material_id == zone_mat.id:
                    props = dict(layer.properties or {})
                    if "infill_material_ref" not in props:
                        props["infill_material_ref"] = infill_ref
                        props["infill_name"]         = infill_name
                        props["infill_type"]         = infill_type
                        props["infill_lambda_W_mK"]  = infill_lambda
                        layer.properties = props
                        changed += 1
            log.append(
                f"  Build-up '{bu_name}': added infill_material_ref to "
                f"{changed} framing zone layer(s)"
            )

        db.commit()
        print("Production correction complete:")
        for line in log:
            print(line)

    except Exception as e:
        db.rollback()
        print(f"ERROR — rolled back: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
