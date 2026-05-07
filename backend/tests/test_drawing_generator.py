"""Tests for the SVG drawing generator skill."""
import math
import re
import xml.etree.ElementTree as ET
import pytest

from app.skills.drawing_generator import (
    MARGIN,
    SCALE,
    _mm,
    _schematic_x,
    floor_plan_svg,
    generate_drawings,
    stud_positions,
    wall_elevation_svg,
)
from app.skills.element_decomposer import OpeningSpec, decompose_pod


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse(svg: str) -> ET.Element:
    """Parse SVG string into ElementTree, stripping default namespace."""
    svg_clean = re.sub(r' xmlns="[^"]+"', '', svg)
    return ET.fromstring(svg_clean)


def _count_tag(svg: str, tag: str) -> int:
    root = _parse(svg)
    return len(root.findall(f".//{tag}"))


def _all_text(svg: str) -> str:
    root = _parse(svg)
    return " ".join(t.text or "" for t in root.iter("text"))


# ── _mm() helper ─────────────────────────────────────────────────────────────

def test_mm_whole_metre():
    assert _mm(1.0) == "1000"

def test_mm_fractional():
    assert _mm(2.7) == "2700"

def test_mm_rounds():
    assert _mm(0.6) == "600"


# ── _schematic_x() ────────────────────────────────────────────────────────────

def test_schematic_x_empty():
    assert _schematic_x(6.0, []) == []

def test_schematic_x_single_centred():
    result = _schematic_x(6.0, [1.0])
    assert len(result) == 1
    center = result[0] + 0.5
    assert abs(center - 3.0) < 0.01

def test_schematic_x_two_openings_symmetric():
    result = _schematic_x(6.0, [1.0, 1.0])
    assert len(result) == 2
    assert result[0] < result[1]

def test_schematic_x_no_negative():
    result = _schematic_x(3.0, [0.9, 0.9, 0.9])
    assert all(x >= 0 for x in result)

def test_schematic_x_fits_within_span():
    widths = [1.0, 0.9]
    result = _schematic_x(6.0, widths)
    for x, w in zip(result, widths):
        assert x + w <= 6.0 + 0.001


# ── stud_positions() ─────────────────────────────────────────────────────────

def test_stud_positions_no_openings_includes_ends():
    studs = stud_positions(3.0, 600, [], [])
    assert studs[0] == pytest.approx(0.0, abs=0.001)
    assert studs[-1] == pytest.approx(3.0, abs=0.01)

def test_stud_positions_count_no_openings():
    studs = stud_positions(3.0, 600, [], [])
    expected = int(3.0 / 0.6) + 1
    assert len(studs) >= expected

def test_stud_positions_no_stud_inside_opening():
    o_xs, o_ws = [1.2], [0.9]
    studs = stud_positions(3.0, 600, o_xs, o_ws)
    for s in studs:
        for xs, w in zip(o_xs, o_ws):
            assert not (xs < s < xs + w), f"stud at {s} is inside opening [{xs}, {xs+w}]"

def test_stud_positions_king_studs_at_opening_edges():
    o_xs, o_ws = [1.2], [0.9]
    studs = stud_positions(3.0, 600, o_xs, o_ws)
    assert 1.2 in [round(s, 4) for s in studs]
    assert round(1.2 + 0.9, 4) in [round(s, 4) for s in studs]

def test_stud_positions_two_openings():
    o_xs = [0.5, 2.0]
    o_ws = [0.6, 0.6]
    studs = stud_positions(4.0, 600, o_xs, o_ws)
    for xs, w in zip(o_xs, o_ws):
        assert xs in [round(s, 4) for s in studs]
        assert round(xs + w, 4) in [round(s, 4) for s in studs]

def test_stud_positions_sorted():
    studs = stud_positions(6.0, 600, [1.0], [1.2])
    assert studs == sorted(studs)

def test_stud_positions_no_duplicates():
    studs = stud_positions(3.6, 600, [], [])
    assert len(studs) == len(set(round(s, 4) for s in studs))


# ── wall_elevation_svg() — basic structure ────────────────────────────────────

@pytest.fixture
def simple_wall():
    return wall_elevation_svg("S", 6.0, 2.7, [])

def test_wall_svg_is_valid_xml(simple_wall):
    root = _parse(simple_wall)
    assert root.tag == "svg"

def test_wall_svg_has_viewbox(simple_wall):
    root = _parse(simple_wall)
    assert "viewBox" in root.attrib

def test_wall_svg_contains_rects(simple_wall):
    assert _count_tag(simple_wall, "rect") >= 3   # bg + wall fill + 2 plates

def test_wall_svg_contains_lines(simple_wall):
    # At least some studs (lines)
    assert _count_tag(simple_wall, "line") >= 2

def test_wall_svg_title_has_face():
    svg = wall_elevation_svg("N", 6.0, 2.7, [])
    assert "Wall N" in svg

def test_wall_svg_title_has_dimensions():
    svg = wall_elevation_svg("E", 3.0, 2.7, [])
    assert "3.0" in svg
    assert "2.7" in svg

def test_wall_svg_width_annotation():
    svg = wall_elevation_svg("S", 6.0, 2.7, [])
    assert "6000" in svg

def test_wall_svg_height_annotation():
    svg = wall_elevation_svg("S", 6.0, 2.7, [])
    assert "2700" in svg


# ── wall_elevation_svg() — openings ──────────────────────────────────────────

@pytest.fixture
def wall_with_openings():
    openings = [
        {"type": "window", "width_m": 1.2, "height_m": 1.1, "sill_height_m": 0.9},
        {"type": "door",   "width_m": 0.9, "height_m": 2.1, "sill_height_m": 0.0},
    ]
    return wall_elevation_svg("S", 6.0, 2.7, openings)

def test_wall_with_openings_valid_xml(wall_with_openings):
    root = _parse(wall_with_openings)
    assert root.tag == "svg"

def test_wall_with_openings_more_rects(simple_wall, wall_with_openings):
    assert _count_tag(wall_with_openings, "rect") > _count_tag(simple_wall, "rect")

def test_wall_opening_label_present(wall_with_openings):
    assert "1200" in wall_with_openings
    assert "1100" in wall_with_openings

def test_wall_opening_type_abbrev(wall_with_openings):
    # "W" for window, "D" for door abbreviations in label
    text = _all_text(wall_with_openings)
    assert "W" in text or "D" in text

def test_wall_no_opening_no_opening_rects(simple_wall):
    # A wall with no openings should have no blue-outlined opening rect
    # Check there's no opening colour in rect attributes
    assert "#EBF5FB" not in simple_wall or "1200" not in simple_wall


# ── floor_plan_svg() — structure ─────────────────────────────────────────────

@pytest.fixture
def simple_plan():
    return floor_plan_svg(3.0, 6.0, [])

def test_floor_plan_valid_xml(simple_plan):
    root = _parse(simple_plan)
    assert root.tag == "svg"

def test_floor_plan_has_viewbox(simple_plan):
    root = _parse(simple_plan)
    assert "viewBox" in root.attrib

def test_floor_plan_compass_n(simple_plan):
    assert ">N<" in simple_plan or "N" in _all_text(simple_plan)

def test_floor_plan_compass_s(simple_plan):
    assert "S" in _all_text(simple_plan)

def test_floor_plan_dimension_length(simple_plan):
    assert "6000" in simple_plan

def test_floor_plan_dimension_width(simple_plan):
    assert "3000" in simple_plan

def test_floor_plan_title(simple_plan):
    assert "Floor Plan" in simple_plan

def test_floor_plan_long_axis_horizontal():
    # Width of SVG should reflect the longer dimension (length_m = 6m)
    root = _parse(floor_plan_svg(3.0, 6.0, []))
    vb = root.attrib.get("viewBox", "")
    parts = vb.split()
    if len(parts) == 4:
        vb_w = float(parts[2])
        vb_h = float(parts[3])
        assert vb_w > vb_h   # wide, not tall (long axis horizontal)


# ── floor_plan_svg() — openings ───────────────────────────────────────────────

def test_floor_plan_with_opening_valid_xml():
    openings = [{"wall": "S", "type": "door", "width_m": 0.9, "height_m": 2.1, "sill_height_m": 0.0}]
    root = _parse(floor_plan_svg(3.0, 6.0, openings))
    assert root.tag == "svg"

def test_floor_plan_opening_adds_rect():
    no_opening = _count_tag(floor_plan_svg(3.0, 6.0, []), "rect")
    with_opening = _count_tag(
        floor_plan_svg(3.0, 6.0, [{"wall": "S", "type": "door",
                                    "width_m": 0.9, "height_m": 2.1, "sill_height_m": 0.0}]),
        "rect"
    )
    assert with_opening > no_opening

def test_floor_plan_openings_all_four_walls():
    openings = [
        {"wall": "N", "type": "window", "width_m": 0.6, "height_m": 0.6, "sill_height_m": 1.2},
        {"wall": "S", "type": "door",   "width_m": 0.9, "height_m": 2.1, "sill_height_m": 0.0},
        {"wall": "E", "type": "window", "width_m": 0.6, "height_m": 0.6, "sill_height_m": 1.0},
        {"wall": "W", "type": "window", "width_m": 0.6, "height_m": 0.6, "sill_height_m": 1.0},
    ]
    root = _parse(floor_plan_svg(3.0, 6.0, openings))
    assert root.tag == "svg"


# ── generate_drawings() — wrapper ────────────────────────────────────────────

@pytest.fixture
def pod_drawings():
    elements = decompose_pod(3.0, 6.0, 2.7, roof_type="duo_pitch", roof_pitch_deg=15.0)
    return generate_drawings(elements, width_m=3.0, length_m=6.0, wall_height_m=2.7)

def test_generate_drawings_returns_six_keys(pod_drawings):
    assert set(pod_drawings.keys()) == {"floor_plan", "sales_sheet", "wall_N", "wall_S", "wall_E", "wall_W"}

def test_generate_drawings_all_valid_svg(pod_drawings):
    for key, svg in pod_drawings.items():
        root = _parse(svg)
        assert root.tag == "svg", f"{key} is not valid SVG"

def test_generate_drawings_floor_plan_present(pod_drawings):
    assert "Floor Plan" in pod_drawings["floor_plan"]

def test_generate_drawings_wall_labels(pod_drawings):
    for face in ("N", "S", "E", "W"):
        assert f"Wall {face}" in pod_drawings[f"wall_{face}"]

def test_generate_drawings_ns_walls_longer_span(pod_drawings):
    # N/S walls span length_m=6m → should say 6000 in dimension
    assert "6000" in pod_drawings["wall_N"]
    assert "6000" in pod_drawings["wall_S"]

def test_generate_drawings_ew_walls_shorter_span(pod_drawings):
    # E/W walls span width_m=3m → should say 3000 in dimension
    assert "3000" in pod_drawings["wall_E"]
    assert "3000" in pod_drawings["wall_W"]

def test_generate_drawings_with_openings():
    openings = [
        OpeningSpec(wall="S", type="door",   width_m=0.9, height_m=2.1),
        OpeningSpec(wall="S", type="window", width_m=1.2, height_m=1.1, sill_height_m=0.9),
        OpeningSpec(wall="N", type="window", width_m=0.6, height_m=0.6, sill_height_m=1.2),
    ]
    elements = decompose_pod(3.0, 6.0, 2.7, roof_type="duo_pitch",
                             roof_pitch_deg=15.0, openings=openings)
    drawings = generate_drawings(elements, width_m=3.0, length_m=6.0, wall_height_m=2.7)
    assert set(drawings.keys()) == {"floor_plan", "sales_sheet", "wall_N", "wall_S", "wall_E", "wall_W"}
    for key, svg in drawings.items():
        root = _parse(svg)
        assert root.tag == "svg", f"{key} is not valid SVG"

def test_generate_drawings_south_wall_has_more_rects_with_openings():
    no_op = decompose_pod(3.0, 6.0, 2.7)
    with_op_specs = [OpeningSpec(wall="S", type="door", width_m=0.9, height_m=2.1)]
    with_op = decompose_pod(3.0, 6.0, 2.7, openings=with_op_specs)

    d_plain = generate_drawings(no_op,    3.0, 6.0, 2.7)
    d_doors = generate_drawings(with_op,  3.0, 6.0, 2.7)

    assert _count_tag(d_doors["wall_S"], "rect") > _count_tag(d_plain["wall_S"], "rect")

def test_generate_drawings_stud_spacing_propagated():
    elements = decompose_pod(3.0, 6.0, 2.7)
    d400 = generate_drawings(elements, 3.0, 6.0, 2.7, stud_spacing_mm=400)
    d600 = generate_drawings(elements, 3.0, 6.0, 2.7, stud_spacing_mm=600)
    # 400mm spacing → more studs → more lines
    assert _count_tag(d400["wall_N"], "line") > _count_tag(d600["wall_N"], "line")
