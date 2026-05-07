"""Seed: Sweden BBR jurisdiction profile

BBR = Boverkets byggregler (BFS 2011:6 with amendments to 2024)
Run with:  python -m seeds.bbr_profile
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()
from app.models import JurisdictionProfile

# Stockholm climate — monthly mean outdoor temperature (°C) and relative humidity (%)
# Source: SMHI climate normals 1991-2020
STOCKHOLM_CLIMATE = {
    "interior_temp_C": 20.0,
    "interior_rh_pct": 50.0,
    "months": [
        {"month": 1,  "temp_C": -2.8, "rh_pct": 85},
        {"month": 2,  "temp_C": -2.8, "rh_pct": 82},
        {"month": 3,  "temp_C": 0.7,  "rh_pct": 75},
        {"month": 4,  "temp_C": 6.3,  "rh_pct": 69},
        {"month": 5,  "temp_C": 12.0, "rh_pct": 65},
        {"month": 6,  "temp_C": 16.6, "rh_pct": 67},
        {"month": 7,  "temp_C": 19.7, "rh_pct": 71},
        {"month": 8,  "temp_C": 18.8, "rh_pct": 73},
        {"month": 9,  "temp_C": 13.5, "rh_pct": 77},
        {"month": 10, "temp_C": 7.7,  "rh_pct": 82},
        {"month": 11, "temp_C": 2.4,  "rh_pct": 86},
        {"month": 12, "temp_C": -1.2, "rh_pct": 86},
    ],
}

# BBR architectural constraints (BFS 2011:6 ch. 3, 6, 8)
BBR_ARCH_CONSTRAINTS = {
    # Space and accessibility (BBR ch. 3)
    "ceiling_height_min_mm": 2400,
    "habitable_room_area_min_m2": 7.0,
    "corridor_width_min_mm": 900,
    "accessible_door_clear_width_mm": 900,    # accessible route requirement
    "door_clear_width_min_mm": 800,
    "door_clear_height_min_mm": 2000,

    # Daylighting (BBR 6:322)
    "window_area_min_pct_floor": 10,          # window area ≥ 10% of floor area per habitable room
    "window_ventilation_area_min_pct_floor": 2,

    # Fall protection (BBR 8:23) — window sill height
    "window_fall_protection_height_mm": 700,  # sill must be ≥ 700mm above floor, or guarded
    "window_sill_height_max_mm": 600,         # if sill < 600mm, fall guard required

    # Escape (BBR 5:332)
    "escape_window_opening_min_m2": 0.33,     # minimum free opening area
    "escape_window_min_height_mm": 450,       # minimum opening dimension (height)
    "escape_window_min_width_mm": 450,        # minimum opening dimension (width)
    "escape_window_max_sill_height_mm": 1100, # sill must be reachable

    # Stairs (BBR 8:22) — residential
    "stair_rise_max_mm": 185,
    "stair_going_min_mm": 230,

    # Radon
    "radon_zone_source": "SGU_SE",            # Geological Survey of Sweden radon map
    "radon_action_level_Bq_m3": 200,

    # Reference
    "ref": "BBR BFS 2011:6, amended to 2024, ch. 3, 5, 6, 8",
}


def seed():
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    with Session() as db:
        existing = db.query(JurisdictionProfile).filter_by(code="BBR", version="2024").first()
        if existing:
            print("BBR 2024 profile already exists — skipping.")
            return existing.id

        profile = JurisdictionProfile(
            version="2024",
            country="SE",
            code="BBR",

            # Thermal targets — BBR ch. 9 (Ep-number method, typical new build targets)
            u_value_wall=0.18,       # W/m²K
            u_value_roof=0.13,
            u_value_floor=0.15,
            u_value_window=1.2,
            airtightness_target=1.5, # ACH at 50Pa (q50 = 0.6 l/s·m² ≈ 1.5 ACH for typical pod)

            climate_data=STOCKHOLM_CLIMATE,

            # Structural zones (Stockholm mid-Sweden defaults; project-level override available)
            snow_zone="SE_Z3",       # characteristic snow load 2.5 kN/m²
            wind_zone="SE_W2",       # basic wind velocity v_b0 = 25 m/s

            radon_zone_source="SGU_SE",
            daylighting_wfr_min=0.10,

            arch_constraints=BBR_ARCH_CONSTRAINTS,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        print(f"Inserted BBR 2024 jurisdiction profile (id={profile.id})")
        return profile.id


if __name__ == "__main__":
    seed()
