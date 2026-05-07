"""Tests for the procurement CSV skill."""
import csv
import io
import pytest

from app.skills.element_decomposer import OpeningSpec, decompose_pod
from app.skills.material_takeoff import NORDIC_STANDARD, takeoff, takeoff_summary
from app.skills.procurement_csv import (
    MATERIAL_PRICES,
    PriceEntry,
    procurement_schedule,
    schedule_total,
    to_csv_string,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def studio_lines():
    """Take-off lines for a standard 3×6 studio pod."""
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="duo_pitch", roof_pitch_deg=15.0)
    return takeoff(els, NORDIC_STANDARD)

@pytest.fixture
def large_lines():
    """Take-off lines for a larger 4×8 pod."""
    els = decompose_pod(4.0, 8.0, 2.7, roof_type="duo_pitch", roof_pitch_deg=15.0)
    return takeoff(els, NORDIC_STANDARD)

@pytest.fixture
def pod_spec_3x6():
    return {"width_m": 3.0, "length_m": 6.0, "wall_height_m": 2.7,
            "roof_type": "duo_pitch", "roof_pitch_deg": 15.0}


# ── procurement_schedule() — data correctness ─────────────────────────────────

def test_row_count_matches_unique_materials(studio_lines):
    rows = procurement_schedule(studio_lines)
    summary = takeoff_summary(studio_lines)
    assert len(rows) == len(summary["materials"])

def test_rows_sorted_alphabetically(studio_lines):
    rows = procurement_schedule(studio_lines)
    names = [r["material"] for r in rows]
    assert names == sorted(names)

def test_item_numbers_sequential(studio_lines):
    rows = procurement_schedule(studio_lines)
    assert [r["item"] for r in rows] == list(range(1, len(rows) + 1))

def test_qty_order_matches_summary(studio_lines):
    rows = procurement_schedule(studio_lines)
    summary_by_name = {m["material"]: m["quantity"] for m in takeoff_summary(studio_lines)["materials"]}
    for row in rows:
        assert row["qty_order"] == pytest.approx(summary_by_name[row["material"]], rel=1e-4)

def test_qty_net_less_than_qty_order(studio_lines):
    rows = procurement_schedule(studio_lines)
    for row in rows:
        assert row["qty_net"] <= row["qty_order"]

def test_unit_is_m2_or_lm(studio_lines):
    rows = procurement_schedule(studio_lines)
    for row in rows:
        assert row["unit"] in ("m2", "lm")


# ── pricing ───────────────────────────────────────────────────────────────────

def test_known_material_has_supplier_ref(studio_lines):
    rows = procurement_schedule(studio_lines)
    osb = next(r for r in rows if r["material"] == "OSB/3 12mm (Egger)")
    assert osb["supplier_ref"] == "EGGER-OSB3-12"

def test_known_material_has_unit_price(studio_lines):
    rows = procurement_schedule(studio_lines)
    osb = next(r for r in rows if r["material"] == "OSB/3 12mm (Egger)")
    assert osb["unit_price"] == pytest.approx(8.50)

def test_est_cost_is_qty_times_unit_price(studio_lines):
    rows = procurement_schedule(studio_lines)
    for row in rows:
        if row["unit_price"] is not None:
            expected = round(row["qty_order"] * row["unit_price"], 2)
            assert row["est_cost"] == pytest.approx(expected, rel=1e-4)

def test_unknown_material_has_no_price():
    """Materials not in the pricing dict show None for price fields."""
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="flat")
    from app.skills.material_takeoff import BuildUpSpec, LayerSpec, takeoff
    custom = BuildUpSpec("ExternalWall", "test", [
        LayerSpec("Mystery Material XYZ", "board"),
    ])
    lines = takeoff(els, [custom])
    rows = procurement_schedule(lines, pricing=MATERIAL_PRICES)
    mystery = next(r for r in rows if r["material"] == "Mystery Material XYZ")
    assert mystery["unit_price"] is None
    assert mystery["est_cost"] is None

def test_custom_pricing_overrides_defaults(studio_lines):
    custom = {"OSB/3 12mm (Egger)": PriceEntry("CUSTOM-REF", 99.99, "m2", "EUR")}
    rows = procurement_schedule(studio_lines, pricing=custom)
    osb = next((r for r in rows if r["material"] == "OSB/3 12mm (Egger)"), None)
    if osb:
        assert osb["unit_price"] == pytest.approx(99.99)

def test_empty_pricing_dict_gives_no_prices(studio_lines):
    rows = procurement_schedule(studio_lines, pricing={})
    for row in rows:
        assert row["unit_price"] is None
        assert row["est_cost"] is None


# ── schedule_total() ──────────────────────────────────────────────────────────

def test_total_is_sum_of_est_costs(studio_lines):
    rows = procurement_schedule(studio_lines)
    expected = sum(r["est_cost"] for r in rows if r["est_cost"] is not None)
    assert schedule_total(rows) == pytest.approx(expected, rel=1e-4)

def test_total_is_none_when_no_pricing(studio_lines):
    rows = procurement_schedule(studio_lines, pricing={})
    assert schedule_total(rows) is None

def test_total_is_positive(studio_lines):
    rows = procurement_schedule(studio_lines)
    assert schedule_total(rows) > 0

def test_larger_pod_costs_more(studio_lines, large_lines):
    small_total = schedule_total(procurement_schedule(studio_lines))
    large_total = schedule_total(procurement_schedule(large_lines))
    assert large_total > small_total


# ── to_csv_string() — format correctness ─────────────────────────────────────

def _parse_data_rows(csv_string: str) -> list[dict]:
    """Extract the data rows from the CSV (after the blank line following headers)."""
    reader = csv.reader(io.StringIO(csv_string))
    rows = list(reader)
    # Find the header row (starts with "#")
    header_idx = next(i for i, r in enumerate(rows) if r and r[0] == "#")
    headers = rows[header_idx]
    data = []
    for row in rows[header_idx + 1:]:
        if not row or not row[0].isdigit():
            break
        data.append(dict(zip(headers, row)))
    return data

def test_csv_is_parseable(studio_lines, pod_spec_3x6):
    csv_str = to_csv_string(procurement_schedule(studio_lines), pod_spec_3x6)
    reader = csv.reader(io.StringIO(csv_str))
    rows = list(reader)
    assert len(rows) > 0

def test_csv_has_column_headers(studio_lines, pod_spec_3x6):
    csv_str = to_csv_string(procurement_schedule(studio_lines), pod_spec_3x6)
    assert "Material" in csv_str
    assert "Order Qty" in csv_str
    assert "Unit Price" in csv_str

def test_csv_contains_pod_dimensions(studio_lines, pod_spec_3x6):
    csv_str = to_csv_string(procurement_schedule(studio_lines), pod_spec_3x6)
    assert "3.0" in csv_str
    assert "6.0" in csv_str

def test_csv_data_row_count(studio_lines, pod_spec_3x6):
    rows = procurement_schedule(studio_lines)
    csv_str = to_csv_string(rows, pod_spec_3x6)
    data_rows = _parse_data_rows(csv_str)
    assert len(data_rows) == len(rows)

def test_csv_data_row_materials_match(studio_lines, pod_spec_3x6):
    rows = procurement_schedule(studio_lines)
    csv_str = to_csv_string(rows, pod_spec_3x6)
    data_rows = _parse_data_rows(csv_str)
    csv_materials = [r["Material"] for r in data_rows]
    expected_materials = [r["material"] for r in rows]
    assert csv_materials == expected_materials

def test_csv_has_total_row(studio_lines, pod_spec_3x6):
    rows = procurement_schedule(studio_lines)
    csv_str = to_csv_string(rows, pod_spec_3x6)
    assert "TOTAL" in csv_str

def test_csv_has_disclaimer(studio_lines, pod_spec_3x6):
    csv_str = to_csv_string(procurement_schedule(studio_lines), pod_spec_3x6)
    assert "indicative" in csv_str.lower()

def test_csv_custom_generated_at(studio_lines, pod_spec_3x6):
    csv_str = to_csv_string(
        procurement_schedule(studio_lines), pod_spec_3x6,
        generated_at="2026-01-15"
    )
    assert "2026-01-15" in csv_str

def test_csv_no_total_when_no_pricing(studio_lines, pod_spec_3x6):
    rows = procurement_schedule(studio_lines, pricing={})
    csv_str = to_csv_string(rows, pod_spec_3x6)
    assert "TOTAL" not in csv_str


# ── Regression: real pod ──────────────────────────────────────────────────────

def test_6x3_studio_full_schedule(pod_spec_3x6):
    openings = [
        OpeningSpec(wall="S", type="door",   width_m=0.9, height_m=2.1),
        OpeningSpec(wall="S", type="window", width_m=1.2, height_m=1.1, sill_height_m=0.9),
        OpeningSpec(wall="N", type="window", width_m=0.6, height_m=0.6, sill_height_m=1.2),
    ]
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="duo_pitch", roof_pitch_deg=15.0, openings=openings)
    lines = takeoff(els, NORDIC_STANDARD)
    rows = procurement_schedule(lines)
    csv_str = to_csv_string(rows, pod_spec_3x6)

    assert len(rows) > 0
    assert schedule_total(rows) > 0
    assert "OSB/3 12mm (Egger)" in csv_str
    assert "KVH C24 47×147 (Latvian)" in csv_str
