"""Tests for the element decomposer skill."""
import math
import pytest

from app.skills.element_decomposer import (
    DecomposedElement,
    DecompositionError,
    OpeningSpec,
    decompose_pod,
    total_external_area,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def get(elements: list[DecomposedElement], label: str) -> DecomposedElement:
    return next(e for e in elements if e.label == label)

def by_type(elements, typ):
    return [e for e in elements if e.type == typ]


# ── Floor ────────────────────────────────────────────────────────────────────

def test_floor_area():
    els = decompose_pod(3.0, 6.0, 2.7)
    floor = get(els, "floor")
    assert floor.area_gross_m2 == pytest.approx(18.0)
    assert floor.area_net_m2   == pytest.approx(18.0)

def test_floor_perimeter():
    els = decompose_pod(3.0, 6.0, 2.7)
    floor = get(els, "floor")
    assert floor.perimeter_m == pytest.approx(2 * (3 + 6))


# ── Flat roof ─────────────────────────────────────────────────────────────────

def test_flat_roof_area():
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="flat")
    roof = get(els, "roof")
    assert roof.area_gross_m2 == pytest.approx(3.0 * 6.0)

def test_flat_roof_no_gable_triangle():
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="flat")
    for face in ("E", "W"):
        wall = get(els, f"wall_{face}")
        assert wall.geometry["gable_triangle_area_m2"] == pytest.approx(0.0)


# ── Duo-pitch roof ────────────────────────────────────────────────────────────

def test_duo_pitch_roof_area():
    width, length, pitch = 3.0, 6.0, 15.0
    half = width / 2
    expected = 2 * (half / math.cos(math.radians(pitch))) * length
    els = decompose_pod(width, length, 2.7, roof_type="duo_pitch", roof_pitch_deg=pitch)
    roof = get(els, "roof")
    assert roof.area_gross_m2 == pytest.approx(expected, rel=1e-4)

def test_duo_pitch_gable_walls_have_triangle():
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="duo_pitch", roof_pitch_deg=15.0)
    for face in ("E", "W"):
        wall = get(els, f"wall_{face}")
        assert wall.geometry["gable_triangle_area_m2"] > 0

def test_duo_pitch_gable_walls_symmetric():
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="duo_pitch", roof_pitch_deg=20.0)
    e_wall = get(els, "wall_E")
    w_wall = get(els, "wall_W")
    assert e_wall.area_gross_m2 == pytest.approx(w_wall.area_gross_m2)

def test_duo_pitch_steeper_pitch_larger_roof():
    shallow = decompose_pod(3.0, 6.0, 2.7, roof_type="duo_pitch", roof_pitch_deg=10.0)
    steep   = decompose_pod(3.0, 6.0, 2.7, roof_type="duo_pitch", roof_pitch_deg=30.0)
    assert get(steep, "roof").area_gross_m2 > get(shallow, "roof").area_gross_m2

def test_duo_pitch_zero_pitch_equals_flat():
    duo  = decompose_pod(3.0, 6.0, 2.7, roof_type="duo_pitch",  roof_pitch_deg=0.0)
    flat = decompose_pod(3.0, 6.0, 2.7, roof_type="flat")
    assert get(duo, "roof").area_gross_m2 == pytest.approx(get(flat, "roof").area_gross_m2)


# ── Mono-pitch roof ───────────────────────────────────────────────────────────

def test_mono_pitch_roof_area():
    width, length, pitch = 4.0, 8.0, 12.0
    expected = (width / math.cos(math.radians(pitch))) * length
    els = decompose_pod(width, length, 2.7, roof_type="mono_pitch", roof_pitch_deg=pitch)
    roof = get(els, "roof")
    assert roof.area_gross_m2 == pytest.approx(expected, rel=1e-4)

def test_mono_pitch_w_wall_higher_than_e_wall():
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="mono_pitch", roof_pitch_deg=15.0)
    e = get(els, "wall_E")
    w = get(els, "wall_W")
    assert w.area_gross_m2 > e.area_gross_m2


# ── Walls ─────────────────────────────────────────────────────────────────────

def test_long_walls_correct_gross_area():
    els = decompose_pod(3.0, 6.0, 2.7)
    for face in ("N", "S"):
        wall = get(els, f"wall_{face}")
        assert wall.area_gross_m2 == pytest.approx(6.0 * 2.7)

def test_short_walls_at_least_rect_area():
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="duo_pitch")
    for face in ("E", "W"):
        wall = get(els, f"wall_{face}")
        assert wall.area_gross_m2 >= 3.0 * 2.7


# ── Openings ──────────────────────────────────────────────────────────────────

def test_openings_subtract_from_net():
    o = OpeningSpec(wall="N", type="window", width_m=1.2, height_m=1.1, sill_height_m=0.9)
    els = decompose_pod(3.0, 6.0, 2.7, openings=[o])
    n = get(els, "wall_N")
    assert n.area_gross_m2 == pytest.approx(6.0 * 2.7)
    assert n.area_net_m2   == pytest.approx(6.0 * 2.7 - 1.2 * 1.1)

def test_openings_gross_unchanged():
    """Gross area is never affected by openings — net only."""
    o = OpeningSpec(wall="N", type="door", width_m=0.9, height_m=2.1)
    els = decompose_pod(3.0, 6.0, 2.7, openings=[o])
    n = get(els, "wall_N")
    assert n.area_gross_m2 == pytest.approx(6.0 * 2.7)

def test_multiple_openings_same_wall():
    openings = [
        OpeningSpec(wall="S", type="window", width_m=1.0, height_m=1.0),
        OpeningSpec(wall="S", type="window", width_m=1.2, height_m=1.1),
    ]
    els = decompose_pod(3.0, 6.0, 2.7, openings=openings)
    s = get(els, "wall_S")
    expected_net = 6.0 * 2.7 - (1.0 * 1.0) - (1.2 * 1.1)
    assert s.area_net_m2 == pytest.approx(expected_net)

def test_openings_on_different_walls():
    openings = [
        OpeningSpec(wall="N", type="window", width_m=1.2, height_m=1.1),
        OpeningSpec(wall="S", type="door",   width_m=0.9, height_m=2.1),
    ]
    els = decompose_pod(3.0, 6.0, 2.7, openings=openings)
    n = get(els, "wall_N")
    s = get(els, "wall_S")
    assert n.area_net_m2 == pytest.approx(6.0 * 2.7 - 1.2 * 1.1)
    assert s.area_net_m2 == pytest.approx(6.0 * 2.7 - 0.9 * 2.1)

def test_opening_elements_present_in_output():
    openings = [
        OpeningSpec(wall="N", type="window", width_m=1.2, height_m=1.1),
        OpeningSpec(wall="S", type="door",   width_m=0.9, height_m=2.1),
    ]
    els = decompose_pod(3.0, 6.0, 2.7, openings=openings)
    assert len(by_type(els, "Opening")) == 2

def test_opening_area_stored_correctly():
    o = OpeningSpec(wall="E", type="window", width_m=0.6, height_m=0.9, sill_height_m=1.1)
    els = decompose_pod(3.0, 6.0, 2.7, openings=[o])
    op_el = get(els, "opening_window_1")
    assert op_el.area_gross_m2 == pytest.approx(0.6 * 0.9)
    assert op_el.geometry["sill_height_m"] == pytest.approx(1.1)


# ── Element counts ────────────────────────────────────────────────────────────

def test_element_counts_no_openings():
    els = decompose_pod(3.0, 6.0, 2.7)
    assert len(by_type(els, "Floor"))        == 1
    assert len(by_type(els, "Roof"))         == 1
    assert len(by_type(els, "ExternalWall")) == 4
    assert len(by_type(els, "Opening"))      == 0

def test_element_counts_with_openings():
    openings = [OpeningSpec(wall="N", type="window", width_m=1.0, height_m=1.0)] * 3
    els = decompose_pod(3.0, 6.0, 2.7, openings=openings)
    assert len(by_type(els, "Opening")) == 3

def test_element_order():
    """Elements always come back in: floor, roof, wall_N, wall_S, wall_E, wall_W, openings."""
    els = decompose_pod(3.0, 6.0, 2.7, openings=[
        OpeningSpec(wall="N", type="window", width_m=1.0, height_m=1.0)
    ])
    labels = [e.label for e in els]
    assert labels[0] == "floor"
    assert labels[1] == "roof"
    assert "wall_N" in labels[2:6]
    assert "wall_S" in labels[2:6]
    assert labels[-1] == "opening_window_1"


# ── total_external_area summary ───────────────────────────────────────────────

def test_summary_flat_pod():
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="flat")
    s = total_external_area(els)
    assert s["floor_m2"]      == pytest.approx(18.0)
    assert s["roof_m2"]       == pytest.approx(18.0)
    assert s["opening_count"] == 0
    assert s["wall_gross_m2"] > 0

def test_summary_opening_count():
    openings = [
        OpeningSpec(wall="N", type="window", width_m=1.0, height_m=1.0),
        OpeningSpec(wall="S", type="door",   width_m=0.9, height_m=2.1),
    ]
    els = decompose_pod(3.0, 6.0, 2.7, openings=openings)
    assert total_external_area(els)["opening_count"] == 2


# ── Validation / error handling ───────────────────────────────────────────────

def test_negative_dimension_raises():
    with pytest.raises(DecompositionError):
        decompose_pod(-1.0, 6.0, 2.7)

def test_zero_height_raises():
    with pytest.raises(DecompositionError):
        decompose_pod(3.0, 6.0, 0.0)

def test_invalid_pitch_raises():
    with pytest.raises(DecompositionError):
        decompose_pod(3.0, 6.0, 2.7, roof_pitch_deg=95.0)

def test_negative_sill_height_raises():
    with pytest.raises(DecompositionError):
        decompose_pod(3.0, 6.0, 2.7, openings=[
            OpeningSpec(wall="N", type="window", width_m=1.0, height_m=1.0, sill_height_m=-0.1)
        ])

def test_unknown_roof_type_raises():
    with pytest.raises(DecompositionError):
        decompose_pod(3.0, 6.0, 2.7, roof_type="mansard")  # type: ignore


# ── Regression: real pod sizes ────────────────────────────────────────────────

def test_6x3_studio_pod():
    """Typical garden room / studio pod."""
    openings = [
        OpeningSpec(wall="S", type="door",   width_m=0.9, height_m=2.1),
        OpeningSpec(wall="S", type="window", width_m=1.2, height_m=1.1, sill_height_m=0.9),
        OpeningSpec(wall="N", type="window", width_m=0.6, height_m=0.6, sill_height_m=1.2),
    ]
    els = decompose_pod(3.0, 6.0, 2.7, roof_type="duo_pitch", roof_pitch_deg=15.0, openings=openings)
    s = total_external_area(els)
    assert s["floor_m2"]      == pytest.approx(18.0)
    assert s["opening_count"] == 3
    assert s["wall_net_m2"]   < s["wall_gross_m2"]

def test_8x4_one_bed_pod():
    """1-bed pod."""
    openings = [
        OpeningSpec(wall="S", type="door",   width_m=0.9, height_m=2.1),
        OpeningSpec(wall="S", type="window", width_m=1.4, height_m=1.2, sill_height_m=0.9),
        OpeningSpec(wall="N", type="window", width_m=1.4, height_m=1.2, sill_height_m=0.9),
        OpeningSpec(wall="E", type="window", width_m=0.6, height_m=0.9, sill_height_m=1.0),
    ]
    els = decompose_pod(4.0, 8.0, 2.7, roof_type="duo_pitch", roof_pitch_deg=15.0, openings=openings)
    s = total_external_area(els)
    assert s["floor_m2"] == pytest.approx(32.0)
    assert s["opening_count"] == 4
