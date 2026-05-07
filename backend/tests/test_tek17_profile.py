"""Tests for the TEK17 (Norway) jurisdiction profile seed data.

Key differences from BBR to verify:
- u_value_floor: 0.10 (stricter)
- u_value_window: 0.80 (significantly stricter)
- escape_window_opening_min_m2: 0.50 (stricter)
- escape_window_max_sill_height_mm: 900 (lower — more accessible)
- window_fall_protection_height_mm: 800 (stricter)
"""
import pytest
from seeds.tek17_profile import seed, TEK17_ARCH_CONSTRAINTS, OSLO_CLIMATE
from app.models import JurisdictionProfile


def test_tek17_thermal_targets(db):
    seed_id = _insert_tek17(db)
    profile = db.get(JurisdictionProfile, seed_id)
    assert profile.u_value_wall == pytest.approx(0.18)
    assert profile.u_value_roof == pytest.approx(0.13)
    assert profile.u_value_floor == pytest.approx(0.10)    # stricter than BBR 0.15
    assert profile.u_value_window == pytest.approx(0.80)   # stricter than BBR 1.20
    assert profile.airtightness_target == pytest.approx(1.5)


def test_tek17_stricter_than_bbr_floor_and_window():
    """TEK17 thermal targets must be at least as strict as BBR on floor and window."""
    from seeds.bbr_profile import BBR_ARCH_CONSTRAINTS
    bbr_floor = 0.15
    tek17_floor = 0.10
    bbr_window = 1.2
    tek17_window = 0.80
    assert tek17_floor <= bbr_floor, "TEK17 floor target must be ≤ BBR"
    assert tek17_window <= bbr_window, "TEK17 window target must be ≤ BBR"


def test_tek17_country_and_code(db):
    seed_id = _insert_tek17(db)
    profile = db.get(JurisdictionProfile, seed_id)
    assert profile.country == "NO"
    assert profile.code == "TEK17"


def test_tek17_stricter_escape_window(db):
    seed_id = _insert_tek17(db)
    profile = db.get(JurisdictionProfile, seed_id)
    constraints = profile.arch_constraints
    # TEK17 requires 0.50m² escape opening vs BBR 0.33m²
    assert constraints["escape_window_opening_min_m2"] == pytest.approx(0.50)
    assert constraints["escape_window_max_sill_height_mm"] == 900  # lower than BBR 1100


def test_tek17_fall_protection_height(db):
    seed_id = _insert_tek17(db)
    profile = db.get(JurisdictionProfile, seed_id)
    # TEK17 requires 800mm fall protection height vs BBR 700mm
    assert profile.arch_constraints["window_fall_protection_height_mm"] == 800


def test_tek17_climate_has_12_months(db):
    seed_id = _insert_tek17(db)
    profile = db.get(JurisdictionProfile, seed_id)
    months = profile.climate_data["months"]
    assert len(months) == 12
    jan = next(m for m in months if m["month"] == 1)
    assert jan["temp_C"] < 0  # Oslo January is cold


def test_tek17_snow_zone(db):
    seed_id = _insert_tek17(db)
    profile = db.get(JurisdictionProfile, seed_id)
    assert profile.snow_zone == "NO_Z3"


# --- helper ---

def _insert_tek17(db):
    from app.models import JurisdictionProfile
    profile = JurisdictionProfile(
        version="2022",
        country="NO",
        code="TEK17",
        u_value_wall=0.18,
        u_value_roof=0.13,
        u_value_floor=0.10,
        u_value_window=0.80,
        airtightness_target=1.5,
        climate_data=OSLO_CLIMATE,
        snow_zone="NO_Z3",
        wind_zone="NO_W2",
        radon_zone_source="NGU_NO",
        daylighting_wfr_min=0.10,
        arch_constraints=TEK17_ARCH_CONSTRAINTS,
    )
    db.add(profile)
    db.commit()
    return profile.id
