"""Tests for the Build-Up Resolver skill.

All inputs follow the INSIDE → OUTSIDE layer convention.
No database access — pure function tests.
"""
import pytest
from app.skills.build_up_resolver import ResolverLayer, resolve


# ── Helper factories ──────────────────────────────────────────────────────────

def _plasterboard():
    return ResolverLayer("Gyproc 12.5mm", thickness_mm=12.5, lambda_W_mK=0.25,
                         role="internal_finish", include_in_u_value=True)

def _vcl():
    return ResolverLayer("Intello Plus VCL", thickness_mm=0.2, lambda_W_mK=0.17,
                         role="vcl", include_in_u_value=False)

def _osb():
    return ResolverLayer("OSB3 11mm", thickness_mm=11.0, lambda_W_mK=0.13,
                         role="sheathing", include_in_u_value=True)

def _stud_pir(framing_fraction=0.15):
    return ResolverLayer("C24 stud + PIR 140mm", thickness_mm=140.0, lambda_W_mK=0.023,
                         role="framing_zone", framing_fraction=framing_fraction,
                         include_in_u_value=True)

def _pir_outboard():
    return ResolverLayer("PIR outboard 50mm", thickness_mm=50.0, lambda_W_mK=0.023,
                         role="insulation", include_in_u_value=True)

def _breather():
    return ResolverLayer("Tyvek Housewrap", thickness_mm=0.2, lambda_W_mK=0.17,
                         role="breather", include_in_u_value=False)

def _cavity():
    return ResolverLayer("Ventilated cavity 25mm", thickness_mm=25.0, lambda_W_mK=0.17,
                         role="cavity", include_in_u_value=False)

def _cladding():
    return ResolverLayer("FC Cladding 12mm", thickness_mm=12.0, lambda_W_mK=0.35,
                         role="cladding", include_in_u_value=True)


NORDIC_WALL_LAYERS = [
    _plasterboard(),
    _vcl(),
    _osb(),
    _stud_pir(),
    _pir_outboard(),
    _breather(),
    _cavity(),
    _cladding(),
]


# ── U-value and targets ───────────────────────────────────────────────────────

def test_nordic_standard_wall_passes_target():
    result = resolve(NORDIC_WALL_LAYERS, "ExternalWall")
    assert result.errors == [], f"Unexpected errors: {result.errors}"
    assert 0.10 < result.u_value <= 0.18, f"U-value {result.u_value} outside expected range"
    bbr = next(t for t in result.targets if t.code == "BBR")
    tek17 = next(t for t in result.targets if t.code == "TEK17")
    assert bbr.passes, f"BBR target failed: U={result.u_value}, target={bbr.target_u_value}"
    assert tek17.passes, f"TEK17 target failed: U={result.u_value}, target={tek17.target_u_value}"


def test_target_labels_are_preliminary():
    result = resolve(NORDIC_WALL_LAYERS, "ExternalWall")
    for t in result.targets:
        assert "preliminary" in t.label.lower() or "profile" in t.label.lower(), \
            f"Target label should mention 'preliminary' or 'profile', got: {t.label!r}"


def test_layer_resistance_calculation():
    """Single solid layer: R = thickness / lambda, U = 1 / (R_si + R + R_se)."""
    layers = [
        ResolverLayer("Concrete 200mm", thickness_mm=200.0, lambda_W_mK=1.15,
                      role="structure", include_in_u_value=True),
        ResolverLayer("EPS 100mm", thickness_mm=100.0, lambda_W_mK=0.038,
                      role="insulation", include_in_u_value=True),
    ]
    result = resolve(layers, "Floor")
    r_concrete = 0.200 / 1.15
    r_eps = 0.100 / 0.038
    r_si, r_se = 0.17, 0.04
    expected_r = r_si + r_concrete + r_eps + r_se
    expected_u = 1.0 / expected_r
    assert result.u_value == pytest.approx(expected_u, abs=0.005)
    assert result.r_total == pytest.approx(expected_r, abs=0.01)


def test_framing_fraction_effective_lambda():
    """PIR 0.023 + 15% timber 0.13 → λ_eff ≈ 0.039."""
    layers = [
        _plasterboard(),
        _vcl(),
        _stud_pir(framing_fraction=0.15),
        _breather(),
        _cladding(),
    ]
    result = resolve(layers, "ExternalWall")
    # Find the framing zone layer result (it should have effective lambda ~ 0.039)
    framing_result = next(
        (lr for lr in result.layers if "stud" in lr.name.lower() or "pir" in lr.name.lower()),
        None,
    )
    assert framing_result is not None
    expected_lambda_eff = 0.15 * 0.13 + 0.85 * 0.023
    assert framing_result.lambda_effective == pytest.approx(expected_lambda_eff, abs=0.002)


# ── Blocking errors ───────────────────────────────────────────────────────────

def test_empty_layers_rejected():
    result = resolve([], "ExternalWall")
    assert any("minimum 2" in e.lower() for e in result.errors)


def test_single_layer_rejected():
    result = resolve([_plasterboard()], "ExternalWall")
    assert any("minimum 2" in e.lower() for e in result.errors)


def test_vcl_missing_error():
    layers = [_plasterboard(), _osb(), _stud_pir(), _pir_outboard(), _breather(), _cladding()]
    result = resolve(layers, "ExternalWall")
    assert any("vcl" in e.lower() or "airtight" in e.lower() or "vapour control" in e.lower()
               for e in result.errors), f"Expected VCL missing error, got: {result.errors}"


def test_vcl_wrong_side_error():
    # VCL placed after (cold side of) main insulation zone
    layers = [
        _plasterboard(),
        _osb(),
        _stud_pir(),       # insulation zone at index 2
        _pir_outboard(),   # insulation at index 3
        _vcl(),            # VCL at index 4 — cold side!
        _breather(),
        _cladding(),
    ]
    result = resolve(layers, "ExternalWall")
    assert any("cold side" in e.lower() or "wrong side" in e.lower() or "warm" in e.lower()
               for e in result.errors), f"Expected VCL wrong side error, got: {result.errors}"


def test_zero_thickness_rejected():
    bad = ResolverLayer("BadLayer", thickness_mm=0.0, lambda_W_mK=0.13, role="structure")
    layers = [_plasterboard(), bad]
    result = resolve(layers, "ExternalWall")
    assert any("thickness" in e.lower() for e in result.errors)


def test_zero_lambda_rejected_for_thermal_layer():
    bad = ResolverLayer("BadMaterial", thickness_mm=50.0, lambda_W_mK=0.0,
                        role="insulation", include_in_u_value=True)
    layers = [_plasterboard(), bad]
    result = resolve(layers, "ExternalWall")
    assert any("lambda" in e.lower() or "λ" in e for e in result.errors)


# ── Warnings (non-blocking) ───────────────────────────────────────────────────

def test_breather_wrong_side_warning():
    # Breather placed before (warm side of) insulation
    layers = [
        _plasterboard(),
        _vcl(),
        _breather(),       # breather on warm side!
        _stud_pir(),
        _pir_outboard(),
        _cladding(),
    ]
    result = resolve(layers, "ExternalWall")
    assert any("breather" in w.lower() for w in result.warnings), \
        f"Expected breather warning, got: {result.warnings}"


def test_no_cladding_warning():
    layers = [_plasterboard(), _vcl(), _stud_pir(), _pir_outboard(), _breather()]
    result = resolve(layers, "ExternalWall")
    assert any("cladding" in w.lower() or "external finish" in w.lower()
               for w in result.warnings)


def test_no_breather_warning_for_external_wall():
    layers = [_plasterboard(), _vcl(), _stud_pir(), _pir_outboard(), _cladding()]
    result = resolve(layers, "ExternalWall")
    assert any("breather" in w.lower() for w in result.warnings)


def test_framing_zone_without_fraction_warning():
    layers = [
        _plasterboard(),
        _vcl(),
        ResolverLayer("Stud zone no fraction", thickness_mm=140.0, lambda_W_mK=0.023,
                      role="framing_zone", framing_fraction=0.0, include_in_u_value=True),
        _pir_outboard(),
        _breather(),
        _cladding(),
    ]
    result = resolve(layers, "ExternalWall")
    assert any("framing" in w.lower() for w in result.warnings)


# ── Assumptions ───────────────────────────────────────────────────────────────

def test_assumptions_always_present():
    result = resolve(NORDIC_WALL_LAYERS, "ExternalWall")
    full_text = " ".join(result.assumptions).lower()
    assert "inside" in full_text or "inside-to-outside" in full_text
    assert "professional review" in full_text or "preliminary" in full_text


def test_cavity_assumption_included():
    result = resolve(NORDIC_WALL_LAYERS, "ExternalWall")
    full_text = " ".join(result.assumptions).lower()
    assert "cavity" in full_text


# ── Floor and Roof ────────────────────────────────────────────────────────────

def test_floor_no_vcl_required():
    """Floor build-ups do not require a VCL — no VCL error expected."""
    layers = [
        ResolverLayer("Concrete 150mm", thickness_mm=150.0, lambda_W_mK=1.15,
                      role="structure", include_in_u_value=True),
        ResolverLayer("EPS 150mm", thickness_mm=150.0, lambda_W_mK=0.038,
                      role="insulation", include_in_u_value=True),
    ]
    result = resolve(layers, "Floor")
    vcl_errors = [e for e in result.errors if "vcl" in e.lower() or "airtight" in e.lower()]
    assert vcl_errors == [], f"Floor should not require VCL, got: {vcl_errors}"


def test_roof_u_value_computed():
    layers = [
        ResolverLayer("OSB deck 12mm", thickness_mm=12.0, lambda_W_mK=0.13,
                      role="structure", include_in_u_value=True),
        ResolverLayer("Mineral wool 300mm", thickness_mm=300.0, lambda_W_mK=0.034,
                      role="insulation", include_in_u_value=True),
    ]
    result = resolve(layers, "Roof")
    assert result.u_value > 0
    assert result.u_value < 0.15, f"Expected good U-value for thick mineral wool, got {result.u_value}"


# ── Composite framing zone: infill_lambda_W_mK ───────────────────────────────

def test_framing_zone_pir_lambda_eff():
    """PIR infill: λ_eff = 0.15×0.13 + 0.85×0.023 = 0.03905."""
    layers = [
        _plasterboard(),
        _vcl(),
        ResolverLayer(
            "C24 stud + PIR 140mm", thickness_mm=140.0,
            lambda_W_mK=0.13,  # base material = C24 timber
            role="framing_zone", framing_fraction=0.15,
            include_in_u_value=True,
            infill_lambda_W_mK=0.023,  # PIR fill overrides lambda_W_mK in U-value calc
        ),
        _breather(),
        _cladding(),
    ]
    result = resolve(layers, "ExternalWall")
    framing = next(lr for lr in result.layers if "stud" in lr.name.lower())
    expected = 0.15 * 0.13 + 0.85 * 0.023
    assert framing.lambda_effective == pytest.approx(expected, abs=0.0001)


def test_framing_zone_mineral_wool_lambda_eff():
    """Mineral wool infill: λ_eff = 0.15×0.13 + 0.85×0.034 = 0.04840."""
    layers = [
        _plasterboard(),
        _vcl(),
        ResolverLayer(
            "C24 stud + MW 140mm", thickness_mm=140.0,
            lambda_W_mK=0.13,  # base material = C24 timber
            role="framing_zone", framing_fraction=0.15,
            include_in_u_value=True,
            infill_lambda_W_mK=0.034,  # mineral wool fill
        ),
        _breather(),
        _cladding(),
    ]
    result = resolve(layers, "ExternalWall")
    framing = next(lr for lr in result.layers if "stud" in lr.name.lower())
    expected = 0.15 * 0.13 + 0.85 * 0.034
    assert framing.lambda_effective == pytest.approx(expected, abs=0.0001)


def test_framing_zone_infill_lambda_not_used_outside_framing_zone():
    """infill_lambda_W_mK is ignored for non-framing_zone roles; original lambda used."""
    layers = [
        ResolverLayer(
            "EPS 100mm", thickness_mm=100.0, lambda_W_mK=0.038,
            role="insulation", include_in_u_value=True,
            infill_lambda_W_mK=0.023,  # should NOT affect this layer
        ),
        ResolverLayer("Concrete 150mm", thickness_mm=150.0, lambda_W_mK=1.15,
                      role="structure", include_in_u_value=True),
    ]
    result = resolve(layers, "Floor")
    eps_result = next(lr for lr in result.layers if "eps" in lr.name.lower())
    assert eps_result.lambda_effective == pytest.approx(0.038, abs=0.001)


# ── total_thickness_mm ────────────────────────────────────────────────────────

def test_total_thickness_standard_hybrid_wall():
    """Nordic Standard Hybrid Wall layers sum to expected total."""
    # 12.5 + 0.2 + 11 + 140 + 50 + 0.2 + 25 + 12 = 251.0 mm
    layers = [
        ResolverLayer("Gyproc 12.5mm",        thickness_mm=12.5,  lambda_W_mK=0.25,  role="internal_finish",  include_in_u_value=True),
        ResolverLayer("VCL 0.2mm",             thickness_mm=0.2,   lambda_W_mK=0.17,  role="vcl",             include_in_u_value=False),
        ResolverLayer("OSB3 11mm",             thickness_mm=11.0,  lambda_W_mK=0.13,  role="sheathing",        include_in_u_value=True),
        ResolverLayer("C24 stud + PIR 140mm",  thickness_mm=140.0, lambda_W_mK=0.023, role="framing_zone",     framing_fraction=0.15, include_in_u_value=True),
        ResolverLayer("PIR outboard 50mm",     thickness_mm=50.0,  lambda_W_mK=0.023, role="insulation",       include_in_u_value=True),
        ResolverLayer("Tyvek Housewrap",       thickness_mm=0.2,   lambda_W_mK=0.17,  role="breather",         include_in_u_value=False),
        ResolverLayer("Ventilated cavity 25mm",thickness_mm=25.0,  lambda_W_mK=0.17,  role="cavity",           include_in_u_value=False),
        ResolverLayer("FC Cladding 12mm",      thickness_mm=12.0,  lambda_W_mK=0.35,  role="cladding",         include_in_u_value=True),
    ]
    result = resolve(layers, "ExternalWall")
    assert result.total_thickness_mm == pytest.approx(251.0, abs=0.1)


def test_total_thickness_updates_after_layer_removed():
    """Removing a 50mm layer reduces total_thickness_mm by 50mm."""
    full_layers = [
        ResolverLayer("Plasterboard 12.5mm", thickness_mm=12.5, lambda_W_mK=0.25,  role="internal_finish", include_in_u_value=True),
        ResolverLayer("VCL",                 thickness_mm=0.2,  lambda_W_mK=0.17,  role="vcl",             include_in_u_value=False),
        ResolverLayer("Service void 50mm",   thickness_mm=50.0, lambda_W_mK=0.17,  role="service_void",    include_in_u_value=False),
        ResolverLayer("C24 stud 140mm",      thickness_mm=140.0,lambda_W_mK=0.023, role="framing_zone",    framing_fraction=0.15, include_in_u_value=True),
        ResolverLayer("Breather",            thickness_mm=0.2,  lambda_W_mK=0.17,  role="breather",        include_in_u_value=False),
        ResolverLayer("Cladding 12mm",       thickness_mm=12.0, lambda_W_mK=0.35,  role="cladding",        include_in_u_value=True),
    ]
    reduced_layers = [l for l in full_layers if l.role != "service_void"]
    full_result    = resolve(full_layers,    "ExternalWall")
    reduced_result = resolve(reduced_layers, "ExternalWall")
    assert full_result.total_thickness_mm - reduced_result.total_thickness_mm == pytest.approx(50.0, abs=0.01)


def test_total_thickness_includes_layers_excluded_from_u_value():
    """VCL, breather, cavity, and service_void (include_in_u_value=False) must count toward total."""
    vcl           = ResolverLayer("VCL",           thickness_mm=0.2,  lambda_W_mK=0.17, role="vcl",          include_in_u_value=False)
    breather      = ResolverLayer("Breather",      thickness_mm=0.2,  lambda_W_mK=0.17, role="breather",     include_in_u_value=False)
    cavity        = ResolverLayer("Cavity 25mm",   thickness_mm=25.0, lambda_W_mK=0.17, role="cavity",       include_in_u_value=False)
    service_void  = ResolverLayer("Service void",  thickness_mm=50.0, lambda_W_mK=0.17, role="service_void", include_in_u_value=False)
    structural    = ResolverLayer("Concrete 150mm",thickness_mm=150.0,lambda_W_mK=1.15, role="structure",    include_in_u_value=True)

    layers = [vcl, service_void, structural, breather, cavity]
    result = resolve(layers, "Floor")
    expected = 0.2 + 50.0 + 150.0 + 0.2 + 25.0
    assert result.total_thickness_mm == pytest.approx(expected, abs=0.1)
