"""
Starter finish catalogue seed — ~27 customer-facing options.

Designed for Sweden / Nordic pod market.
All images: generated_placeholder or missing.
No unapproved supplier images.
Supplier/product links stored on internal_description only.

Run from backend/:
    python seeds/finish_catalogue_seed.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from app.db import SessionLocal
from app.models import FinishCatalogueItem

ITEMS = [
    # ── External cladding ─────────────────────────────────────────────────────
    dict(
        code="ext_cladding_painted_timber_std",
        category="external_cladding",
        name="Painted Timber Cladding — Standard",
        customer_name="Painted Timber Façade",
        customer_description=(
            "Clean painted timber façade suitable for modern garden offices and studio pods. "
            "Available in white, grey or dark tones. Low maintenance with periodic repainting."
        ),
        internal_description=(
            "Painted softwood cladding, typically 22×95mm or similar profile. "
            "Specify profile, paint system and colour at order."
        ),
        unit="m2",
        quantity_rule="per_m2_wall_area",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["base_cladding", "painted"],
        sort_hint=10,
        is_active=True,
    ),
    dict(
        code="ext_cladding_stained_timber_natural",
        category="external_cladding",
        name="Stained Timber Cladding — Natural",
        customer_name="Stained Timber — Natural Finish",
        customer_description=(
            "Natural timber appearance with stained finish for a warmer Scandinavian look. "
            "Semi-transparent stain shows natural wood grain. Periodic maintenance required."
        ),
        internal_description=(
            "Oiled or stained softwood/hardwood cladding. "
            "Specify profile and stain system at order. Typical: Sioo:x or similar."
        ),
        unit="m2",
        quantity_rule="per_m2_wall_area",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["base_cladding", "natural"],
        sort_hint=20,
        is_active=True,
    ),
    dict(
        code="ext_cladding_fibre_cement_premium",
        category="external_cladding",
        name="Fibre Cement Cladding — Premium",
        customer_name="Fibre Cement — Premium Façade",
        customer_description=(
            "Low-maintenance premium façade board with a clean contemporary appearance. "
            "Factory finish, no painting required. Suitable for humid Nordic climates."
        ),
        internal_description=(
            "Fibre cement board system, e.g. Equitone, Cembrit or similar. "
            "Specify colour, profile and fixing system at order."
        ),
        unit="m2",
        quantity_rule="per_m2_wall_area",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["premium_cladding", "modern"],
        sort_hint=30,
        is_active=True,
    ),

    # ── Internal paint ────────────────────────────────────────────────────────
    dict(
        code="int_paint_white",
        category="internal_paint",
        name="White Painted Interior",
        customer_name="White Interior",
        customer_description=(
            "Clean white painted internal finish for a bright, simple interior. "
            "Reflects light and creates a spacious feel. Standard matt emulsion throughout."
        ),
        internal_description="White matt emulsion to plasterboard/panel substrate.",
        unit="m2",
        quantity_rule="per_m2_wall_area",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=True,
        package_tags=["base_finish", "paint"],
        sort_hint=10,
        is_active=True,
    ),
    dict(
        code="int_paint_warm_neutral",
        category="internal_paint",
        name="Warm Neutral Painted Interior",
        customer_name="Warm Neutral Interior",
        customer_description=(
            "Soft warm neutral interior finish for a calmer studio feel. "
            "Warm greige or linen tones. Creates a relaxed, liveable atmosphere."
        ),
        internal_description="Warm neutral matt emulsion — specify shade at order.",
        unit="m2",
        quantity_rule="per_m2_wall_area",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["upgrade_finish", "paint"],
        sort_hint=20,
        is_active=True,
    ),
    dict(
        code="int_paint_premium_colour",
        category="internal_paint",
        name="Premium Colour Paint Finish",
        customer_name="Selected Colour Interior",
        customer_description=(
            "Selected colour paint finish for a more personal interior. "
            "Choose from a curated palette of Scandinavian-inspired tones. "
            "Final colour confirmed at order stage."
        ),
        internal_description="Premium paint system — Jotun, Sherwin-Williams or equivalent. Colour TBC.",
        unit="m2",
        quantity_rule="per_m2_wall_area",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["premium_finish", "paint"],
        sort_hint=30,
        is_active=True,
    ),

    # ── Timber feature finish ─────────────────────────────────────────────────
    dict(
        code="int_timber_feature_wall",
        category="internal_timber_finish",
        name="Timber Feature Wall",
        customer_name="Timber Feature Wall",
        customer_description=(
            "Decorative timber feature wall to create a warmer interior character. "
            "Typically applied to one wall — adds natural texture and warmth to the pod."
        ),
        internal_description=(
            "Slat panelling or solid timber board feature wall. "
            "Specify timber species, profile and finish at order."
        ),
        unit="m2",
        quantity_rule="per_m2_wall_area",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["premium_finish", "timber"],
        sort_hint=10,
        is_active=True,
    ),

    # ── Flooring ──────────────────────────────────────────────────────────────
    dict(
        code="flooring_budget_laminate",
        category="flooring",
        name="Budget Laminate Flooring",
        customer_name="Laminate Floor",
        customer_description=(
            "Cost-effective laminate floor finish suitable for office and light residential use. "
            "Easy to install and clean. Available in light oak or neutral grey tones."
        ),
        internal_description="AC4-rated click laminate. Specify decor at order.",
        unit="m2",
        quantity_rule="per_m2_floor_area",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["base_finish", "flooring"],
        sort_hint=10,
        is_active=True,
    ),
    dict(
        code="flooring_durable_lvt",
        category="flooring",
        name="Durable Vinyl / LVT Flooring",
        customer_name="LVT Vinyl Floor",
        customer_description=(
            "Durable and easy-clean floor finish suitable for higher-use pods. "
            "Water-resistant. Comfortable underfoot. Available in wood and stone effects."
        ),
        internal_description="Click-lock LVT 5mm+ wear layer. Specify decor at order.",
        unit="m2",
        quantity_rule="per_m2_floor_area",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["standard_finish", "flooring"],
        sort_hint=20,
        is_active=True,
    ),
    dict(
        code="flooring_engineered_timber",
        category="flooring",
        name="Engineered Timber Floor",
        customer_name="Engineered Timber Floor",
        customer_description=(
            "Premium timber floor finish for a warmer residential interior. "
            "Real wood surface, brushed and oiled. Suitable for underfloor heating."
        ),
        internal_description="Engineered oak or similar 3-ply. Specify species and finish at order.",
        unit="m2",
        quantity_rule="per_m2_floor_area",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["premium_finish", "flooring"],
        lead_time_note="4–6 weeks",
        sort_hint=30,
        is_active=True,
    ),

    # ── Furniture ─────────────────────────────────────────────────────────────
    dict(
        code="furniture_office_desk_chair_set",
        category="furniture_set",
        name="Office Desk + Chair Set",
        customer_name="Office Desk + Chair",
        customer_description=(
            "Simple office furniture set with desk and chair allowance. "
            "Suitable for home office and garden studio pods."
        ),
        internal_description=(
            "Desk + ergonomic chair allowance. IKEA/equivalent starting point — "
            "do not show supplier image unless approved. Final brand TBC."
        ),
        unit="set",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["furniture", "office"],
        sort_hint=10,
        is_active=True,
    ),
    dict(
        code="furniture_single_bed_set",
        category="furniture_set",
        name="Single Bed Set",
        customer_name="Single Bed",
        customer_description="Basic single bed package allowance. Frame and mattress included.",
        internal_description="Single 90cm bed frame + mattress. IKEA/equivalent starting point.",
        unit="set",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["furniture", "bedroom"],
        sort_hint=20,
        is_active=True,
    ),
    dict(
        code="furniture_double_bed_set",
        category="furniture_set",
        name="Double Bed Set",
        customer_name="Double Bed",
        customer_description="Basic double bed package allowance. Frame and mattress included.",
        internal_description="Double 140cm bed frame + mattress. IKEA/equivalent starting point.",
        unit="set",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["furniture", "bedroom"],
        sort_hint=30,
        is_active=True,
    ),
    dict(
        code="furniture_studio_table_chairs",
        category="furniture_set",
        name="Studio Table + Chairs Set",
        customer_name="Table + Chairs",
        customer_description=(
            "Small table and chairs package for studio or guest pod use. "
            "Seats 2–4 persons. Suitable for dining, meetings or casual workspace."
        ),
        internal_description="Compact table 800–1200mm + 2–4 chairs. IKEA/equivalent. Brand TBC.",
        unit="set",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["furniture", "studio"],
        sort_hint=40,
        is_active=True,
    ),

    # ── Sanitaryware ──────────────────────────────────────────────────────────
    dict(
        code="sanitary_basic_wc_vanity_set",
        category="sanitaryware",
        name="Basic WC + Vanity Set",
        customer_name="Basic WC + Vanity",
        customer_description=(
            "Basic WC and vanity allowance for bathroom pod configurations. "
            "Includes close-coupled WC and wall-hung vanity unit with basin."
        ),
        internal_description="Geberit / Gustavsberg / IFÖ or equivalent. Specify brand at order.",
        unit="set",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["bathroom", "sanitaryware"],
        sort_hint=10,
        is_active=True,
    ),
    dict(
        code="sanitary_premium_wc_vanity_set",
        category="sanitaryware",
        name="Premium WC + Vanity Set",
        customer_name="Premium WC + Vanity",
        customer_description=(
            "Premium bathroom fixture allowance for upgraded pod configurations. "
            "Wall-hung WC with concealed cistern and designer vanity unit."
        ),
        internal_description=(
            "TOTO / Duravit / Villeroy & Boch or equivalent — store reference internally. "
            "Do not show product image unless approved. Specify brand at order."
        ),
        unit="set",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["bathroom", "sanitaryware", "premium"],
        sort_hint=20,
        is_active=True,
    ),
    dict(
        code="vanity_unit_allowance",
        category="vanity_unit",
        name="Vanity Unit Allowance",
        customer_name="Vanity Unit",
        customer_description="Basic vanity unit allowance. Wall-hung unit with basin and soft-close door.",
        internal_description="600mm vanity allowance — IFÖ, Gustavsberg or equivalent.",
        unit="each",
        quantity_rule="each",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["bathroom", "vanity"],
        sort_hint=10,
        is_active=True,
    ),

    # ── Kitchenette ───────────────────────────────────────────────────────────
    dict(
        code="kitchenette_basic",
        category="kitchenette",
        name="Basic Kitchenette",
        customer_name="Basic Kitchenette",
        customer_description=(
            "Compact kitchenette allowance for studio or guest pod configurations. "
            "Includes base unit, worktop, sink and 2-ring hob allowance."
        ),
        internal_description="1200–1500mm kitchenette. IKEA Metod or equivalent. Specify at order.",
        unit="set",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["kitchen", "kitchenette"],
        lead_time_note="6–8 weeks",
        sort_hint=10,
        is_active=True,
    ),
    dict(
        code="kitchenette_enhanced",
        category="kitchenette",
        name="Enhanced Kitchenette",
        customer_name="Enhanced Kitchenette",
        customer_description=(
            "Upgraded kitchenette allowance with improved storage and finish. "
            "Wall units, better worktop and integrated appliance allowance."
        ),
        internal_description=(
            "1500–2000mm kitchenette + wall units. Premium worktop allowance. "
            "IKEA Metod / HTH or equivalent. Specify at order."
        ),
        unit="set",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["kitchen", "kitchenette", "enhanced"],
        lead_time_note="6–10 weeks",
        sort_hint=20,
        is_active=True,
    ),

    # ── Lighting ──────────────────────────────────────────────────────────────
    dict(
        code="lighting_basic_ceiling_pkg",
        category="lighting",
        name="Basic Ceiling Light Package",
        customer_name="Basic Ceiling Lighting",
        customer_description=(
            "Simple internal lighting allowance. "
            "Surface-mounted or pendant ceiling fittings throughout. "
            "Number and style confirmed at order."
        ),
        internal_description="Basic surface-mount LED ceiling light(s). Ensto/Airam or equivalent.",
        unit="package",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["lighting", "base_pkg"],
        sort_hint=10,
        is_active=True,
    ),
    dict(
        code="lighting_led_downlight_pkg",
        category="lighting",
        name="LED Downlight Package",
        customer_name="LED Downlights",
        customer_description=(
            "Clean recessed or surface LED lighting package. "
            "Even illumination throughout the pod. "
            "CCT and quantity confirmed at order."
        ),
        internal_description="Recessed LED downlights — LEDVANCE/Philips or equivalent. Qty per floor area.",
        unit="package",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["lighting", "downlights"],
        sort_hint=20,
        is_active=True,
    ),
    dict(
        code="lighting_feature_upgrade",
        category="lighting",
        name="Feature Lighting Upgrade",
        customer_name="Feature Lighting",
        customer_description=(
            "Decorative lighting allowance for a more designed interior. "
            "Includes pendant or accent lighting in addition to base lighting package."
        ),
        internal_description="Feature pendant / accent lighting — client to specify brand/style.",
        unit="package",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["lighting", "feature"],
        sort_hint=30,
        is_active=True,
    ),

    # ── CCTV / Data ───────────────────────────────────────────────────────────
    dict(
        code="cctv_cat6_prewire_ready",
        category="cctv_data",
        name="CCTV-Ready CAT6 Prewire",
        customer_name="Network + CCTV Prewire",
        customer_description=(
            "CAT6 prewire allowance for future IP camera installation. "
            "Conduit and back-boxes included. Active cameras not included."
        ),
        internal_description="CAT6 home-runs + conduit + back-boxes. Active equipment excluded.",
        unit="package",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["cctv_data", "prewire"],
        sort_hint=10,
        is_active=True,
    ),
    dict(
        code="cctv_basic_ip_camera_pkg",
        category="cctv_data",
        name="Basic IP Camera Package",
        customer_name="IP Camera System",
        customer_description=(
            "Basic IP camera system allowance. "
            "4-camera outdoor IP CCTV with NVR and local storage allowance. "
            "Brand and resolution TBC."
        ),
        internal_description="4× IP cameras + PoE NVR. Hikvision/Reolink/Axis allowance. Brand TBC.",
        unit="package",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["cctv_data", "camera_pkg"],
        sort_hint=20,
        is_active=True,
    ),

    # ── Solar / Battery ───────────────────────────────────────────────────────
    dict(
        code="solar_pv_ready_roof",
        category="solar_battery",
        name="PV-Ready Roof Provision",
        customer_name="Solar-Ready Roof",
        customer_description=(
            "Roof provision for future solar PV route and fixing strategy. "
            "Spare conduit runs and marked fixing/ballast zones. "
            "PV panels and electrical installation not included."
        ),
        internal_description="Conduit + zone marking. Structural note in engineer schedule.",
        unit="package",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["solar", "pv_ready"],
        notes=(
            "Solar PV installation is a provisional option only. Final design, structural "
            "fixing, electrical design, grid connection and certification must be confirmed "
            "by appointed specialists."
        ),
        sort_hint=10,
        is_active=True,
    ),
    dict(
        code="solar_pv_package_provisional",
        category="solar_battery",
        name="Solar PV Package — Provisional",
        customer_name="Solar PV — Provisional",
        customer_description=(
            "Provisional solar panel allowance. "
            "Indicative 3–4 kWp rooftop array. "
            "Final design and electrical installation by specialist required."
        ),
        internal_description=(
            "Provisional PV allowance — 3–4 kWp. Fronius/SMA + panel brand TBC. "
            "Grid connection and certification by specialist."
        ),
        unit="package",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["solar", "pv"],
        notes="Provisional allowance only. Specialist design and installation required.",
        sort_hint=20,
        is_active=True,
    ),
    dict(
        code="solar_battery_storage_provisional",
        category="solar_battery",
        name="Battery Storage — Provisional",
        customer_name="Battery Storage — Provisional",
        customer_description=(
            "Provisional battery storage allowance. "
            "Indicative 5–10 kWh home battery. "
            "Final electrical design and installation by specialist required."
        ),
        internal_description=(
            "Battery storage allowance — Tesla Powerwall / SonnenBatterie / Growatt or equivalent. "
            "Final electrical design and grid connection by specialist."
        ),
        unit="package",
        quantity_rule="package_fixed",
        price_type="allowance",
        image_source_type="generated_placeholder",
        image_approval_status="generated_placeholder",
        customer_visible=True,
        included_by_default=False,
        package_tags=["solar", "battery"],
        notes="Provisional allowance only. Specialist design and installation required.",
        sort_hint=30,
        is_active=True,
    ),
]


def run():
    db = SessionLocal()
    try:
        inserted = skipped = 0
        for row in ITEMS:
            row.pop("sort_hint", None)   # not a model field — used for human ordering above
            exists = db.query(FinishCatalogueItem).filter_by(code=row["code"]).first()
            if exists:
                skipped += 1
                continue
            db.add(FinishCatalogueItem(**row))
            inserted += 1
        db.commit()
        total = db.query(FinishCatalogueItem).count()
        print(f"Inserted {inserted} new items, {skipped} already existed. "
              f"Total catalogue items: {total}.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
