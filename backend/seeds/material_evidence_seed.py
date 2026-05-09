"""
Seed starter evidence for existing materials.

Run from backend/ directory:
    python seeds/material_evidence_seed.py

Options:
    --force   Overwrite fields even if a non-empty value already exists in the DB.
              Default: skip fields that already have a value (safe re-run behaviour).

Idempotent — matches by supplier_ref, updates evidence fields only.
Does NOT create new materials or duplicates.
All URLs are real published manufacturer/supplier pages — no fake links.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db import engine
from app.models import MaterialLibrary

# ── Evidence definitions keyed by supplier_ref ────────────────────────────────
# supplier_url   : official product page
# datasheet_url  : technical data sheet (TDS/PDS)
# dop_url        : Declaration of Performance (DoP)
# evidence_status: "verified" only when supplier_url + datasheet_url + dop_url all set;
#                  "partial" when some evidence exists but incomplete;
#                  "provisional" for assemblies / not-yet-selected products;
#                  None = let _auto_evidence_status() compute from category logic.

EVIDENCE: list[dict] = [

    # ────────────────────────────────────────────────────────────────────────────
    # MANUFACTURED PRODUCTS — real manufacturer evidence
    # ────────────────────────────────────────────────────────────────────────────

    {
        "supplier_ref": "SGG-GYPROC-12.5",
        "evidence_category": "manufactured_product",
        "manufacturer": "Saint-Gobain / British Gypsum",
        "supplier_name": "British Gypsum",
        "supplier_url": "https://www.british-gypsum.com/products/board-products/gyproc-wallboard-12-5mm",
        "datasheet_url": None,   # TDS on same product page — confirm direct PDF URL before adding
        "dop_url": None,         # DoP link not yet confirmed
        "evidence_status": "partial",   # product page confirmed; TDS/DoP URLs to follow
        "evidence_notes": (
            "Saint-Gobain / British Gypsum Gyproc WallBoard 12.5mm. "
            "EN 520 standard plasterboard. "
            "Product page confirmed — add TDS and DoP direct URLs when available."
        ),
    },

    {
        "supplier_ref": "DUPONT-TYVEK-HOUSEWRAP",
        "evidence_category": "manufactured_product",
        "manufacturer": "DuPont",
        "supplier_name": "DuPont",
        "supplier_url": "https://www.dupont.co.uk/products/tyvek-housewrap.html",
        "datasheet_url": None,   # TDS for product type 3060B available — confirm direct PDF URL
        "dop_url": None,         # DoP for type 3060B available — confirm direct PDF URL
        "evidence_status": "partial",   # product page confirmed; TDS/DoP direct PDF URLs to follow
        "evidence_notes": (
            "DuPont Tyvek Housewrap breather membrane. Product type 3060B. "
            "Breathable membrane for timber/steel/concrete wall systems. "
            "TDS and DoP available from DuPont — add direct PDF URLs when confirmed."
        ),
    },

    {
        "supplier_ref": "GENERIC-OSB3-11",
        "evidence_category": "manufactured_product",
        "manufacturer": "Kronospan",
        "supplier_name": "Kronospan",
        "supplier_url": "https://kronospan.com/en_IS/products/view/kronobuild/osb/osb-3-699/",
        "datasheet_url": None,   # DoP referenced on Kronospan site — add direct URL when confirmed
        "dop_url": None,
        "evidence_status": "partial",   # manufacturer + product page confirmed; DoP URL to follow
        "evidence_notes": (
            "OSB/3 sheathing board to EN 300. Kronospan OSB 3. "
            "DoP documentation available from Kronospan for LV/UK markets. "
            "Confirm exact product code and add DoP direct URL."
        ),
    },

    {
        "supplier_ref": "GENERIC-PIR-OUTBOARD-50",
        "evidence_category": "manufactured_product",
        "manufacturer": "Finnfoam",
        "supplier_name": "Finnfoam",
        "supplier_url": "https://finnfoam.com/applications/walls/exterior-walls-ff-pir/",
        "datasheet_url": None,   # FF-PIR datasheet available on finnfoam.com — add PDF URL
        "dop_url": None,         # FF-PIR DoP available — add direct URL
        "evidence_status": "partial",
        "evidence_notes": (
            "Finnfoam FF-PIR polyurethane insulation board (outboard continuous). 50mm. "
            "Declared λ = 0.022 W/mK. DoP available. "
            "Add TDS and DoP direct PDF URLs when confirmed for selected thickness/facer."
        ),
    },

    {
        "supplier_ref": "GENERIC-PIR-OUTBOARD-100",
        "evidence_category": "manufactured_product",
        "manufacturer": "Finnfoam",
        "supplier_name": "Finnfoam",
        "supplier_url": "https://finnfoam.com/applications/walls/exterior-walls-ff-pir/",
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": "partial",
        "evidence_notes": (
            "Finnfoam FF-PIR polyurethane insulation board (outboard continuous). 100mm. "
            "Same product family as 50mm. Add TDS and DoP direct PDF URLs when confirmed."
        ),
    },

    {
        "supplier_ref": "GENERIC-PIR-FRAMING-140",
        "evidence_category": "manufactured_product",
        "manufacturer": "Finnfoam",
        "supplier_name": "Finnfoam",
        "supplier_url": "https://finnfoam.com/applications/walls/exterior-walls-ff-pir/",
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": "partial",
        "evidence_notes": (
            "Finnfoam FF-PIR PIR infill insulation for framing zone. 140mm. "
            "Same product family as outboard boards. "
            "Add TDS and DoP direct PDF URLs when confirmed."
        ),
    },

    {
        "supplier_ref": "GENERIC-EPS-FLOOR-150",
        "evidence_category": "manufactured_product",
        "manufacturer": "Tenapors",
        "supplier_name": "Tenapors",
        "supplier_url": "https://www.tenapors.lv/wp-content/uploads/sgb_pdf/tenapors-eps-100-en.pdf",
        "datasheet_url": "https://www.tenapors.lv/wp-content/uploads/sgb_pdf/tenapors-eps-100-en.pdf",
        "dop_url": None,         # Tenapors EPS 100 DoP available — confirm URL
        "evidence_status": "partial",
        "evidence_notes": (
            "Tenapors EPS 100 floor/foundation insulation. 150mm (variable). "
            "Product datasheet confirmed. "
            "Add DoP direct URL when confirmed for selected thickness."
        ),
    },

    {
        "supplier_ref": "GENERIC-FC-CLADDING-12",
        "evidence_category": "manufactured_product",
        "manufacturer": "Cedral / Etex",
        "supplier_name": "Cedral",
        "supplier_url": None,    # cedral.com product page — confirm exact product (Lap/Click/board)
        "datasheet_url": None,
        "dop_url": "https://media.cedral.world/cert_214697_gb/original/91542098/declaration_of_performance_-_cedral_sidings.pdf",
        "evidence_status": "partial",
        "evidence_notes": (
            "Cedral / Etex fibre cement cladding board. 12mm. "
            "DoP confirmed for Cedral sidings (Lap & Click) under EN 12467. "
            "Confirm exact product type (Lap/Click/board) and add product page URL."
        ),
    },

    {
        "supplier_ref": "PROCLIMA-INTELLO-PLUS",
        "evidence_category": "manufactured_product",
        "manufacturer": "Pro Clima",
        "supplier_name": "Pro Clima",
        "supplier_url": None,    # proclima.com Intello Plus page — add URL
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": "partial",   # manufacturer known, spec_ref ETA-07/0274 on record
        "evidence_notes": (
            "Pro Clima Intello Plus intelligent airtightness / VCL membrane. "
            "ETA-07/0274. Variable sd 0.25–25 m. "
            "Add product page, TDS, and ETA certificate URLs from proclima.com."
        ),
    },

    {
        "supplier_ref": "GENERIC-MW-ROOF-300",
        "evidence_category": "manufactured_product",
        "manufacturer": None,    # PAROC / Knauf / ISOVER — not yet selected
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": None,   # auto: missing — no manufacturer selected yet
        "evidence_notes": (
            "Mineral wool roof insulation. 300mm. "
            "Possible suppliers: PAROC, Knauf, ISOVER. "
            "Do not mark partial/verified until exact product is selected."
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
        "evidence_status": None,   # auto: missing
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
        "evidence_status": None,   # auto: missing
        "evidence_notes": (
            "Standard 0.2mm polythene vapour control layer. "
            "Generic commodity product — no specific manufacturer datasheet required. "
            "sd ≈ 50 m. Review if a specific branded product is selected."
        ),
    },

    # ────────────────────────────────────────────────────────────────────────────
    # RAW / SUPPLIER-SPECIFIED MATERIALS
    # ────────────────────────────────────────────────────────────────────────────

    {
        "supplier_ref": "GENERIC-C24-TIMBER",
        "evidence_category": "raw_material",
        "manufacturer": None,
        "supplier_name": None,
        "supplier_url": None,
        "datasheet_url": None,
        "dop_url": None,
        "evidence_status": None,   # auto: missing (raw_material, no supplier set)
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
        "evidence_status": None,
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

    # ────────────────────────────────────────────────────────────────────────────
    # ASSEMBLY / CALCULATION ITEMS — never require manufacturer datasheet
    # ────────────────────────────────────────────────────────────────────────────

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


def _should_update(existing_val, new_val, force: bool) -> bool:
    """Only overwrite if forced or field is currently empty."""
    if force:
        return new_val is not None
    return (existing_val is None or existing_val == "") and new_val is not None


def run(force: bool = False) -> None:
    from app.api.build_ups import _auto_evidence_status

    with Session(engine) as db:
        updated = 0
        skipped = 0
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

            changed = False

            def _set(field, val):
                nonlocal changed
                if _should_update(getattr(mat, field, None), val, force):
                    setattr(mat, field, val)
                    changed = True

            # Always apply category from seed (default "manufactured_product" in DB is not user-set)
            if ev.get("evidence_category"):
                mat.evidence_category = ev["evidence_category"]
                changed = True
            _set("manufacturer",      ev.get("manufacturer"))
            _set("supplier_name",     ev.get("supplier_name"))
            _set("supplier_url",      ev.get("supplier_url"))
            _set("datasheet_url",     ev.get("datasheet_url"))
            _set("dop_url",           ev.get("dop_url"))
            _set("evidence_notes",    ev.get("evidence_notes"))

            # Evidence status: manual override takes precedence; else auto-compute
            override = ev.get("evidence_status")
            if override is not None:
                if force or mat.evidence_status in ("missing", None):
                    mat.evidence_status = override
                    changed = True
            else:
                new_status = _auto_evidence_status(mat)
                if mat.evidence_status != new_status:
                    mat.evidence_status = new_status
                    changed = True

            if changed:
                updated += 1
            else:
                skipped += 1

        db.commit()
        print(f"\nEvidence seed complete: {updated} updated, {skipped} already set, {not_found} not found.")

        # Summary by status
        from sqlalchemy import func
        print("\nEvidence status summary:")
        for status, count in sorted(
            db.query(MaterialLibrary.evidence_status, func.count())
            .group_by(MaterialLibrary.evidence_status).all()
        ):
            print(f"  {status or 'null'}: {count}")

        print("\nEvidence category summary:")
        for cat, count in sorted(
            db.query(MaterialLibrary.evidence_category, func.count())
            .group_by(MaterialLibrary.evidence_category).all()
        ):
            print(f"  {cat or 'null'}: {count}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    if force:
        print("Running in --force mode (overwriting existing values).")
    run(force=force)
