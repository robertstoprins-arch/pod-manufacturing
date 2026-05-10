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
        "datasheet_url": "https://www.british-gypsum.com/documents/product-data-sheet-pds/british-gypsum-pds-gyproc-wallboard-12-5mm.pdf",
        "dop_url": None,         # DoP not publicly indexed — add manually from british-gypsum.com CE Marking section
        "evidence_status": "partial",
        "evidence_notes": (
            "Saint-Gobain / British Gypsum Gyproc WallBoard 12.5mm. EN 520 standard plasterboard. "
            "Product page and PDS confirmed. DoP available on british-gypsum.com under CE Marking — "
            "add direct DoP PDF URL manually."
        ),
    },

    {
        "supplier_ref": "DUPONT-TYVEK-HOUSEWRAP",
        "evidence_category": "manufactured_product",
        "manufacturer": "DuPont",
        "supplier_name": "DuPont",
        "supplier_url": "https://www.dupont.co.uk/products/tyvek-housewrap.html",
        "datasheet_url": "https://www.dupont.co.uk/content/dam/dupont/amer/us/en/safety/public/documents/en/TyvekHousewrap-3060B-TDS.pdf",
        "dop_url": "https://www.dupont.co.uk/content/dam/dupont/amer/us/en/safety/public/documents/en/TyvekHousewrap-3060B-DoP.pdf",
        "evidence_status": "verified",
        "evidence_notes": (
            "DuPont Tyvek Housewrap breather membrane. Product type 3060B. "
            "Product page, TDS and DoP all confirmed from dupont.co.uk."
        ),
    },

    {
        "supplier_ref": "GENERIC-OSB3-11",
        "evidence_category": "manufactured_product",
        "manufacturer": "Kronospan",
        "supplier_name": "Kronospan",
        "supplier_url": "https://kronospan.com/en_EN/products/view/kronobuild/osb/osb-3/osb-3-699/",
        "datasheet_url": None,   # Kronospan downloads served via JS app — no stable direct PDF URL
        "dop_url": "https://kronospan.com/en_IE/ajax/express_services/download/?args%5B0%5D=express-services&args%5B1%5D=downloads&args%5B2%5D=United-Kingdom&args%5B3%5D=declaration-of-performance&args%5B4%5D=dop-osb-3-mogliev.pdf",
        "evidence_status": "partial",
        "evidence_notes": (
            "OSB/3 sheathing board to EN 300. Kronospan OSB 3. Product page and DoP confirmed. "
            "TDS served via Kronospan's JS download portal — no stable direct PDF URL available. "
            "DoP URL is Kronospan's UK download endpoint — verify it resolves before sharing with client."
        ),
    },

    {
        "supplier_ref": "GENERIC-PIR-OUTBOARD-50",
        "evidence_category": "manufactured_product",
        "manufacturer": "Finnfoam",
        "supplier_name": "Finnfoam",
        "supplier_url": "https://www.finnfoam.fi/en/products/ff-pir/",
        "datasheet_url": "https://finnfoam.fi/wp-content/uploads/2024/03/FF-PIR_EN_technical_properties.pdf",
        "dop_url": "https://finnfoam.fi/wp-content/uploads/2025/01/Finnfoam_2025_en_FF-PIR-GT_201-FF-2025-01-20.pdf",
        "evidence_status": "verified",
        "evidence_notes": (
            "Finnfoam FF-PIR polyurethane insulation board (outboard continuous). 50mm. "
            "Declared λ = 0.022 W/mK. Product page, TDS and DoP (variant GT/201) confirmed from finnfoam.fi. "
            "Note: DoP is variant-specific (GT = standard uncoated). "
            "Update if a coated or foil-faced variant is selected."
        ),
    },

    {
        "supplier_ref": "GENERIC-PIR-OUTBOARD-100",
        "evidence_category": "manufactured_product",
        "manufacturer": "Finnfoam",
        "supplier_name": "Finnfoam",
        "supplier_url": "https://www.finnfoam.fi/en/products/ff-pir/",
        "datasheet_url": "https://finnfoam.fi/wp-content/uploads/2024/03/FF-PIR_EN_technical_properties.pdf",
        "dop_url": "https://finnfoam.fi/wp-content/uploads/2025/01/Finnfoam_2025_en_FF-PIR-GT_201-FF-2025-01-20.pdf",
        "evidence_status": "verified",
        "evidence_notes": (
            "Finnfoam FF-PIR polyurethane insulation board (outboard continuous). 100mm. "
            "Same product family as 50mm — same TDS and DoP apply. "
            "Product page, TDS and DoP confirmed from finnfoam.fi."
        ),
    },

    {
        "supplier_ref": "GENERIC-PIR-FRAMING-140",
        "evidence_category": "manufactured_product",
        "manufacturer": "Finnfoam",
        "supplier_name": "Finnfoam",
        "supplier_url": "https://www.finnfoam.fi/en/products/ff-pir/",
        "datasheet_url": "https://finnfoam.fi/wp-content/uploads/2024/03/FF-PIR_EN_technical_properties.pdf",
        "dop_url": "https://finnfoam.fi/wp-content/uploads/2025/01/Finnfoam_2025_en_FF-PIR-GT_201-FF-2025-01-20.pdf",
        "evidence_status": "verified",
        "evidence_notes": (
            "Finnfoam FF-PIR PIR infill insulation for C24 framing zone. 140mm. "
            "Same product family as outboard boards — same TDS and DoP apply. "
            "Product page, TDS and DoP confirmed from finnfoam.fi."
        ),
    },

    {
        "supplier_ref": "GENERIC-EPS-FLOOR-150",
        "evidence_category": "manufactured_product",
        "manufacturer": "Tenapors",
        "supplier_name": "Tenapors",
        "supplier_url": "https://www.tenapors.lv/en/products/eps-100/",
        "datasheet_url": "https://www.tenapors.lv/wp-content/uploads/sgb_pdf/tenapors-eps-100-en.pdf",
        "dop_url": "https://www.tenapors.lv/wp-content/uploads/dop/tenapors-eps-100-dop-en.pdf",
        "evidence_status": "verified",
        "evidence_notes": (
            "Tenapors EPS 100 floor/foundation insulation. 150mm (variable thickness). "
            "Product page, TDS and DoP all confirmed from tenapors.lv."
        ),
    },

    {
        "supplier_ref": "GENERIC-FC-CLADDING-12",
        "evidence_category": "manufactured_product",
        "manufacturer": "Cedral / Etex",
        "supplier_name": "Cedral",
        "supplier_url": "https://www.cedral.world/en-gb/cladding/cedral-lap/",
        "datasheet_url": "https://media.cedral.world/cert_214697_gb/original/91542097/material_information_sheet_-_cedral_lap.pdf",
        "dop_url": "https://media.cedral.world/cert_214697_gb/original/91542098/declaration_of_performance_-_cedral_sidings.pdf",
        "evidence_status": "verified",
        "evidence_notes": (
            "Cedral Lap fibre cement cladding board. 12mm. EN 12467. "
            "Product page (Cedral Lap), Material Information Sheet and DoP all confirmed from cedral.world. "
            "DoP covers both Lap and Click product lines. "
            "Update supplier_url to cedral-click page if Click profile is selected."
        ),
    },

    {
        "supplier_ref": "PROCLIMA-INTELLO-PLUS",
        "evidence_category": "manufactured_product",
        "manufacturer": "Pro Clima",
        "supplier_name": "Pro Clima",
        "supplier_url": "https://www.proclima.com/products/internal-sealing/intello-plus",
        "datasheet_url": "https://proclima-pdm.moll-group.eu/datasheets/INTPL/datasheet/INTELLO%20PLUS.pdf?language=en-xx",
        "dop_url": "https://proclima-pdm.moll-group.eu/datasheets/INTPL/DoP/INTELLO%20PLUS.pdf?language=en-xx",
        "evidence_status": "verified",
        "evidence_notes": (
            "Pro Clima Intello Plus intelligent airtightness / VCL membrane. "
            "Variable sd 0.25–25 m. Product page, TDS and DoP all confirmed from proclima.com. "
            "Note: current certificate is ETA-18/1146 (supersedes ETA-07/0274 previously on record). "
            "Update spec_ref if building control requires the current ETA number."
        ),
    },

    {
        "supplier_ref": "GENERIC-MW-ROOF-300",
        "evidence_category": "manufactured_product",
        "manufacturer": "Rockwool",
        "supplier_name": "Rockwool",
        "supplier_url": "https://www.rockwool.com/uk/products-and-applications/product-overview/slab-products/rwa45-en-gb/",
        "datasheet_url": "https://www.rockwool.com/syssiteassets/rw-uk/downloads/datasheets/rw-slabs.pdf",
        "dop_url": "https://www.rockwool.com/uk/legal-notice/declaration-of-performance/",
        "evidence_status": "partial",
        "evidence_notes": (
            "Rockwool RW Slabs / RWA45 stone wool insulation for pitched roof. 300mm. "
            "Euroclass A1 non-combustible. λ = 0.034–0.045 W/mK depending on grade. "
            "Product page and TDS confirmed from rockwool.com/uk. "
            "DoP URL links to Rockwool's DoP finder portal — search by product name 'RW Slabs' or DoP number on packaging."
        ),
    },

    {
        "supplier_ref": "GENERIC-MW-FRAMING-140",
        "evidence_category": "manufactured_product",
        "manufacturer": "Rockwool",
        "supplier_name": "Rockwool",
        "supplier_url": "https://www.rockwool.com/uk/products/flexi/",
        "datasheet_url": "https://www.rockwool.com/syssiteassets/rw-uk/downloads/datasheets/rw-slabs.pdf",
        "dop_url": "https://www.rockwool.com/uk/legal-notice/declaration-of-performance/",
        "evidence_status": "partial",
        "evidence_notes": (
            "Rockwool Flexi stone wool insulation for C24 framing zone. 140mm. "
            "Flexible edge for tight friction-fit between studs. Euroclass A1. "
            "Product page confirmed from rockwool.com/uk. "
            "DoP URL links to Rockwool's DoP finder portal — search by product name 'Flexi'."
        ),
    },

    {
        "supplier_ref": "GENERIC-VCL-STANDARD",
        "evidence_category": "manufactured_product",
        "manufacturer": "Visqueen",
        "supplier_name": "Visqueen",
        "supplier_url": "https://visqueen.com/products/vapour-barrier",
        "datasheet_url": "https://www.resapol.com/wp-content/uploads/2021/12/Visqueen_Vapour_Barrier_datasheet-tds.pdf",
        "dop_url": None,   # CE DoP not required for polythene VCL — not a CE-marked product
        "evidence_status": "partial",
        "evidence_notes": (
            "Visqueen Vapour Barrier polyethylene vapour control layer. 250 micron (0.25mm). "
            "BBA approved. Install to warm side of insulation. sd ≈ 50 m. "
            "Product page and TDS confirmed. No CE DoP required for this product type."
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
