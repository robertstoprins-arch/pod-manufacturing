"""
Seed indicative market prices for standard materials.

Nordic / Baltic market benchmarks in EUR/m² (or EUR/m for linear items).
All prices are trade-level estimates — update with real supplier quotes.
Price type: 'import_benchmark' — clearly flagged as indicative.

Run from backend/:
    python seeds/material_prices_seed.py

Idempotent — skips materials that already have a default price of this type.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from app.db import SessionLocal
from app.models import MaterialLibrary, MaterialPrice

# supplier_ref → (price_per_unit, unit, currency, notes)
#
# Unit conventions:
#   "m2"  — area materials (boards, membranes, insulation, cladding)
#   "lm"  — linear materials (battens, studs, counter-battens)
#           Must match mto_resolver output units to avoid unit-mismatch fallback.
#   "m3"  — volume materials (concrete)
#
# Variable-thickness materials (EPS, PIR outboard) are priced at a stated
# basis thickness; the BOM engine scales proportionally.
#   EPS  basis = 100mm (price stored for 100mm; 250mm → price × 2.5)
#   PIR  basis =  50mm (price stored for  50mm; 100mm → price × 2.0)
PRICES: dict[str, tuple] = {
    # Internal finish
    "SGG-GYPROC-12.5":              (4.50,  "m2",  "EUR", "Standard 12.5mm plasterboard, trade supply"),
    # Service void — 25×50 battens at 600cc, priced per lm of batten
    # Previously stored as m2; corrected to lm to match mto_resolver output.
    "GENERIC-SVC-VOID-50":          (0.90,  "lm",  "EUR", "25×50 treated service void batten per lm, indicative"),
    # VCL membranes
    "GENERIC-VCL-STANDARD":         (1.50,  "m2",  "EUR", "Standard 0.2mm polythene VCL, trade supply"),
    "PROCLIMA-INTELLO-PLUS":        (6.50,  "m2",  "EUR", "Intello Plus intelligent VCL, trade supply (premium/enhanced only)"),
    # Sheathing
    "GENERIC-OSB3-11":              (7.50,  "m2",  "EUR", "OSB/3 11mm, trade supply"),
    # Framing zones (composite panel prices — used as fallback if sub-material refs missing)
    "GENERIC-C24-PIR-140":          (38.00, "m2",  "EUR", "C24 stud zone 140mm + PIR fill composite, indicative"),
    "GENERIC-C24-MW-140":           (22.00, "m2",  "EUR", "C24 stud zone 140mm + mineral wool fill composite, indicative"),
    # Outboard insulation — variable thickness; prices at stated basis thickness
    "GENERIC-PIR-OUTBOARD-50":      (18.00, "m2",  "EUR", "PIR board outboard, trade supply — basis 50mm (BOM scales by thickness)"),
    "GENERIC-PIR-OUTBOARD-100":     (32.00, "m2",  "EUR", "PIR board 100mm outboard, trade supply"),
    # Breather membrane
    "DUPONT-TYVEK-HOUSEWRAP":       (3.50,  "m2",  "EUR", "Tyvek Housewrap, trade supply"),
    # Ventilated cavity — combined batten + fixing allowance per m2 of wall face
    "GENERIC-VENT-CAVITY-25":       (5.00,  "m2",  "EUR", "Ventilated cavity inc battens, indicative"),
    # Linear battens / counter-battens
    "GENERIC-BATTEN-25X50":         (0.80,  "lm",  "EUR", "25×50 treated batten per lm, trade supply"),
    "GENERIC-COUNTER-BATTEN-38X50": (1.20,  "lm",  "EUR", "38×50 treated counter-batten per lm, trade supply"),
    # Cladding
    "GENERIC-FC-CLADDING-12":       (28.00, "m2",  "EUR", "Fibre cement cladding 12mm, trade supply"),
    # Floor insulation — EPS variable thickness; basis 100mm
    "GENERIC-EPS-FLOOR-150":        (8.00,  "m2",  "EUR", "EPS floor insulation, trade supply — basis 100mm (BOM scales by thickness)"),
    # Concrete slab — indicative rate; verify with local supplier
    "GENERIC-CONCRETE-SLAB-150":    (55.00, "m2",  "EUR", "In-situ concrete slab 150mm incl pour, indicative — verify supplier rate"),
    # Roof insulation
    "GENERIC-MW-ROOF-300":          (16.00, "m2",  "EUR", "Mineral wool roof insulation, trade supply"),
    # C24 structural timber — priced per lm for framing_zone_split sub-lines
    "GENERIC-C24-TIMBER":           (3.50,  "lm",  "EUR", "C24 structural timber per lm, trade supply"),
    # Framing zone infill materials — priced separately from composite zone
    "GENERIC-PIR-FRAMING-140":      (18.00, "m2",  "EUR", "PIR infill 140mm framing zone per m2, indicative"),
    "GENERIC-MW-FRAMING-140":       (12.00, "m2",  "EUR", "Mineral wool infill 140mm framing zone per m2, indicative"),
}


def run():
    db = SessionLocal()
    seeded = 0
    skipped = 0
    try:
        mats = db.query(MaterialLibrary).all()
        mat_by_ref = {m.supplier_ref: m for m in mats}

        for ref, (price, unit, currency, notes) in PRICES.items():
            mat = mat_by_ref.get(ref)
            if mat is None:
                print(f"  WARN: material not found for ref {ref!r} — skipping")
                continue

            # Skip if already has a default import_benchmark price for this unit
            existing = next(
                (p for p in mat.prices
                 if p.price_type == "import_benchmark" and p.unit == unit and p.is_default),
                None
            )
            if existing:
                skipped += 1
                continue

            db.add(MaterialPrice(
                material_id=mat.id,
                price_type="import_benchmark",
                price_per_unit=price,
                unit=unit,
                currency=currency,
                notes=notes,
                is_default=True,
            ))
            seeded += 1

        db.commit()
        print(f"Prices: seeded {seeded}, skipped {skipped} (already present).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
