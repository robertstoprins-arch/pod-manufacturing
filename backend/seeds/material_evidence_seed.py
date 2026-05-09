"""
Seed starter evidence for existing materials.

Run from backend/ directory:
    python seeds/material_evidence_seed.py

Idempotent — matches by supplier_ref, updates evidence fields only.
Does NOT create new materials.
Does NOT fake links — all URLs are real published pages.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db import engine
from app.models import MaterialLibrary

# ── Evidence definitions keyed by supplier_ref ────────────────────────────────
# Fields:
#   evidence_category    : manufactured_product | generic_assembly | raw_material |
#                          provisional_allowance | service_item
#   manufacturer         : string (if known)
#   supplier_name        : string (if known)
#   supplier_url         : real published product page (or None)
#   datasheet_url        : real published datasheet (or None)
#   dop_url              : real published DoP (or None)
#   evidence_status      : manual override (or None = auto-compute from category logic)
#   evidence_notes       : internal note
#
# Rule: do not set evidence_status="verified" unless supplier_url + datasheet_url are both set.

EVIDENCE: list[dict] = [

    # ── Manufactured products ─────────────────────────────────────────────────

    {
        "supplier_ref": "SGG-GYPROC-12.5",
        "evidence_category": "manufactured_product",
        "manufacturer": "Saint-Gobain / British Gypsum",
        "supplier_name": "Saint-Gobain",
        "supplier_url": None,       # add when exact product page confirmed
        "datasheet_url": None,      # add when TDS URL confirmed
        "dop_url": None,
        "evidence_status": None,    # auto: missing (no URLs yet, but manufacturer known)
        "evidence_notes": (
            "Saint-Gobain Gyproc Standard Wallboard 12.5mm. "
            "EN 520 plasterboard. British Gypsum publishes product data sheet for "
            "Gyproc WallBoard 12.5mm — add URL when confirmed."
        ),
    },
    {
        "supplier_ref": "PROCLIMA-INTELLO-PLUS",
        "evidence_category": "manufactured_product",
        "manufacturer": "Pro Clima",
        "supplier_name": "Pro Clima",
        "supplier_url": None,       # add Pro Clima Intello Plus product page URL
        "datasheet_url": None,      # add TDS/datasheet URL
        "dop_url": None,
        "evidence_status": None,    # auto: missing (no URLs yet)
        "evidence_notes": (
            "Pro Clima Intello Plus intelligent airtightness membrane. "
            "ETA-07/0274. Variable sd 0.25–25 m. "
            "Add supplier/datasheet URLs from proclima.com when confirmed."
        ),
    },
    {
        "supplier_ref": "GENERIC-OSB3-11",
        "evidence_category": "manufactured_product",
        "manufacturer": None,       # Kronospan or equivalent — not yet selected
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": None,    # auto: missing
        "evidence_notes": (
            "OSB/3 sheathing board to EN 300. "
            "Typical supplier: Kronospan. Kronospan publishes OSB/3 DoP for "
            "LV/UK markets — update when exact supplier and product are confirmed."
        ),
    },
    {
        "supplier_ref": "GENERIC-PIR-OUTBOARD-50",
        "evidence_category": "manufactured_product",
        "manufacturer": None,       # Finnfoam FF-PIR or equivalent — not yet selected
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": None,    # auto: missing
        "evidence_notes": (
            "PIR insulation board (outboard continuous). 50mm. "
            "Possible product: Finnfoam FF-PIR (λ=0.022 W/mK, DoP available). "
            "Update when exact product/thickness/facer and supplier are confirmed."
        ),
    },
    {
        "supplier_ref": "GENERIC-PIR-OUTBOARD-100",
        "evidence_category": "manufactured_product",
        "manufacturer": None,
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": None,    # auto: missing
        "evidence_notes": (
            "PIR insulation board (outboard continuous). 100mm. "
            "Same product family as 50mm — Finnfoam FF-PIR or equivalent. "
            "Update when exact product and supplier are confirmed."
        ),
    },
    {
        "supplier_ref": "DUPONT-TYVEK-HOUSEWRAP",
        "evidence_category": "manufactured_product",
        "manufacturer": "DuPont",
        "supplier_name": "DuPont",
        "supplier_url": None,       # add Tyvek Housewrap product page when confirmed
        "datasheet_url": None,      # add TDS URL when confirmed
        "dop_url": None,            # DoP for product type 3060B available — add URL
        "evidence_status": None,    # auto: missing (manufacturer known, no URLs yet)
        "evidence_notes": (
            "DuPont Tyvek Housewrap breather membrane. "
            "Suitable for timber frame / steel frame / concrete wall systems. "
            "DoP for type 3060B available from DuPont — add URLs when confirmed."
        ),
    },
    {
        "supplier_ref": "GENERIC-FC-CLADDING-12",
        "evidence_category": "manufactured_product",
        "manufacturer": None,       # Cedral/Etex or equivalent — not yet selected
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": None,    # auto: missing
        "evidence_notes": (
            "Fibre cement cladding board. 12mm. "
            "Possible products: Cedral Lap or Cedral Click (Etex group). "
            "Cedral publishes DoP under EN 12467. "
            "Update when exact product type (Lap/Click/board) and supplier are confirmed."
        ),
    },
    {
        "supplier_ref": "GENERIC-EPS-FLOOR-150",
        "evidence_category": "manufactured_product",
        "manufacturer": None,       # Tenapors / Tenax EPS 100 or equivalent
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": None,    # auto: missing
        "evidence_notes": (
            "EPS floor insulation (EPS 100 grade). 150mm variable thickness. "
            "Possible supplier: Tenapors (TENAPORS EPS 100, DoP available). "
            "Update when exact supplier and product are confirmed."
        ),
    },
    {
        "supplier_ref": "GENERIC-MW-ROOF-300",
        "evidence_category": "manufactured_product",
        "manufacturer": None,       # PAROC / Knauf / ISOVER — not yet selected
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": None,    # auto: missing
        "evidence_notes": (
            "Mineral wool roof insulation. 300mm. "
            "Possible suppliers: PAROC, Knauf, ISOVER. "
            "Do not mark partial/verified until exact product is selected."
        ),
    },
    {
        "supplier_ref": "GENERIC-PIR-FRAMING-140",
        "evidence_category": "manufactured_product",
        "manufacturer": None,
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": None,    # auto: missing
        "evidence_notes": (
            "PIR infill insulation for framing zone. 140mm. "
            "Same product family as PIR outboard — update when supplier/product confirmed."
        ),
    },
    {
        "supplier_ref": "GENERIC-MW-FRAMING-140",
        "evidence_category": "manufactured_product",
        "manufacturer": None,
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": None,    # auto: missing
        "evidence_notes": (
            "Mineral wool infill insulation for framing zone. 140mm. "
            "Possible suppliers: PAROC, Knauf, ISOVER semi-rigid batts. "
            "Update when exact product and supplier are confirmed."
        ),
    },
    {
        "supplier_ref": "GENERIC-VCL-STANDARD",
        "evidence_category": "manufactured_product",
        "manufacturer": None,
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": None,    # auto: missing (generic polythene — no specific product)
        "evidence_notes": (
            "Standard 0.2mm polythene vapour control layer. "
            "Generic commodity product — no specific manufacturer datasheet required. "
            "sd ≈ 50 m. Review if a specific branded product is selected."
        ),
    },

    # ── Raw materials ─────────────────────────────────────────────────────────

    {
        "supplier_ref": "GENERIC-C24-TIMBER",
        "evidence_category": "raw_material",
        "manufacturer": None,
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": None,    # auto: missing (raw_material with no supplier yet)
        "evidence_notes": (
            "C24 structural timber framing (47×140mm or equivalent). "
            "Grade to EN 338 / BS 4978. Local merchant supply — add supplier URL when confirmed."
        ),
    },
    {
        "supplier_ref": "GENERIC-CONCRETE-SLAB-150",
        "evidence_category": "raw_material",
        "manufacturer": None,
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": None,    # auto: missing
        "evidence_notes": "In-situ concrete slab. Mix spec to be confirmed by structural engineer.",
    },
    {
        "supplier_ref": "GENERIC-BATTEN-25X50",
        "evidence_category": "raw_material",
        "manufacturer": None,
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": None,
        "evidence_notes": "Treated timber batten 25×50mm. Local merchant supply.",
    },
    {
        "supplier_ref": "GENERIC-COUNTER-BATTEN-38X50",
        "evidence_category": "raw_material",
        "manufacturer": None,
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": None,
        "evidence_notes": "Treated timber counter-batten 38×50mm. Local merchant supply.",
    },

    # ── Generic assemblies ────────────────────────────────────────────────────

    {
        "supplier_ref": "GENERIC-SVC-VOID-50",
        "evidence_category": "generic_assembly",
        "manufacturer": None,
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": "provisional",
        "evidence_notes": (
            "Assembly/calculation item. Service void formed by 25×50 battens at 600 centres. "
            "Evidence is provided by the component materials, not this row."
        ),
    },
    {
        "supplier_ref": "GENERIC-C24-PIR-140",
        "evidence_category": "generic_assembly",
        "manufacturer": None,
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": "provisional",
        "evidence_notes": (
            "Assembly/calculation item. C24 stud zone with PIR infill at 140mm. "
            "Evidence is provided by GENERIC-C24-TIMBER and GENERIC-PIR-FRAMING-140."
        ),
    },
    {
        "supplier_ref": "GENERIC-C24-MW-140",
        "evidence_category": "generic_assembly",
        "manufacturer": None,
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": "provisional",
        "evidence_notes": (
            "Assembly/calculation item. C24 stud zone with mineral wool infill at 140mm. "
            "Evidence is provided by GENERIC-C24-TIMBER and GENERIC-MW-FRAMING-140."
        ),
    },
    {
        "supplier_ref": "GENERIC-VENT-CAVITY-25",
        "evidence_category": "generic_assembly",
        "manufacturer": None,
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": "provisional",
        "evidence_notes": (
            "Assembly/calculation item. Ventilated cavity formed by counter-battens. "
            "Excluded from U-value calculation per ISO 6946. "
            "Evidence is provided by GENERIC-COUNTER-BATTEN-38X50."
        ),
    },
]


def run() -> None:
    with Session(engine) as db:
        updated = 0
        not_found = 0

        for ev in EVIDENCE:
            ref = ev["supplier_ref"]
            mat = (
                db.query(MaterialLibrary)
                .filter(MaterialLibrary.supplier_ref == ref)
                .first()
            )
            if mat is None:
                print(f"  NOT FOUND: {ref}")
                not_found += 1
                continue

            # Apply evidence fields
            mat.evidence_category = ev["evidence_category"]
            if ev.get("manufacturer") is not None:
                mat.manufacturer = ev["manufacturer"]
            if ev.get("supplier_name") is not None:
                mat.supplier_name = ev["supplier_name"]
            if ev.get("supplier_url") is not None:
                mat.supplier_url = ev["supplier_url"]
            if ev.get("datasheet_url") is not None:
                mat.datasheet_url = ev["datasheet_url"]
            if ev.get("dop_url") is not None:
                mat.dop_url = ev["dop_url"]
            if ev.get("evidence_notes") is not None:
                mat.evidence_notes = ev["evidence_notes"]

            # Status: use manual override if set, otherwise auto-compute from category
            if ev.get("evidence_status") is not None:
                mat.evidence_status = ev["evidence_status"]
            else:
                from app.api.build_ups import _auto_evidence_status
                mat.evidence_status = _auto_evidence_status(mat)

            updated += 1

        db.commit()
        print(f"Evidence seed complete: {updated} updated, {not_found} not found.")

        # Print summary by status
        from sqlalchemy import func
        rows = (
            db.query(MaterialLibrary.evidence_status, func.count())
            .group_by(MaterialLibrary.evidence_status)
            .all()
        )
        print("Evidence summary:")
        for status, count in sorted(rows):
            print(f"  {status}: {count}")

        rows2 = (
            db.query(MaterialLibrary.evidence_category, func.count())
            .group_by(MaterialLibrary.evidence_category)
            .all()
        )
        print("Category summary:")
        for cat, count in sorted(rows2):
            print(f"  {cat}: {count}")


if __name__ == "__main__":
    run()
