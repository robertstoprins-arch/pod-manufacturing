"""
Skill: Procurement CSV

Takes a material take-off line list and produces a procurement schedule —
one row per material, with waste-adjusted order quantities, supplier references,
unit prices, and estimated costs.

Two public functions:
  procurement_schedule() — returns structured list of dicts (testable without CSV parsing)
  to_csv_string()        — formats that list as a downloadable CSV with document header

Pure function — no database access. Default pricing matches materials_template.xlsx.
"""
import csv
import io
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.skills.material_takeoff import MaterialLine, takeoff_summary


@dataclass
class PriceEntry:
    supplier_ref: str = ""
    price_per_unit: Optional[float] = None
    unit: str = ""
    currency: str = "EUR"


# Prices sourced from materials_template.xlsx (EUR, indicative)
MATERIAL_PRICES: dict[str, PriceEntry] = {
    "KVH C24 47×147 (Latvian)":          PriceEntry("LV-KVH-C24-147",    0.85,  "m",  "EUR"),
    "KVH C24 47×195 (Latvian)":          PriceEntry("LV-KVH-C24-195",    1.10,  "m",  "EUR"),
    "KVH C24 47×220 (Latvian)":          PriceEntry("LV-KVH-C24-220",    1.25,  "m",  "EUR"),
    "KVH C24 47×97 Noggin (Latvian)":    PriceEntry("LV-KVH-C24-97",     0.55,  "m",  "EUR"),
    "OSB/3 12mm (Egger)":                PriceEntry("EGGER-OSB3-12",      8.50,  "m2", "EUR"),
    "OSB/3 18mm floor (Egger)":          PriceEntry("EGGER-OSB3-18",     12.00,  "m2", "EUR"),
    "Rockwool Flexi 45 (between-stud)":  PriceEntry("RW-FLEXI-45",        6.80,  "m2", "EUR"),
    "Rockwool Flexi 100":                PriceEntry("RW-FLEXI-100",        9.40,  "m2", "EUR"),
    "Rockwool Frontrock Max E 100":      PriceEntry("RW-FRONTROCK-100",   18.50,  "m2", "EUR"),
    "Paroc eXtra 100 (between-rafter)":  PriceEntry("PAROC-EXTRA-100",    8.20,  "m2", "EUR"),
    "ISOVER Multimax 30 (roof)":         PriceEntry("ISOVER-MM30",         7.90,  "m2", "EUR"),
    "Kingspan Kooltherm K15 50mm":       PriceEntry("KS-K15-50",          22.00,  "m2", "EUR"),
    "Kingspan Kooltherm K15 80mm":       PriceEntry("KS-K15-80",          30.00,  "m2", "EUR"),
    "Kingspan Kooltherm K15 100mm":      PriceEntry("KS-K15-100",         36.00,  "m2", "EUR"),
    "Gyproc Standard 12.5mm":           PriceEntry("GYPROC-STD-125",       4.50,  "m2", "EUR"),
    "Gyproc FireLine 15mm":              PriceEntry("GYPROC-FL-15",         5.80,  "m2", "EUR"),
    "Siga Majrex 200 VCL":               PriceEntry("SIGA-MAJREX-200",     1.85,  "m2", "EUR"),
    "Tyvek Housewrap Breather":          PriceEntry("TYVEK-HW",             1.40,  "m2", "EUR"),
    "Rockwool Acoustic 45 (party wall)": PriceEntry("RW-ACOUSTIC-45",      7.20,  "m2", "EUR"),
    "Latvian Spruce Feather-edge 21mm":  PriceEntry("LV-SPRUCE-FE-21",     9.50,  "m2", "EUR"),
    "Cembrit Patina Fibre-cement":       PriceEntry("CEMBRIT-PATINA",      32.00,  "m2", "EUR"),
}


def procurement_schedule(
    lines: list[MaterialLine],
    pricing: dict[str, PriceEntry] | None = None,
) -> list[dict]:
    """
    Build a procurement schedule from take-off lines.

    Returns a list of dicts, one per unique material, sorted alphabetically.
    Each dict has:
      item           sequential row number (int)
      material       material name
      supplier_ref   supplier catalogue code (str, empty if unknown)
      qty_net        net quantity before waste
      qty_order      order quantity (net × waste)
      unit           "m2" or "lm"
      unit_price     float | None
      est_cost       float | None  (qty_order × unit_price)
      currency       "EUR" or as specified in PriceEntry
    """
    if pricing is None:
        pricing = MATERIAL_PRICES

    summary = takeoff_summary(lines)
    rows = []

    for i, mat in enumerate(summary["materials"], start=1):
        name = mat["material"]
        qty_order = mat["quantity"]
        unit = mat["unit"]
        qty_net = round(
            sum(l.quantity_net for l in lines if l.material_name == name), 3
        )

        p = pricing.get(name)
        supplier_ref = p.supplier_ref if p else ""
        unit_price: Optional[float] = None
        est_cost: Optional[float] = None
        currency = "EUR"

        if p and p.price_per_unit is not None:
            unit_price = p.price_per_unit
            est_cost = round(qty_order * p.price_per_unit, 2)
            currency = p.currency

        rows.append({
            "item":         i,
            "material":     name,
            "supplier_ref": supplier_ref,
            "qty_net":      qty_net,
            "qty_order":    qty_order,
            "unit":         unit,
            "unit_price":   unit_price,
            "est_cost":     est_cost,
            "currency":     currency,
        })

    return rows


def schedule_total(rows: list[dict]) -> Optional[float]:
    """Sum est_cost across all rows. Returns None if no rows have pricing."""
    costs = [r["est_cost"] for r in rows if r["est_cost"] is not None]
    return round(sum(costs), 2) if costs else None


def to_csv_string(
    rows: list[dict],
    pod_spec: dict,
    build_up_preset: str = "nordic_standard",
    generated_at: str | None = None,
) -> str:
    """
    Format a procurement schedule as a UTF-8 CSV string.

    Parameters
    ----------
    rows            Output from procurement_schedule().
    pod_spec        Dict with width_m, length_m, wall_height_m, roof_type, roof_pitch_deg.
    build_up_preset Label string for the document header.
    generated_at    ISO date string, defaults to today.
    """
    if generated_at is None:
        generated_at = date.today().isoformat()

    buf = io.StringIO()
    w = csv.writer(buf)

    # ── Document header ───────────────────────────────────────────────────────
    w.writerow(["Pod Manufacturing — Procurement Schedule"])
    w.writerow(["Generated", generated_at])
    w.writerow([
        "Pod",
        (
            f"{pod_spec.get('width_m')}m × "
            f"{pod_spec.get('length_m')}m × "
            f"{pod_spec.get('wall_height_m')}m  "
            f"{pod_spec.get('roof_type', '')}  "
            f"{pod_spec.get('roof_pitch_deg', '')}°"
        ),
    ])
    w.writerow(["Build-up", build_up_preset])
    w.writerow([])

    # ── Column headers ────────────────────────────────────────────────────────
    w.writerow([
        "#",
        "Material",
        "Supplier Ref",
        "Net Qty",
        "Order Qty",
        "Unit",
        "Unit Price (EUR)",
        "Est. Cost (EUR)",
    ])

    # ── Data rows ─────────────────────────────────────────────────────────────
    for row in rows:
        w.writerow([
            row["item"],
            row["material"],
            row["supplier_ref"],
            row["qty_net"],
            row["qty_order"],
            row["unit"],
            f"{row['unit_price']:.2f}" if row["unit_price"] is not None else "",
            f"{row['est_cost']:.2f}"   if row["est_cost"]   is not None else "",
        ])

    # ── Summary footer ────────────────────────────────────────────────────────
    total = schedule_total(rows)
    w.writerow([])
    if total is not None:
        w.writerow(["", "", "", "", "", "TOTAL (EUR)", "", f"{total:.2f}"])
        w.writerow([])
    w.writerow(["", "Prices are indicative. Verify with suppliers before placing orders."])

    return buf.getvalue()
