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
PRICES: dict[str, tuple] = {
    # Internal finish
    "SGG-GYPROC-12.5":            (4.50,  "m2",  "EUR", "Standard 12.5mm plasterboard, trade supply"),
    # Service void — batten framing labour+material combined
    "GENERIC-SVC-VOID-50":        (8.00,  "m2",  "EUR", "25×50 batten frame incl fixing, indicative"),
    # VCL membrane
    "PROCLIMA-INTELLO-PLUS":      (6.50,  "m2",  "EUR", "Intello Plus, trade supply"),
    # Sheathing
    "GENERIC-OSB3-11":            (7.50,  "m2",  "EUR", "OSB/3 11mm, trade supply"),
    # Framing zones (stud + insulation combined as m2 panel)
    "GENERIC-C24-PIR-140":        (38.00, "m2",  "EUR", "C24 stud zone 140mm + PIR fill, indicative"),
    "GENERIC-C24-MW-140":         (22.00, "m2",  "EUR", "C24 stud zone 140mm + mineral wool fill, indicative"),
    # Outboard insulation
    "GENERIC-PIR-OUTBOARD-50":    (18.00, "m2",  "EUR", "PIR board 50mm outboard, trade supply"),
    # Breather membrane
    "DUPONT-TYVEK-HOUSEWRAP":     (3.50,  "m2",  "EUR", "Tyvek Housewrap, trade supply"),
    # Ventilated cavity — counter-batten labour+material
    "GENERIC-VENT-CAVITY-25":     (5.00,  "m2",  "EUR", "Ventilated cavity inc battens, indicative"),
    # Linear batten / counter-batten
    "GENERIC-BATTEN-25X50":       (0.80,  "m",   "EUR", "25×50 treated batten, trade supply"),
    "GENERIC-COUNTER-BATTEN-38X50": (1.20, "m",  "EUR", "38×50 treated counter-batten, trade supply"),
    # Cladding
    "GENERIC-FC-CLADDING-12":     (28.00, "m2",  "EUR", "Fibre cement cladding 12mm, trade supply"),
    # Floor
    "GENERIC-EPS-FLOOR-150":      (14.00, "m2",  "EUR", "EPS floor 150mm, trade supply per 100mm basis"),
    "GENERIC-CONCRETE-SLAB-150":  (55.00, "m2",  "EUR", "In-situ concrete slab 150mm incl pour, indicative"),
    # Roof insulation
    "GENERIC-MW-ROOF-300":        (16.00, "m2",  "EUR", "Mineral wool roof 300mm, trade supply"),
    # Structural framing
    "GENERIC-C24-TIMBER":         (3.50,  "m",   "EUR", "C24 structural timber, trade supply"),
    # Framing zone infill (sold per m2 of panel)
    "GENERIC-PIR-FRAMING-140":    (18.00, "m2",  "EUR", "PIR infill 140mm framing zone, indicative"),
    "GENERIC-MW-FRAMING-140":     (12.00, "m2",  "EUR", "Mineral wool infill 140mm framing zone, indicative"),
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
