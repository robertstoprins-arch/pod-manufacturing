"""
Tests for mto_resolver.py — role-based linear/area MTO calculations.

All expected values from the recovery spec (Section 8 / Section 12).
"""
import pytest
from app.skills.mto_resolver import (
    DEFAULT_NOGGIN_ROWS,
    DEFAULT_STUD_SPACING_M,
    DEFAULT_STUD_WIDTH_M,
    EXTRA_STUDS_PER_OPENING,
    MtoInputLayer,
    WallGeometry,
    resolve_mto,
    _studs_raw,
    _plates_raw,
    _noggins_raw,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wall(length_m, height_m, opening_count=0, gross=None, net=None):
    gross = gross or (length_m * height_m)
    net   = net   or (gross - opening_count * 1.44)   # assume 1.2×1.2 openings
    return WallGeometry(
        label="wall_test",
        length_m=length_m,
        height_m=height_m,
        opening_count=opening_count,
        gross_area_m2=gross,
        net_area_m2=net,
    )


# ── Stud calculations ─────────────────────────────────────────────────────────

def test_studs_6m_no_openings():
    """6m wall at 600mm centres, no openings → 11 studs, 30.8 lm."""
    raw, _ = _studs_raw(6.0, 2.8, opening_count=0)
    assert raw == pytest.approx(30.8, abs=0.01)


def test_studs_6m_one_opening():
    """6m wall, 1 opening → 11 base + 4 extra = 15 studs, 42.0 lm."""
    raw, note = _studs_raw(6.0, 2.8, opening_count=1)
    assert raw == pytest.approx(42.0, abs=0.01)
    assert "extra" in note


def test_studs_base_count():
    # floor(6 / 0.6) + 1 = 11
    import math
    assert math.floor(6.0 / DEFAULT_STUD_SPACING_M) + 1 == 11


# ── Plate calculations ────────────────────────────────────────────────────────

def test_plates_6m():
    """6m wall → top + bottom = 12.0 lm."""
    raw = _plates_raw(6.0)
    assert raw == pytest.approx(12.0, abs=0.001)


# ── Noggin calculations ───────────────────────────────────────────────────────

def test_noggins_6m():
    """
    6m wall: 11 studs → 10 bays
    noggin_length = 0.600 − 0.038 = 0.562
    total = 10 × 0.562 = 5.62 lm
    """
    raw, note = _noggins_raw(6.0)
    assert raw == pytest.approx(5.62, abs=0.01)
    assert "10 noggins" in note


# ── Area material ─────────────────────────────────────────────────────────────

def test_board_area_net():
    """Plasterboard: net area, waste 1.10."""
    layer = MtoInputLayer(name="Plasterboard", role="internal_finish", thickness_mm=12.5)
    result = resolve_mto([layer], "ExternalWall", [], total_net_m2=15.36, total_gross_m2=16.8)
    assert len(result) == 1
    line = result[0]
    assert line.unit == "m2"
    assert line.method == "board_area"
    assert line.raw_quantity == pytest.approx(15.36, abs=0.001)
    assert line.waste_factor == pytest.approx(1.10, abs=0.001)
    assert line.order_quantity == pytest.approx(15.36 * 1.10, abs=0.01)


def test_insulation_waste_is_1_08():
    """Insulation role gets 1.08 waste (PIR/EPS/MW)."""
    layer = MtoInputLayer(name="PIR Board", role="insulation", thickness_mm=50.0)
    result = resolve_mto([layer], "ExternalWall", [], total_net_m2=15.36, total_gross_m2=16.8)
    assert result[0].waste_factor == pytest.approx(1.08, abs=0.001)


def test_cladding_waste_is_1_12():
    """Cladding uses board_area_cladding method with 1.12 waste."""
    layer = MtoInputLayer(name="FC Cladding", role="cladding", thickness_mm=12.0)
    result = resolve_mto([layer], "ExternalWall", [], total_net_m2=15.36, total_gross_m2=16.8)
    assert result[0].method == "board_area_cladding"
    assert result[0].waste_factor == pytest.approx(1.12, abs=0.001)


# ── Membrane ──────────────────────────────────────────────────────────────────

def test_membrane_gross_plus_laps():
    """VCL: gross area × 1.10 = 18.48 for gross=16.8."""
    layer = MtoInputLayer(name="Intello Plus", role="vcl", thickness_mm=0.2)
    result = resolve_mto([layer], "ExternalWall", [], total_net_m2=15.36, total_gross_m2=16.8)
    line = result[0]
    assert line.method == "membrane_area"
    assert line.unit == "m2"
    assert line.raw_quantity == pytest.approx(16.8, abs=0.001)
    assert line.order_quantity == pytest.approx(16.8 * 1.10, abs=0.01)   # 18.48


# ── Linear battens ────────────────────────────────────────────────────────────

def test_service_void_battens_linear():
    """Service void → linear_vertical_centres, not area."""
    layer = MtoInputLayer(name="Service Void Battens", role="service_void", thickness_mm=50.0)
    walls = [_wall(6.0, 2.8)]   # 1 wall for simplicity
    result = resolve_mto([layer], "ExternalWall", walls, total_net_m2=16.8, total_gross_m2=16.8)
    line = result[0]
    assert line.method == "linear_vertical_centres"
    assert line.unit == "lm"


def test_cavity_battens_linear():
    """Cavity → linear_vertical_centres."""
    layer = MtoInputLayer(name="Ventilated Cavity", role="cavity", thickness_mm=25.0)
    walls = [_wall(6.0, 2.8)]
    result = resolve_mto([layer], "ExternalWall", walls, total_net_m2=16.8, total_gross_m2=16.8)
    assert result[0].unit == "lm"
    assert result[0].method == "linear_vertical_centres"


def test_service_void_roof_not_calculated():
    """service_void on Roof must return not_calculated, never m2."""
    layer = MtoInputLayer(name="Roof Service Void", role="service_void", thickness_mm=50.0)
    result = resolve_mto([layer], "Roof", [], total_net_m2=18.0, total_gross_m2=18.0)
    assert len(result) == 1
    line = result[0]
    assert line.method == "not_calculated"
    assert line.unit == "lm"
    assert line.raw_quantity == 0.0
    assert line.order_quantity == 0.0


def test_cavity_floor_not_calculated():
    """cavity on Floor must return not_calculated, never m2."""
    layer = MtoInputLayer(name="Floor Cavity", role="cavity", thickness_mm=25.0)
    result = resolve_mto([layer], "Floor", [], total_net_m2=18.0, total_gross_m2=18.0)
    assert result[0].method == "not_calculated"
    assert result[0].unit == "lm"


# ── Framing zone split ────────────────────────────────────────────────────────

def test_framing_zone_produces_two_lines():
    """framing_zone_split must emit 2 lines: timber (lm) + insulation infill (m2)."""
    layer = MtoInputLayer(
        name="C24+PIR 140mm", role="framing_zone", thickness_mm=140.0, framing_fraction=0.15
    )
    walls = [_wall(6.0, 2.8, gross=16.8, net=15.36)]
    result = resolve_mto([layer], "ExternalWall", walls, total_net_m2=15.36, total_gross_m2=16.8)
    assert len(result) == 2
    timber = result[0]
    infill = result[1]
    assert timber.unit == "lm"
    assert timber.method == "framing_zone_split_timber"
    assert infill.unit == "m2"
    assert infill.method == "framing_zone_split_insulation"


def test_framing_zone_timber_includes_studs_plates_noggins():
    """Timber line = studs + plates + noggins (no waste applied to raw)."""
    layer = MtoInputLayer(
        name="C24+PIR 140mm", role="framing_zone", thickness_mm=140.0, framing_fraction=0.15
    )
    walls = [_wall(6.0, 2.8)]
    result = resolve_mto([layer], "ExternalWall", walls, total_net_m2=16.8, total_gross_m2=16.8)
    timber = result[0]
    # studs: 11 × 2.8 = 30.8, plates: 12.0, noggins ≈ 5.62 → total ≈ 48.42
    assert timber.raw_quantity == pytest.approx(30.8 + 12.0 + 5.62, abs=0.1)
    assert timber.waste_factor == pytest.approx(1.10, abs=0.001)


def test_framing_zone_pir_infill_area():
    """PIR infill = net_area × (1 − framing_fraction), waste 1.08."""
    layer = MtoInputLayer(
        name="C24+PIR 140mm", role="framing_zone", thickness_mm=140.0, framing_fraction=0.15
    )
    walls = [_wall(6.0, 2.8, gross=16.8, net=15.36)]
    result = resolve_mto([layer], "ExternalWall", walls, total_net_m2=15.36, total_gross_m2=16.8)
    infill = result[1]
    assert infill.method == "framing_zone_split_insulation"
    assert "PIR infill" in infill.material_name
    # net 15.36 × 0.85 = 13.056
    assert infill.raw_quantity == pytest.approx(15.36 * 0.85, abs=0.01)
    assert infill.waste_factor == pytest.approx(1.08, abs=0.001)


def test_framing_zone_mw_infill_label():
    """Mineral wool framing zone: infill line says 'Mineral wool infill', not PIR."""
    layer = MtoInputLayer(
        name="C24 Stud Zone + Mineral Wool Fill (140mm)",
        role="framing_zone",
        thickness_mm=140.0,
        framing_fraction=0.15,
    )
    walls = [_wall(6.0, 2.8, gross=16.8, net=15.36)]
    result = resolve_mto([layer], "ExternalWall", walls, total_net_m2=15.36, total_gross_m2=16.8)
    assert len(result) == 2
    timber, infill = result
    assert timber.method == "framing_zone_split_timber"
    assert timber.unit == "lm"
    assert infill.method == "framing_zone_split_insulation"
    assert infill.unit == "m2"
    assert "Mineral wool infill" in infill.material_name
    assert "PIR" not in infill.material_name
    assert infill.raw_quantity == pytest.approx(15.36 * 0.85, abs=0.01)
    assert infill.waste_factor == pytest.approx(1.08, abs=0.001)


def test_framing_zone_generic_infill_label():
    """Unknown fill type defaults to 'Insulation infill'."""
    layer = MtoInputLayer(
        name="C24 Stud Zone + EPS Fill",
        role="framing_zone",
        thickness_mm=140.0,
        framing_fraction=0.15,
    )
    walls = [_wall(6.0, 2.8)]
    result = resolve_mto([layer], "ExternalWall", walls, total_net_m2=16.8, total_gross_m2=16.8)
    assert "Insulation infill" in result[1].material_name


def test_framing_zone_no_split_for_floor():
    """framing_zone on Floor element (no wall geometry) falls back to board_area."""
    layer = MtoInputLayer(
        name="Joist Zone", role="framing_zone", thickness_mm=195.0, framing_fraction=0.15
    )
    result = resolve_mto([layer], "Floor", [], total_net_m2=18.0, total_gross_m2=18.0)
    assert len(result) == 1
    assert result[0].unit == "m2"


# ── Concrete volume ───────────────────────────────────────────────────────────

def test_concrete_slab_outputs_m3():
    """Concrete slab: area × thickness → m3, waste 1.03."""
    layer = MtoInputLayer(
        name="Concrete Slab (in-situ)",
        role="structure",
        thickness_mm=150,
        supplier_ref="GENERIC-CONCRETE-SLAB-150",
    )
    lines = resolve_mto([layer], "Floor", [], total_net_m2=40.0, total_gross_m2=40.0)
    assert len(lines) == 1
    assert lines[0].method == "volume_from_area_thickness"
    assert lines[0].unit == "m3"
    assert lines[0].raw_quantity == pytest.approx(6.0, abs=0.001)
    assert lines[0].waste_factor == pytest.approx(1.03, abs=0.001)
    assert lines[0].order_quantity == pytest.approx(6.18, abs=0.001)


def test_non_concrete_structure_stays_m2():
    """A structure role that is NOT concrete stays on board_area (m2)."""
    layer = MtoInputLayer(
        name="Cross-Laminated Timber Panel",
        role="structure",
        thickness_mm=100,
        supplier_ref="GENERIC-CLT-100",
    )
    lines = resolve_mto([layer], "Floor", [], total_net_m2=40.0, total_gross_m2=40.0)
    assert lines[0].unit == "m2"
    assert lines[0].method == "board_area"


# ── Net area logic ────────────────────────────────────────────────────────────

def test_net_area_calculation():
    """Gross 16.8, one 1.2×1.2 opening = 1.44, net = 15.36."""
    gross = 6.0 * 2.8
    opening_area = 1.2 * 1.2
    net = gross - opening_area
    assert net == pytest.approx(15.36, abs=0.001)


# ── Composite framing zone — properties-based infill ─────────────────────────

def test_framing_zone_pir_infill_via_props():
    """Properties infill_name='PIR Infill' → MTO label uses it; supplier ref attached."""
    layer = MtoInputLayer(
        name="C24 Stud Zone + PIR Fill (140mm)",
        role="framing_zone",
        thickness_mm=140.0,
        framing_fraction=0.15,
        properties={
            "infill_type": "pir",
            "infill_name": "PIR Infill",
            "infill_material_ref": "GENERIC-PIR-FRAMING-140",
            "infill_lambda_W_mK": 0.023,
        },
    )
    walls = [_wall(6.0, 2.8, gross=16.8, net=15.36)]
    result = resolve_mto([layer], "ExternalWall", walls, total_net_m2=15.36, total_gross_m2=16.8)
    assert len(result) == 2
    infill = result[1]
    assert infill.method == "framing_zone_split_insulation"
    assert "PIR Infill" in infill.material_name
    assert "GENERIC-PIR-FRAMING-140" in infill.notes


def test_framing_zone_mw_infill_via_props():
    """Properties infill_name='Mineral Wool Infill' → MTO label uses it; no PIR in name."""
    layer = MtoInputLayer(
        name="C24 Stud Zone",
        role="framing_zone",
        thickness_mm=140.0,
        framing_fraction=0.15,
        properties={
            "infill_type": "mineral_wool",
            "infill_name": "Mineral Wool Infill",
            "infill_material_ref": "GENERIC-MW-FRAMING-140",
            "infill_lambda_W_mK": 0.034,
        },
    )
    walls = [_wall(6.0, 2.8, gross=16.8, net=15.36)]
    result = resolve_mto([layer], "ExternalWall", walls, total_net_m2=15.36, total_gross_m2=16.8)
    infill = result[1]
    assert "Mineral Wool Infill" in infill.material_name
    assert "PIR" not in infill.material_name
    assert "GENERIC-MW-FRAMING-140" in infill.notes


def test_framing_zone_props_infill_overrides_name_detection():
    """When properties.infill_name is set, it wins even if layer name says 'PIR'."""
    layer = MtoInputLayer(
        name="C24 + PIR Zone",   # name says PIR...
        role="framing_zone",
        thickness_mm=140.0,
        framing_fraction=0.15,
        properties={             # ...but props say mineral wool
            "infill_name": "Mineral Wool Infill",
            "infill_material_ref": "GENERIC-MW-FRAMING-140",
        },
    )
    walls = [_wall(6.0, 2.8)]
    result = resolve_mto([layer], "ExternalWall", walls, total_net_m2=16.8, total_gross_m2=16.8)
    mat_name = result[1].material_name
    # material_name = "<layer_name> — <infill_label>"; check the label part
    infill_label = mat_name.split(" — ", 1)[-1]
    assert "Mineral Wool Infill" in infill_label
    assert "PIR" not in infill_label
