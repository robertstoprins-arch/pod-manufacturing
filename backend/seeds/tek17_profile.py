"""Seed: Norway TEK17 jurisdiction profile

TEK17 = Tekniske krav til byggverk (Forskrift om tekniske krav til byggverk, 2017 rev. 2022)
Run with:  python -m seeds.tek17_profile
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()
from app.models import JurisdictionProfile

# Oslo climate — monthly mean outdoor temperature (°C) and relative humidity (%)
# Source: Meteorologisk institutt climate normals 1991-2020
OSLO_CLIMATE = {
    "interior_temp_C": 20.0,
    "interior_rh_pct": 50.0,
    "months": [
        {"month": 1,  "temp_C": -3.9, "rh_pct": 82},
        {"month": 2,  "temp_C": -3.1, "rh_pct": 78},
        {"month": 3,  "temp_C": 1.7,  "rh_pct": 68},
        {"month": 4,  "temp_C": 7.3,  "rh_pct": 61},
        {"month": 5,  "temp_C": 13.0, "rh_pct": 58},
        {"month": 6,  "temp_C": 17.3, "rh_pct": 62},
        {"month": 7,  "temp_C": 20.0, "rh_pct": 65},
        {"month": 8,  "temp_C": 18.7, "rh_pct": 68},
        {"month": 9,  "temp_C": 13.1, "rh_pct": 73},
        {"month": 10, "temp_C": 7.5,  "rh_pct": 78},
        {"month": 11, "temp_C": 1.8,  "rh_pct": 83},
        {"month": 12, "temp_C": -2.3, "rh_pct": 84},
    ],
}

# TEK17 architectural constraints (§ 12, §13, §15)
TEK17_ARCH_CONSTRAINTS = {
    # Space and accessibility (TEK17 §12)
    "ceiling_height_min_mm": 2400,
    "habitable_room_area_min_m2": 7.0,
    "corridor_width_min_mm": 900,
    "accessible_door_clear_width_mm": 900,
    "door_clear_width_min_mm": 800,
    "door_clear_height_min_mm": 2000,

    # Daylighting (TEK17 §13-4)
    "window_area_min_pct_floor": 10,
    "window_ventilation_area_min_pct_floor": 1.5,

    # Fall protection (TEK17 §12-16)
    "window_fall_protection_height_mm": 800,  # stricter than BBR
    "window_sill_height_max_mm": 600,

    # Escape (TEK17 §11-14)
    "escape_window_opening_min_m2": 0.50,     # stricter than BBR
    "escape_window_min_height_mm": 500,
    "escape_window_min_width_mm": 500,
    "escape_window_max_sill_height_mm": 900,  # lower max sill height than BBR

    # Stairs (TEK17 §12-17) — residential
    "stair_rise_max_mm": 185,
    "stair_going_min_mm": 230,

    # Radon
    "radon_zone_source": "NGU_NO",            # Norges geologiske undersøkelse radon map
    "radon_action_level_Bq_m3": 200,

    # Reference
    "ref": "TEK17 (Forskrift om tekniske krav til byggverk, 2017 rev. 2022) §12, §13, §15",
}


def seed():
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    with Session() as db:
        existing = db.query(JurisdictionProfile).filter_by(code="TEK17", version="2022").first()
        if existing:
            print("TEK17 2022 profile already exists — skipping.")
            return existing.id

        profile = JurisdictionProfile(
            version="2022",
            country="NO",
            code="TEK17",

            # Thermal targets — TEK17 §14 (energy frame method)
            u_value_wall=0.18,       # W/m²K
            u_value_roof=0.13,
            u_value_floor=0.10,      # stricter floor target vs BBR
            u_value_window=0.80,     # significantly stricter than BBR 1.2
            airtightness_target=1.5, # ACH at 50Pa (TEK17 §14-2, new build requirement)

            climate_data=OSLO_CLIMATE,

            # Structural zones (Oslo mid-Norway defaults)
            snow_zone="NO_Z3",       # characteristic snow load 3.0 kN/m² (Oslo)
            wind_zone="NO_W2",       # basic wind velocity v_b0 = 22 m/s

            radon_zone_source="NGU_NO",
            daylighting_wfr_min=0.10,

            arch_constraints=TEK17_ARCH_CONSTRAINTS,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        print(f"Inserted TEK17 2022 jurisdiction profile (id={profile.id})")
        return profile.id


if __name__ == "__main__":
    seed()
