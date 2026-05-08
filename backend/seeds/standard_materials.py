"""
Seed standard building materials into material_library.

Run from the backend/ directory:
    python seeds/standard_materials.py

Idempotent — skips any row whose supplier_ref already exists.
Ensures a LibraryVersion with id=1 exists before inserting.

Layer convention: INSIDE → OUTSIDE.
include_in_u_value=False means the layer exists for validation or MTO
but is excluded from the thermal resistance calculation path.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db import engine
from app.models import LibraryVersion, MaterialLibrary

# ── Material definitions ──────────────────────────────────────────────────────
# Properties dict carries: default_role, default_thickness_mm, include_in_u_value,
# sd_value_m (vapour diffusion resistance, metres), category.
MATERIALS: list[dict] = [
    # 1. Internal finish
    {
        "name": "Gyproc Standard Plasterboard",
        "manufacturer": "Saint-Gobain",
        "lambda_W_mK": 0.25,
        "density_kg_m3": 800.0,
        "supplier_ref": "SGG-GYPROC-12.5",
        "spec_ref": "EN 520",
        "unit": "m2",
        "properties": {
            "category": "internal_finish",
            "default_role": "internal_finish",
            "default_thickness_mm": 12.5,
            "include_in_u_value": True,
            "sd_value_m": None,
        },
    },
    # 2. Service void — MTO only, not in U-value path
    {
        "name": "Service Void (Battens 25×50 @ 600cc)",
        "manufacturer": None,
        "lambda_W_mK": 0.34,      # timber; excluded from U-value anyway
        "density_kg_m3": 450.0,
        "supplier_ref": "GENERIC-SVC-VOID-50",
        "unit": "m2",
        "properties": {
            "category": "service_void",
            "default_role": "service_void",
            "default_thickness_mm": 50.0,
            "include_in_u_value": False,    # MTO only
            "sd_value_m": None,
        },
    },
    # 3. VCL — validation only
    {
        "name": "Intello Plus VCL",
        "manufacturer": "Pro Clima",
        "lambda_W_mK": 0.17,
        "density_kg_m3": None,
        "supplier_ref": "PROCLIMA-INTELLO-PLUS",
        "spec_ref": "ETA-07/0274",
        "unit": "m2",
        "properties": {
            "category": "vcl",
            "default_role": "vcl",
            "default_thickness_mm": 0.2,
            "include_in_u_value": False,    # negligible resistance; kept for validation
            "sd_value_m": 25.0,             # variable sd ≈ 0.25–25 m (intelligent membrane)
        },
    },
    # 4. Structural sheathing
    {
        "name": "OSB/3 Sheathing Board",
        "manufacturer": None,
        "lambda_W_mK": 0.13,
        "density_kg_m3": 650.0,
        "supplier_ref": "GENERIC-OSB3-11",
        "spec_ref": "EN 300",
        "unit": "m2",
        "properties": {
            "category": "sheathing",
            "default_role": "sheathing",
            "default_thickness_mm": 11.0,
            "include_in_u_value": True,
            "sd_value_m": 3.0,
        },
    },
    # 5. Structural framing zone (stud + PIR fill) — framing_fraction=0.15 suggested
    {
        "name": "C24 Stud Zone + PIR Fill (140mm)",
        "manufacturer": None,
        "lambda_W_mK": 0.023,               # PIR fill lambda; framing applied at layer level
        "density_kg_m3": None,
        "supplier_ref": "GENERIC-C24-PIR-140",
        "unit": "m2",
        "properties": {
            "category": "framing_zone",
            "default_role": "framing_zone",
            "default_thickness_mm": 140.0,
            "include_in_u_value": True,
            "framing_fraction_default": 0.15,   # 47mm stud @ 600cc ≈ 7.8%, rounded up
            "sd_value_m": None,
        },
    },
    # 5b. Structural framing zone (stud + mineral wool fill) — cost-optimised hybrid
    {
        "name": "C24 Stud Zone + Mineral Wool Fill (140mm)",
        "manufacturer": None,
        "lambda_W_mK": 0.034,               # MW fill lambda (Rockwool/Paroc semi-rigid)
        "density_kg_m3": None,
        "supplier_ref": "GENERIC-C24-MW-140",
        "unit": "m2",
        "properties": {
            "category": "framing_zone",
            "default_role": "framing_zone",
            "default_thickness_mm": 140.0,
            "include_in_u_value": True,
            "framing_fraction_default": 0.15,
            "sd_value_m": None,
        },
    },
    # 6. Outboard continuous insulation
    {
        "name": "PIR Insulation Board (Outboard)",
        "manufacturer": None,
        "lambda_W_mK": 0.023,
        "density_kg_m3": 32.0,
        "supplier_ref": "GENERIC-PIR-OUTBOARD-50",
        "unit": "m2",
        "properties": {
            "category": "insulation",
            "default_role": "insulation",
            "default_thickness_mm": 50.0,
            "include_in_u_value": True,
            "sd_value_m": 100.0,            # PIR faces have high sd — note for review
        },
    },
    # 7. Breather membrane — validation only
    {
        "name": "DuPont Tyvek Housewrap (Breather Membrane)",
        "manufacturer": "DuPont",
        "lambda_W_mK": 0.17,
        "density_kg_m3": None,
        "supplier_ref": "DUPONT-TYVEK-HOUSEWRAP",
        "unit": "m2",
        "properties": {
            "category": "breather",
            "default_role": "breather",
            "default_thickness_mm": 0.2,
            "include_in_u_value": False,
            "sd_value_m": 0.02,             # sd ≤ 0.1 m — vapour-open
        },
    },
    # 8. Ventilated cavity — excluded from U-value path
    {
        "name": "Ventilated Cavity",
        "manufacturer": None,
        "lambda_W_mK": 0.17,                # not used; excluded from calc
        "density_kg_m3": 1.2,
        "supplier_ref": "GENERIC-VENT-CAVITY-25",
        "unit": "m2",
        "properties": {
            "category": "cavity",
            "default_role": "cavity",
            "default_thickness_mm": 25.0,
            "include_in_u_value": False,    # ventilated — excluded per ISO 6946
            "sd_value_m": None,
        },
    },
    # 9. Treated batten (cladding support) — MTO only
    {
        "name": "Treated Timber Batten 25×50",
        "manufacturer": None,
        "lambda_W_mK": 0.13,
        "density_kg_m3": 450.0,
        "supplier_ref": "GENERIC-BATTEN-25X50",
        "unit": "m",
        "properties": {
            "category": "cavity",
            "default_role": "cavity",
            "default_thickness_mm": 25.0,
            "include_in_u_value": False,
            "sd_value_m": None,
        },
    },
    # 10. Counter-batten — MTO only
    {
        "name": "Treated Timber Counter-Batten 38×50",
        "manufacturer": None,
        "lambda_W_mK": 0.13,
        "density_kg_m3": 450.0,
        "supplier_ref": "GENERIC-COUNTER-BATTEN-38X50",
        "unit": "m",
        "properties": {
            "category": "cavity",
            "default_role": "cavity",
            "default_thickness_mm": 38.0,
            "include_in_u_value": False,
            "sd_value_m": None,
        },
    },
    # 11. Cladding
    {
        "name": "Fibre Cement Cladding Board",
        "manufacturer": None,
        "lambda_W_mK": 0.35,
        "density_kg_m3": 1500.0,
        "supplier_ref": "GENERIC-FC-CLADDING-12",
        "unit": "m2",
        "properties": {
            "category": "cladding",
            "default_role": "cladding",
            "default_thickness_mm": 12.0,
            "include_in_u_value": True,
            "sd_value_m": 50.0,
        },
    },
    # 12. Floor insulation
    {
        "name": "EPS Floor Insulation",
        "manufacturer": None,
        "lambda_W_mK": 0.038,
        "density_kg_m3": 20.0,
        "supplier_ref": "GENERIC-EPS-FLOOR-150",
        "unit": "m2",
        "properties": {
            "category": "insulation",
            "default_role": "insulation",
            "default_thickness_mm": 150.0,
            "include_in_u_value": True,
            "sd_value_m": 80.0,
        },
    },
    # 13. Concrete slab
    {
        "name": "Concrete Slab (in-situ)",
        "manufacturer": None,
        "lambda_W_mK": 1.15,
        "density_kg_m3": 2300.0,
        "supplier_ref": "GENERIC-CONCRETE-SLAB-150",
        "unit": "m2",
        "properties": {
            "category": "structure",
            "default_role": "structure",
            "default_thickness_mm": 150.0,
            "include_in_u_value": True,
            "sd_value_m": None,
        },
    },
    # 14. Roof insulation
    {
        "name": "Mineral Wool Roof Insulation",
        "manufacturer": None,
        "lambda_W_mK": 0.034,
        "density_kg_m3": 30.0,
        "supplier_ref": "GENERIC-MW-ROOF-300",
        "unit": "m2",
        "properties": {
            "category": "insulation",
            "default_role": "insulation",
            "default_thickness_mm": 300.0,
            "include_in_u_value": True,
            "sd_value_m": None,
        },
    },
    # 15. C24 structural timber — used as framing zone base material
    {
        "name": "C24 Structural Timber (Framing)",
        "manufacturer": None,
        "lambda_W_mK": 0.13,
        "density_kg_m3": 450.0,
        "supplier_ref": "GENERIC-C24-TIMBER",
        "unit": "m",
        "properties": {
            "category": "framing_zone",
            "default_role": "framing_zone",
            "default_thickness_mm": 140.0,
            "include_in_u_value": True,
            "framing_fraction_default": 0.15,
            "sd_value_m": None,
        },
    },
    # 16. PIR infill for composite framing zone
    {
        "name": "PIR Infill Insulation (Framing Zone)",
        "manufacturer": None,
        "lambda_W_mK": 0.023,
        "density_kg_m3": 32.0,
        "supplier_ref": "GENERIC-PIR-FRAMING-140",
        "unit": "m2",
        "properties": {
            "category": "insulation",
            "default_role": "insulation",
            "default_thickness_mm": 140.0,
            "include_in_u_value": True,
            "sd_value_m": 100.0,
        },
    },
    # 17. Mineral wool infill for composite framing zone
    {
        "name": "Mineral Wool Infill Insulation (Framing Zone)",
        "manufacturer": None,
        "lambda_W_mK": 0.034,
        "density_kg_m3": 30.0,
        "supplier_ref": "GENERIC-MW-FRAMING-140",
        "unit": "m2",
        "properties": {
            "category": "insulation",
            "default_role": "insulation",
            "default_thickness_mm": 140.0,
            "include_in_u_value": True,
            "sd_value_m": None,
        },
    },
    # 18. Standard polythene VCL — used in standard/light build-ups
    # Intello Plus is reserved for enhanced/premium airtightness specifications.
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
            "sd_value_m": 50.0,   # standard PE: high vapour resistance
        },
    },
    # 19. PIR outboard insulation — 100mm thickness
    # Used in standard hybrid wall and enhanced wall build-ups.
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


def run() -> None:
    with Session(engine) as db:
        # Ensure library_version id=1 exists
        lv = db.get(LibraryVersion, 1)
        if lv is None:
            lv = LibraryVersion(id=1, version="v1.0", notes="Standard material library")
            db.add(lv)
            db.flush()

        seeded = 0
        skipped = 0
        for m in MATERIALS:
            existing = (
                db.query(MaterialLibrary)
                .filter_by(supplier_ref=m["supplier_ref"])
                .first()
            )
            if existing:
                skipped += 1
                continue
            db.add(MaterialLibrary(library_version_id=lv.id, **m))
            seeded += 1

        db.commit()
        print(f"Materials: seeded {seeded}, skipped {skipped} (already present).")


if __name__ == "__main__":
    run()
