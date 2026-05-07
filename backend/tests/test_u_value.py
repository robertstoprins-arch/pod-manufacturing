"""Tests for the U-value pre-check skill."""
import math
import pytest

from app.skills.u_value import (
    JURISDICTION_TARGETS,
    NORDIC_FLOOR_THERMAL,
    NORDIC_ROOF_THERMAL,
    NORDIC_WALL_THERMAL,
    UValueError,
    UValueLayer,
    calculate_u_value,
)


# ── Simple known-value calculations ──────────────────────────────────────────

def test_single_continuous_layer_wall():
    # R_si=0.13, layer R=100mm/0.040=2.5, R_se=0.04 → R_total=2.67 → U=0.3745
    layers = [UValueLayer("Insulation 100mm", thickness_mm=100, lambda_W_mK=0.040)]
    r = calculate_u_value("ExternalWall", layers, target_u=1.0)
    expected_r = 0.13 + (0.100 / 0.040) + 0.04   # = 2.67
    assert r.r_total == pytest.approx(expected_r, rel=1e-4)
    assert r.u_value == pytest.approx(1.0 / expected_r, rel=1e-4)

def test_surface_resistances_wall():
    layers = [UValueLayer("Insulation", thickness_mm=100, lambda_W_mK=0.040)]
    r = calculate_u_value("ExternalWall", layers, target_u=1.0)
    assert r.r_si == pytest.approx(0.13)
    assert r.r_se == pytest.approx(0.04)

def test_surface_resistances_roof():
    layers = [UValueLayer("Insulation", thickness_mm=100, lambda_W_mK=0.040)]
    r = calculate_u_value("Roof", layers, target_u=1.0)
    assert r.r_si == pytest.approx(0.10)
    assert r.r_se == pytest.approx(0.04)

def test_surface_resistances_floor():
    layers = [UValueLayer("Insulation", thickness_mm=100, lambda_W_mK=0.040)]
    r = calculate_u_value("Floor", layers, target_u=1.0)
    assert r.r_si == pytest.approx(0.17)
    assert r.r_se == pytest.approx(0.04)

def test_multiple_continuous_layers():
    # R_si=0.13, Gyproc 12.5mm/0.25=0.05, OSB 12mm/0.13=0.092, R_se=0.04
    layers = [
        UValueLayer("Gyproc 12.5mm", thickness_mm=12.5, lambda_W_mK=0.25),
        UValueLayer("OSB 12mm",      thickness_mm=12.0, lambda_W_mK=0.13),
    ]
    r = calculate_u_value("ExternalWall", layers, target_u=1.0)
    expected_r = 0.13 + (0.0125 / 0.25) + (0.012 / 0.13) + 0.04
    assert r.r_total == pytest.approx(expected_r, rel=1e-4)

def test_layer_results_count():
    layers = [
        UValueLayer("Layer A", thickness_mm=50, lambda_W_mK=0.04),
        UValueLayer("Layer B", thickness_mm=12, lambda_W_mK=0.13),
    ]
    r = calculate_u_value("ExternalWall", layers, target_u=1.0)
    assert len(r.layers) == 2

def test_layer_r_values_correct():
    layers = [
        UValueLayer("A", thickness_mm=100, lambda_W_mK=0.040),
        UValueLayer("B", thickness_mm=12,  lambda_W_mK=0.130),
    ]
    r = calculate_u_value("ExternalWall", layers, target_u=1.0)
    assert r.layers[0].r_value == pytest.approx(0.100 / 0.040, rel=1e-4)
    assert r.layers[1].r_value == pytest.approx(0.012 / 0.130, rel=1e-4)


# ── Bridged layer (framing + fill) ────────────────────────────────────────────

def test_bridged_layer_lambda_effective():
    # 47mm studs at 600 c/c: framing_fraction = 47/600
    ff = 47 / 600
    layers = [UValueLayer(
        "Stud zone",
        thickness_mm=147, lambda_W_mK=0.037,
        framing_fraction=ff, lambda_framing=0.13,
    )]
    r = calculate_u_value("ExternalWall", layers, target_u=1.0)
    expected_lambda_eff = ff * 0.13 + (1 - ff) * 0.037
    expected_r_layer = (0.147) / expected_lambda_eff
    assert r.layers[0].lambda_effective == pytest.approx(expected_lambda_eff, rel=1e-4)
    assert r.layers[0].r_value == pytest.approx(expected_r_layer, rel=1e-4)

def test_bridged_layer_higher_u_than_continuous():
    # A bridged layer (with framing) should have a higher U than continuous insulation
    bridged = [UValueLayer("Stud+wool", thickness_mm=147, lambda_W_mK=0.037,
                           framing_fraction=47/600, lambda_framing=0.13)]
    continuous = [UValueLayer("Full insulation", thickness_mm=147, lambda_W_mK=0.037)]
    r_bridged = calculate_u_value("ExternalWall", bridged, target_u=1.0)
    r_continuous = calculate_u_value("ExternalWall", continuous, target_u=1.0)
    assert r_bridged.u_value > r_continuous.u_value

def test_zero_framing_fraction_equals_continuous():
    # framing_fraction=0 must give identical result to no framing argument
    with_zero = calculate_u_value("ExternalWall", [
        UValueLayer("A", thickness_mm=100, lambda_W_mK=0.040, framing_fraction=0.0)
    ], target_u=1.0)
    without = calculate_u_value("ExternalWall", [
        UValueLayer("A", thickness_mm=100, lambda_W_mK=0.040)
    ], target_u=1.0)
    assert with_zero.u_value == pytest.approx(without.u_value)


# ── PASS / FAIL ───────────────────────────────────────────────────────────────

def test_pass_when_u_below_target():
    # High-insulation wall: U ≈ 0.15 → should pass 0.18
    layers = [UValueLayer("PIR 200mm", thickness_mm=200, lambda_W_mK=0.022)]
    r = calculate_u_value("ExternalWall", layers, target_u=0.18)
    assert r.status == "PASS"

def test_fail_when_u_above_target():
    # Thin insulation: U will be high
    layers = [UValueLayer("Insulation 50mm", thickness_mm=50, lambda_W_mK=0.040)]
    r = calculate_u_value("ExternalWall", layers, target_u=0.18)
    assert r.status == "FAIL"

def test_pass_exactly_at_target():
    # Construct a build-up that hits exactly the target
    # R_total needed = 1/target; solve for insulation thickness
    target = 0.20
    r_si, r_se = 0.13, 0.04
    lambda_ins = 0.040
    # R_ins = 1/target - r_si - r_se
    r_ins_needed = (1.0 / target) - r_si - r_se   # = 5.0 - 0.17 = 4.83
    thickness_mm = r_ins_needed * lambda_ins * 1000  # in mm
    layers = [UValueLayer("Exact", thickness_mm=thickness_mm, lambda_W_mK=lambda_ins)]
    r = calculate_u_value("ExternalWall", layers, target_u=target)
    assert r.status == "PASS"
    assert r.u_value == pytest.approx(target, rel=1e-4)

def test_margin_positive_on_pass():
    layers = [UValueLayer("PIR 200mm", thickness_mm=200, lambda_W_mK=0.022)]
    r = calculate_u_value("ExternalWall", layers, target_u=0.18)
    assert r.status == "PASS"
    assert r.margin > 0

def test_margin_negative_on_fail():
    layers = [UValueLayer("Insulation 50mm", thickness_mm=50, lambda_W_mK=0.040)]
    r = calculate_u_value("ExternalWall", layers, target_u=0.18)
    assert r.status == "FAIL"
    assert r.margin < 0

def test_margin_equals_target_minus_u():
    layers = [UValueLayer("Ins", thickness_mm=150, lambda_W_mK=0.037)]
    r = calculate_u_value("ExternalWall", layers, target_u=0.18)
    assert r.margin == pytest.approx(0.18 - r.u_value, rel=1e-4)


# ── element_label passthrough ─────────────────────────────────────────────────

def test_element_label_stored():
    layers = [UValueLayer("Ins", thickness_mm=100, lambda_W_mK=0.040)]
    r = calculate_u_value("ExternalWall", layers, target_u=0.18, element_label="wall_N")
    assert r.element_label == "wall_N"
    assert r.element_type == "ExternalWall"


# ── Validation / error handling ───────────────────────────────────────────────

def test_unknown_element_type_raises():
    with pytest.raises(UValueError):
        calculate_u_value("Partition", [UValueLayer("X", 100, 0.04)], target_u=0.18)

def test_zero_thickness_raises():
    with pytest.raises(UValueError):
        calculate_u_value("ExternalWall", [UValueLayer("X", 0, 0.04)], target_u=0.18)

def test_zero_lambda_raises():
    with pytest.raises(UValueError):
        calculate_u_value("ExternalWall", [UValueLayer("X", 100, 0.0)], target_u=0.18)

def test_empty_layers_raises():
    with pytest.raises(UValueError):
        calculate_u_value("ExternalWall", [], target_u=0.18)

def test_zero_target_u_raises():
    with pytest.raises(UValueError):
        calculate_u_value("ExternalWall", [UValueLayer("X", 100, 0.04)], target_u=0.0)

def test_framing_fraction_ge_one_raises():
    with pytest.raises(UValueError):
        calculate_u_value("ExternalWall", [
            UValueLayer("X", 100, 0.04, framing_fraction=1.0)
        ], target_u=0.18)

def test_framing_fraction_with_zero_lambda_framing_raises():
    with pytest.raises(UValueError):
        calculate_u_value("ExternalWall", [
            UValueLayer("X", 100, 0.04, framing_fraction=0.1, lambda_framing=0.0)
        ], target_u=0.18)


# ── Jurisdiction targets ──────────────────────────────────────────────────────

def test_bbr_targets_present():
    t = JURISDICTION_TARGETS["BBR_SE"]
    assert t["ExternalWall"] == pytest.approx(0.18)
    assert t["Roof"]         == pytest.approx(0.13)
    assert t["Floor"]        == pytest.approx(0.15)
    assert t["window"]       == pytest.approx(1.20)

def test_tek17_targets_present():
    t = JURISDICTION_TARGETS["TEK17_NO"]
    assert t["ExternalWall"] == pytest.approx(0.18)
    assert t["Floor"]        == pytest.approx(0.10)
    assert t["window"]       == pytest.approx(0.80)

def test_tek17_floor_stricter_than_bbr():
    assert JURISDICTION_TARGETS["TEK17_NO"]["Floor"] < JURISDICTION_TARGETS["BBR_SE"]["Floor"]

def test_tek17_window_stricter_than_bbr():
    assert JURISDICTION_TARGETS["TEK17_NO"]["window"] < JURISDICTION_TARGETS["BBR_SE"]["window"]


# ── Nordic thermal presets ────────────────────────────────────────────────────

def test_nordic_wall_calculates_without_error():
    r = calculate_u_value("ExternalWall", NORDIC_WALL_THERMAL, target_u=0.18)
    assert r.u_value > 0
    assert r.r_total > 0

def test_nordic_floor_calculates_without_error():
    r = calculate_u_value("Floor", NORDIC_FLOOR_THERMAL, target_u=0.15)
    assert r.u_value > 0

def test_nordic_roof_calculates_without_error():
    r = calculate_u_value("Roof", NORDIC_ROOF_THERMAL, target_u=0.13)
    assert r.u_value > 0

def test_nordic_wall_u_value_approx():
    # 47×147 studs at 600 c/c with Rockwool 0.037 → expect ~0.26 W/m²K
    r = calculate_u_value("ExternalWall", NORDIC_WALL_THERMAL, target_u=0.18)
    assert 0.20 < r.u_value < 0.35

def test_nordic_wall_fails_bbr():
    # 147mm stud wall without extra insulation cannot meet BBR 0.18
    r = calculate_u_value(
        "ExternalWall",
        NORDIC_WALL_THERMAL,
        target_u=JURISDICTION_TARGETS["BBR_SE"]["ExternalWall"],
    )
    assert r.status == "FAIL"

def test_nordic_wall_fails_tek17():
    r = calculate_u_value(
        "ExternalWall",
        NORDIC_WALL_THERMAL,
        target_u=JURISDICTION_TARGETS["TEK17_NO"]["ExternalWall"],
    )
    assert r.status == "FAIL"

def test_adding_extra_insulation_reduces_u_value():
    # Adding a 50mm PIR layer to Nordic wall should reduce U-value
    base_r = calculate_u_value("ExternalWall", NORDIC_WALL_THERMAL, target_u=0.18)
    enhanced_layers = NORDIC_WALL_THERMAL + [
        UValueLayer("PIR outboard 50mm", thickness_mm=50, lambda_W_mK=0.022)
    ]
    enhanced_r = calculate_u_value("ExternalWall", enhanced_layers, target_u=0.18)
    assert enhanced_r.u_value < base_r.u_value

def test_adding_50mm_pir_to_nordic_wall_passes_bbr():
    # 50mm Kingspan Kooltherm K15 (lambda=0.020) outboard of the stud wall
    # should push U-value below 0.18
    enhanced = NORDIC_WALL_THERMAL + [
        UValueLayer("Kingspan Kooltherm K15 50mm", thickness_mm=50, lambda_W_mK=0.020)
    ]
    r = calculate_u_value("ExternalWall", enhanced, target_u=0.18)
    assert r.status == "PASS"
