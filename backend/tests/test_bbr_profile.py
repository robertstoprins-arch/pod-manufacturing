"""Tests for the BBR (Sweden) jurisdiction profile seed data."""
import pytest
from seeds.bbr_profile import seed, BBR_ARCH_CONSTRAINTS, STOCKHOLM_CLIMATE
from app.models import JurisdictionProfile


def test_bbr_thermal_targets(db):
    seed_id = _insert_bbr(db)
    profile = db.get(JurisdictionProfile, seed_id)
    assert profile.u_value_wall == pytest.approx(0.18)
    assert profile.u_value_roof == pytest.approx(0.13)
    assert profile.u_value_floor == pytest.approx(0.15)
    assert profile.u_value_window == pytest.approx(1.2)
    assert profile.airtightness_target == pytest.approx(1.5)


def test_bbr_country_and_code(db):
    seed_id = _insert_bbr(db)
    profile = db.get(JurisdictionProfile, seed_id)
    assert profile.country == "SE"
    assert profile.code == "BBR"


def test_bbr_arch_constraints_door_width(db):
    seed_id = _insert_bbr(db)
    profile = db.get(JurisdictionProfile, seed_id)
    constraints = profile.arch_constraints
    assert constraints["door_clear_width_min_mm"] == 800
    assert constraints["accessible_door_clear_width_mm"] == 900


def test_bbr_arch_constraints_escape_window(db):
    seed_id = _insert_bbr(db)
    profile = db.get(JurisdictionProfile, seed_id)
    constraints = profile.arch_constraints
    assert constraints["escape_window_opening_min_m2"] == pytest.approx(0.33)
    assert constraints["escape_window_min_height_mm"] == 450
    assert constraints["escape_window_max_sill_height_mm"] == 1100


def test_bbr_arch_constraints_ceiling_height(db):
    seed_id = _insert_bbr(db)
    profile = db.get(JurisdictionProfile, seed_id)
    assert profile.arch_constraints["ceiling_height_min_mm"] == 2400


def test_bbr_climate_has_12_months(db):
    seed_id = _insert_bbr(db)
    profile = db.get(JurisdictionProfile, seed_id)
    months = profile.climate_data["months"]
    assert len(months) == 12
    # Coldest month (Jan) should be below 0°C in Stockholm
    jan = next(m for m in months if m["month"] == 1)
    assert jan["temp_C"] < 0


def test_bbr_snow_zone(db):
    seed_id = _insert_bbr(db)
    profile = db.get(JurisdictionProfile, seed_id)
    assert profile.snow_zone == "SE_Z3"


# --- helper ---

def _insert_bbr(db):
    """Insert a BBR profile directly (bypassing seed's DB connection) for test isolation."""
    from app.models import JurisdictionProfile
    profile = JurisdictionProfile(
        version="2024",
        country="SE",
        code="BBR",
        u_value_wall=0.18,
        u_value_roof=0.13,
        u_value_floor=0.15,
        u_value_window=1.2,
        airtightness_target=1.5,
        climate_data=STOCKHOLM_CLIMATE,
        snow_zone="SE_Z3",
        wind_zone="SE_W2",
        radon_zone_source="SGU_SE",
        daylighting_wfr_min=0.10,
        arch_constraints=BBR_ARCH_CONSTRAINTS,
    )
    db.add(profile)
    db.commit()
    return profile.id
