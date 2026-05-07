"""Tests for the material take-off skill."""
import math
import pytest

from app.skills.element_decomposer import OpeningSpec, decompose_pod
from app.skills.material_takeoff import (
    BuildUpSpec,
    LayerSpec,
    MaterialLine,
    TakeoffError,
    NORDIC_STANDARD,
    NORDIC_WALL,
    NORDIC_FLOOR,
    NORDIC_ROOF,
    takeoff,
    takeoff_summary,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def lines_for(label: str, mat: str, lines: list[MaterialLine]) -> list[MaterialLine]:
    return [l for l in lines if l.element_label == label and l.material_name == mat]

def first(label: str, mat: str, lines: list[MaterialLine]) -> MaterialLine:
    return lines_for(label, mat, lines)[0]


# ── Wall framing ──────────────────────────────────────────────────────────────

def test_wall_stud_count_long_wall():
    # 6.0m span at 600mm c/c → ceil(6.0/0.6)+1 = 11 studs
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="flat")
    spec = BuildUpSpec("ExternalWall", "test", [
        LayerSpec("Stud", "framing", spacing_mm=600),
    ])
    ls = takeoff(els, [spec])
    n = first("wall_N", "Stud", ls)
    expected_studs = math.ceil(6.0 / 0.6) + 1   # = 11
    assert n.unit == "lm"
    assert n.quantity_net == pytest.approx(expected_studs * 2.7, rel=1e-4)

def test_wall_stud_count_short_wall():
    # 3.0m span at 600mm c/c → ceil(3.0/0.6)+1 = 6 studs
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="flat")
    spec = BuildUpSpec("ExternalWall", "test", [
        LayerSpec("Stud", "framing", spacing_mm=600),
    ])
    ls = takeoff(els, [spec])
    e = first("wall_E", "Stud", ls)
    expected_studs = math.ceil(3.0 / 0.6) + 1   # = 6
    assert e.quantity_net == pytest.approx(expected_studs * 2.7, rel=1e-4)

def test_wall_plate_length():
    # Two plates (top + sole) per wall = 2 × span
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="flat")
    spec = BuildUpSpec("ExternalWall", "test", [
        LayerSpec("Plate", "plate"),
    ])
    ls = takeoff(els, [spec])
    n = first("wall_N", "Plate", ls)
    assert n.unit == "lm"
    assert n.quantity_net == pytest.approx(2 * 6.0, rel=1e-4)

def test_wall_board_area():
    # Continuous layers use area_gross_m2
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="flat")
    spec = BuildUpSpec("ExternalWall", "test", [
        LayerSpec("OSB", "board"),
    ])
    ls = takeoff(els, [spec])
    n = first("wall_N", "OSB", ls)
    assert n.unit == "m2"
    assert n.quantity_net == pytest.approx(6.0 * 2.7, rel=1e-4)

def test_wall_waste_applied():
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="flat")
    spec = BuildUpSpec("ExternalWall", "test", [
        LayerSpec("OSB", "board", waste_factor=1.10),
    ])
    ls = takeoff(els, [spec])
    n = first("wall_N", "OSB", ls)
    assert n.quantity == pytest.approx(n.quantity_net * 1.10, rel=1e-4)


# ── Floor framing ─────────────────────────────────────────────────────────────

def test_floor_joist_count():
    # 3×6 floor; joists span 3.0m, spaced at 400mm along 6.0m
    # ceil(6.0/0.4)+1 = 16 joists
    els = decompose_pod(3.0, 6.0, 2.7)
    spec = BuildUpSpec("Floor", "test", [
        LayerSpec("Joist", "framing", spacing_mm=400),
    ])
    ls = takeoff(els, [spec])
    f = first("floor", "Joist", ls)
    expected = (math.ceil(6.0 / 0.4) + 1) * 3.0
    assert f.unit == "lm"
    assert f.quantity_net == pytest.approx(expected, rel=1e-4)

def test_floor_rim_joist():
    # Rim/header = perimeter = 2×(3+6) = 18 lm
    els = decompose_pod(3.0, 6.0, 2.7)
    spec = BuildUpSpec("Floor", "test", [
        LayerSpec("Rim", "plate"),
    ])
    ls = takeoff(els, [spec])
    f = first("floor", "Rim", ls)
    assert f.quantity_net == pytest.approx(2 * (3.0 + 6.0), rel=1e-4)

def test_floor_board_area():
    els = decompose_pod(3.0, 6.0, 2.7)
    spec = BuildUpSpec("Floor", "test", [
        LayerSpec("Deck", "board"),
    ])
    ls = takeoff(els, [spec])
    f = first("floor", "Deck", ls)
    assert f.unit == "m2"
    assert f.quantity_net == pytest.approx(3.0 * 6.0, rel=1e-4)


# ── Roof framing ──────────────────────────────────────────────────────────────

def test_duo_pitch_rafter_lm():
    width, length, pitch = 3.0, 6.0, 15.0
    pitch_rad = math.radians(pitch)
    half_w = width / 2
    rafter_span = half_w / math.cos(pitch_rad)
    count_per_side = math.ceil(length / 0.6) + 1   # 600mm spacing
    expected = 2 * count_per_side * rafter_span

    els = decompose_pod(width, length, 2.7, roof_type="duo_pitch", roof_pitch_deg=pitch)
    spec = BuildUpSpec("Roof", "test", [
        LayerSpec("Rafter", "framing", spacing_mm=600),
    ])
    ls = takeoff(els, [spec])
    r = first("roof", "Rafter", ls)
    assert r.unit == "lm"
    assert r.quantity_net == pytest.approx(expected, rel=1e-3)

def test_mono_pitch_rafter_lm():
    width, length, pitch = 4.0, 8.0, 12.0
    pitch_rad = math.radians(pitch)
    rafter_span = width / math.cos(pitch_rad)
    count = math.ceil(length / 0.6) + 1
    expected = count * rafter_span

    els = decompose_pod(width, length, 2.7, roof_type="mono_pitch", roof_pitch_deg=pitch)
    spec = BuildUpSpec("Roof", "test", [
        LayerSpec("Rafter", "framing", spacing_mm=600),
    ])
    ls = takeoff(els, [spec])
    r = first("roof", "Rafter", ls)
    assert r.quantity_net == pytest.approx(expected, rel=1e-3)

def test_flat_roof_joist_lm():
    # Flat roof: joists span width, spaced along length
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="flat")
    spec = BuildUpSpec("Roof", "test", [
        LayerSpec("Joist", "framing", spacing_mm=400),
    ])
    ls = takeoff(els, [spec])
    r = first("roof", "Joist", ls)
    count = math.ceil(6.0 / 0.4) + 1
    expected = count * 3.0
    assert r.quantity_net == pytest.approx(expected, rel=1e-3)

def test_roof_deck_area_is_slope_area():
    # The roof element area_gross_m2 is already sloped — take-off should use it
    width, length, pitch = 3.0, 6.0, 15.0
    half_w = width / 2
    slope_area = 2 * (half_w / math.cos(math.radians(pitch))) * length

    els = decompose_pod(width, length, 2.7, roof_type="duo_pitch", roof_pitch_deg=pitch)
    spec = BuildUpSpec("Roof", "test", [
        LayerSpec("Deck", "board"),
    ])
    ls = takeoff(els, [spec])
    r = first("roof", "Deck", ls)
    assert r.quantity_net == pytest.approx(slope_area, rel=1e-3)


# ── Openings and skipped elements ────────────────────────────────────────────

def test_openings_produce_no_lines():
    openings = [OpeningSpec(wall="S", type="door", width_m=0.9, height_m=2.1)]
    els = decompose_pod(3.0, 6.0, 2.7, openings=openings)
    spec = BuildUpSpec("ExternalWall", "test", [
        LayerSpec("OSB", "board"),
    ])
    ls = takeoff(els, [spec])
    opening_lines = [l for l in ls if "opening" in l.element_label]
    assert opening_lines == []

def test_element_type_without_buildup_skipped():
    els = decompose_pod(3.0, 6.0, 2.7)
    # only floor spec → walls and roof produce no lines
    spec = BuildUpSpec("Floor", "test", [LayerSpec("Deck", "board")])
    ls = takeoff(els, [spec])
    assert all(l.element_label == "floor" for l in ls)


# ── Validation ────────────────────────────────────────────────────────────────

def test_framing_without_spacing_raises():
    els = decompose_pod(3.0, 6.0, 2.7)
    spec = BuildUpSpec("ExternalWall", "test", [
        LayerSpec("Stud", "framing", spacing_mm=0),  # missing spacing
    ])
    with pytest.raises(TakeoffError):
        takeoff(els, [spec])


# ── Summary ───────────────────────────────────────────────────────────────────

def test_summary_groups_by_material():
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="flat")
    spec = BuildUpSpec("ExternalWall", "test", [
        LayerSpec("OSB", "board"),
    ])
    ls = takeoff(els, [spec])
    s = takeoff_summary(ls)
    # 4 walls × 1 line each = 4 lines
    assert s["line_count"] == 4
    # all collapsed into one material row
    mats = {m["material"]: m for m in s["materials"]}
    assert "OSB" in mats
    # total OSB = sum of all 4 wall areas
    total_walls = sum(l.quantity for l in ls)
    assert mats["OSB"]["quantity"] == pytest.approx(total_walls, rel=1e-4)

def test_summary_sorted_by_name():
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="flat")
    spec = BuildUpSpec("ExternalWall", "test", [
        LayerSpec("Zinc",    "board"),
        LayerSpec("Alpha",   "board"),
        LayerSpec("Membrane","membrane"),
    ])
    ls = takeoff(els, [spec])
    s = takeoff_summary(ls)
    names = [m["material"] for m in s["materials"]]
    assert names == sorted(names)


# ── Nordic standard build-ups ─────────────────────────────────────────────────

def test_nordic_standard_runs_without_error():
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="duo_pitch", roof_pitch_deg=15.0)
    ls = takeoff(els, NORDIC_STANDARD)
    assert len(ls) > 0

def test_nordic_standard_all_element_types_covered():
    els = decompose_pod(3.0, 6.0, 2.7)
    ls = takeoff(els, NORDIC_STANDARD)
    labels = {l.element_label for l in ls}
    assert "floor" in labels
    assert "roof" in labels
    assert "wall_N" in labels

def test_nordic_wall_has_framing_and_plates():
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="flat")
    ls = takeoff(els, [NORDIC_WALL])
    wall_n = [l for l in ls if l.element_label == "wall_N"]
    layer_types = {l.layer_type for l in wall_n}
    assert "framing" in layer_types
    assert "plate" in layer_types
    assert "board" in layer_types
    assert "membrane" in layer_types

def test_nordic_summary_has_osb_and_kvh():
    els = decompose_pod(3.0, 6.0, 2.7)
    ls = takeoff(els, NORDIC_STANDARD)
    s = takeoff_summary(ls)
    mat_names = {m["material"] for m in s["materials"]}
    assert "OSB/3 12mm (Egger)" in mat_names
    assert "KVH C24 47×147 (Latvian)" in mat_names

def test_nordic_kvh_unit_is_lm():
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="flat")
    ls = takeoff(els, [NORDIC_WALL])
    kvh_lines = [l for l in ls if l.material_name == "KVH C24 47×147 (Latvian)"]
    assert all(l.unit == "lm" for l in kvh_lines)


# ── Regression: real pod sizes ────────────────────────────────────────────────

def test_6x3_studio_pod_nordic():
    openings = [
        OpeningSpec(wall="S", type="door",   width_m=0.9, height_m=2.1),
        OpeningSpec(wall="S", type="window", width_m=1.2, height_m=1.1, sill_height_m=0.9),
        OpeningSpec(wall="N", type="window", width_m=0.6, height_m=0.6, sill_height_m=1.2),
    ]
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="duo_pitch", roof_pitch_deg=15.0, openings=openings)
    ls = takeoff(els, NORDIC_STANDARD)
    s = takeoff_summary(ls)

    assert s["line_count"] > 0
    # Every material in summary has a positive quantity
    for mat in s["materials"]:
        assert mat["quantity"] > 0

def test_8x4_one_bed_pod_nordic():
    openings = [
        OpeningSpec(wall="S", type="door",   width_m=0.9, height_m=2.1),
        OpeningSpec(wall="S", type="window", width_m=1.4, height_m=1.2, sill_height_m=0.9),
        OpeningSpec(wall="N", type="window", width_m=1.4, height_m=1.2, sill_height_m=0.9),
        OpeningSpec(wall="E", type="window", width_m=0.6, height_m=0.9, sill_height_m=1.0),
    ]
    els = decompose_pod(4.0, 8.0, 2.7, roof_type="duo_pitch", roof_pitch_deg=15.0, openings=openings)
    ls = takeoff(els, NORDIC_STANDARD)
    s = takeoff_summary(ls)

    # Larger pod → more material than the 6×3
    els_small = decompose_pod(3.0, 6.0, 2.7, roof_type="duo_pitch", roof_pitch_deg=15.0)
    ls_small = takeoff(els_small, NORDIC_STANDARD)
    s_small = takeoff_summary(ls_small)

    # Total lines should be equal (same number of elements × layers)
    assert s["line_count"] == s_small["line_count"]

    # OSB area should be larger for the bigger pod
    osb_large = next(m["quantity"] for m in s["materials"] if m["material"] == "OSB/3 12mm (Egger)")
    osb_small = next(m["quantity"] for m in s_small["materials"] if m["material"] == "OSB/3 12mm (Egger)")
    assert osb_large > osb_small
