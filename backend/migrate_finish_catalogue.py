"""Create finish_catalogue_items table and seed initial catalogue entries."""
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('../.env')
from app.db import engine, SessionLocal
from app.models import Base, FinishCatalogueItem

Base.metadata.create_all(engine, tables=[FinishCatalogueItem.__table__])
print("Table created: finish_catalogue_items")

db = SessionLocal()

SEED = [
    # ── External cladding ─────────────────────────────────────────────────────
    dict(
        code="ext_cladding_larch_natural",
        category="external_cladding",
        name="Natural Larch Cladding",
        customer_name="Natural Larch — Untreated",
        customer_description="Western red larch horizontal cladding, natural untreated finish. "
                             "Weathers to a silver-grey over time.",
        internal_description="Tongue-and-groove or open-joint profile. Specify profile at order.",
        supplier_name="Generic / TBC",
        unit="m2", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="per_m2_wall_area",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["base_cladding", "natural"],
        lead_time_note="4–6 weeks",
        is_active=True,
    ),
    dict(
        code="ext_cladding_larch_charred",
        category="external_cladding",
        name="Charred Larch Cladding (Shou Sugi Ban)",
        customer_name="Charred Larch — Black",
        customer_description="Shou sugi ban charred larch cladding. Deep black finish, "
                             "low maintenance, striking appearance.",
        internal_description="Specify charring depth and oil finish at order.",
        supplier_name="Generic / TBC",
        unit="m2", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="per_m2_wall_area",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["premium_cladding", "charred"],
        lead_time_note="6–8 weeks",
        is_active=True,
    ),
    dict(
        code="ext_cladding_cement_board_grey",
        category="external_cladding",
        name="Fibre Cement Board — Anthracite Grey",
        customer_name="Cement Board — Dark Grey",
        customer_description="Fibre cement panel cladding system, anthracite grey finish. "
                             "Low maintenance, modern appearance.",
        supplier_name="Generic / TBC",
        unit="m2", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="per_m2_wall_area",
        included_by_default=True, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["base_cladding", "modern"],
        lead_time_note="4–6 weeks",
        is_active=True,
    ),
    dict(
        code="ext_cladding_metal_zincalume",
        category="external_cladding",
        name="Standing Seam Metal — Zincalume",
        customer_name="Metal Standing Seam — Silver",
        customer_description="Zincalume or similar standing seam metal cladding. "
                             "Industrial-modern aesthetic, very durable.",
        supplier_name="Generic / TBC",
        unit="m2", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="per_m2_wall_area",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["premium_cladding", "metal"],
        lead_time_note="6–10 weeks",
        is_active=True,
    ),

    # ── Internal paint ────────────────────────────────────────────────────────
    dict(
        code="int_paint_white_standard",
        category="internal_paint",
        name="White Emulsion — Standard",
        customer_name="White Matt Emulsion",
        customer_description="Standard white matt emulsion throughout. Clean, simple finish.",
        supplier_name="Generic",
        unit="m2", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="per_m2_wall_area",
        included_by_default=True, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["base_finish", "paint"],
        is_active=True,
    ),
    dict(
        code="int_paint_colour_feature",
        category="internal_paint",
        name="Feature Wall Paint — Client Colour",
        customer_name="Feature Wall — Client Colour Choice",
        customer_description="One feature wall in client-selected colour. "
                             "Remaining walls in white matt.",
        supplier_name="Generic / TBC",
        unit="m2", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="per_m2_wall_area",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["upgrade_finish", "paint"],
        is_active=True,
    ),

    # ── Flooring ──────────────────────────────────────────────────────────────
    dict(
        code="flooring_lvt_oak",
        category="flooring",
        name="LVT Flooring — Oak Effect",
        customer_name="Luxury Vinyl Tile — Oak",
        customer_description="Click-lock LVT flooring, oak effect. Water resistant, "
                             "durable and comfortable underfoot.",
        supplier_name="Generic / TBC",
        unit="m2", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="per_m2_floor_area",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["standard_finish", "flooring"],
        is_active=True,
    ),
    dict(
        code="flooring_engineered_oak",
        category="flooring",
        name="Engineered Oak Flooring",
        customer_name="Engineered Oak — Brushed",
        customer_description="Engineered oak floating floor, brushed and oiled finish. "
                             "Premium appearance, real wood surface.",
        supplier_name="Generic / TBC",
        unit="m2", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="per_m2_floor_area",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["premium_finish", "flooring"],
        lead_time_note="4–6 weeks",
        is_active=True,
    ),
    dict(
        code="flooring_polished_concrete_look",
        category="flooring",
        name="Polished Concrete Effect — Microcement",
        customer_name="Microcement — Polished Concrete Look",
        customer_description="Applied microcement finish, polished concrete aesthetic. "
                             "Seamless, contemporary finish.",
        supplier_name="Generic / TBC",
        unit="m2", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="per_m2_floor_area",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["premium_finish", "flooring"],
        lead_time_note="4–6 weeks",
        is_active=True,
    ),

    # ── Sanitaryware ──────────────────────────────────────────────────────────
    dict(
        code="sanitary_shower_enclosure_std",
        category="sanitaryware",
        name="Shower Enclosure — Standard",
        customer_name="Walk-In Shower Enclosure",
        customer_description="Standard frameless shower enclosure with tray and thermostatic mixer. "
                             "Final selection subject to pod dimension and layout.",
        supplier_name="Generic / TBC",
        unit="each", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="each",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["bathroom", "sanitaryware"],
        is_active=True,
    ),

    # ── Toilet ────────────────────────────────────────────────────────────────
    dict(
        code="toilet_wall_hung_std",
        category="toilet",
        name="Wall-Hung WC — Standard",
        customer_name="Wall-Hung Toilet",
        customer_description="Wall-hung WC with concealed cistern and soft-close seat. "
                             "Clean, space-saving design.",
        supplier_name="Generic / TBC",
        unit="each", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="each",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["bathroom", "toilet"],
        is_active=True,
    ),
    dict(
        code="toilet_close_coupled_std",
        category="toilet",
        name="Close-Coupled WC — Standard",
        customer_name="Close-Coupled Toilet",
        customer_description="Close-coupled WC with dual flush and soft-close seat.",
        supplier_name="Generic / TBC",
        unit="each", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="each",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["bathroom", "toilet"],
        is_active=True,
    ),

    # ── Vanity unit ───────────────────────────────────────────────────────────
    dict(
        code="vanity_unit_600_white",
        category="vanity_unit",
        name="Vanity Unit 600mm — White Gloss",
        customer_name="600mm Vanity Unit — White",
        customer_description="600mm wall-hung vanity unit with basin, white gloss finish. "
                             "Soft-close door.",
        supplier_name="Generic / TBC",
        unit="each", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="each",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["bathroom", "vanity"],
        is_active=True,
    ),

    # ── Kitchenette ───────────────────────────────────────────────────────────
    dict(
        code="kitchenette_base_1500",
        category="kitchenette",
        name="Kitchenette — 1500mm Base",
        customer_name="Kitchenette Unit — 1500mm",
        customer_description="Compact kitchenette: 1500mm base unit with worktop, under-counter "
                             "fridge space, 2-ring induction hob and single sink. "
                             "Colour and door style TBC.",
        supplier_name="Generic / TBC",
        unit="set", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="package_fixed",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["kitchen", "kitchenette"],
        lead_time_note="6–10 weeks",
        is_active=True,
    ),

    # ── Furniture sets ────────────────────────────────────────────────────────
    dict(
        code="furniture_single_bed",
        category="furniture_set",
        name="Single Bed Frame + Mattress",
        customer_name="Single Bed",
        customer_description="Single bed frame with medium-firm mattress. "
                             "Frame style and colour subject to final selection.",
        supplier_name="Generic / TBC",
        unit="each", unit_cost=270.0, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="each",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["furniture", "bedroom"],
        is_active=True,
    ),
    dict(
        code="furniture_double_bed",
        category="furniture_set",
        name="Double Bed Frame + Mattress",
        customer_name="Double Bed",
        customer_description="Double bed frame with medium-firm mattress. "
                             "Frame style and colour subject to final selection.",
        supplier_name="Generic / TBC",
        unit="each", unit_cost=370.0, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="each",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["furniture", "bedroom"],
        is_active=True,
    ),
    dict(
        code="furniture_office_desk_chair",
        category="furniture_set",
        name="Office Desk + Ergonomic Chair",
        customer_name="Desk + Chair Set",
        customer_description="1200–1400mm work desk with ergonomic task chair. "
                             "Style subject to final selection.",
        supplier_name="Generic / TBC",
        unit="set", unit_cost=370.0, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="package_fixed",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["furniture", "office"],
        is_active=True,
    ),

    # ── Lighting ──────────────────────────────────────────────────────────────
    dict(
        code="lighting_recessed_led_pkg",
        category="lighting",
        name="Recessed LED Downlights Package",
        customer_name="LED Downlights — Recessed",
        customer_description="Recessed LED downlight package. Number and layout to suit pod size. "
                             "CCT and finish TBC.",
        supplier_name="Generic / TBC",
        unit="set", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="package_fixed",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["lighting", "base_pkg"],
        is_active=True,
    ),
    dict(
        code="lighting_pendant_feature",
        category="lighting",
        name="Feature Pendant Light",
        customer_name="Feature Pendant — Client Choice",
        customer_description="Pendant light fitting — client to specify brand and style. "
                             "Allowance included.",
        supplier_name="Generic / TBC",
        unit="each", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="each",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["lighting", "feature"],
        is_active=True,
    ),

    # ── CCTV / Data ───────────────────────────────────────────────────────────
    dict(
        code="cctv_cat6_prewire",
        category="cctv_data",
        name="CAT6 Data Prewire",
        customer_name="CAT6 Network Prewire",
        customer_description="CAT6 home-runs to external camera positions and data/comms location. "
                             "Conduit and back-boxes included. Active equipment excluded.",
        supplier_name="Generic",
        unit="set", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="package_fixed",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["cctv_data", "prewire"],
        is_active=True,
    ),
    dict(
        code="cctv_4_camera_ip_pkg",
        category="cctv_data",
        name="4-Camera IP CCTV Package",
        customer_name="4-Camera IP Security Package",
        customer_description="Basic 4-camera IP CCTV system. PoE switch and NVR allowance included. "
                             "Brand and resolution TBC.",
        supplier_name="Generic / TBC",
        unit="set", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="package_fixed",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["cctv_data", "camera_pkg"],
        is_active=True,
    ),

    # ── Solar / Battery ───────────────────────────────────────────────────────
    dict(
        code="solar_pv_ready_provision",
        category="solar_battery",
        name="PV-Ready Roof Provision",
        customer_name="Solar-Ready Roof",
        customer_description="Spare conduit runs, marked fixing/ballast zones and load path "
                             "noted in structural schedule. PV panels not included.",
        supplier_name="Generic",
        unit="set", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="package_fixed",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["solar", "pv_ready"],
        notes="Solar PV installation is a provisional option only. Final design, structural "
              "fixing, electrical design, grid connection and certification must be confirmed "
              "by appointed specialists.",
        is_active=True,
    ),
    dict(
        code="solar_pv_4kw_provisional",
        category="solar_battery",
        name="Solar PV — 4 kWp Provisional Allowance",
        customer_name="Solar PV 4 kWp",
        customer_description="4 kWp roof-mounted solar PV system — provisional allowance only. "
                             "Final design and installation by specialist.",
        supplier_name="Generic / TBC",
        unit="set", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="package_fixed",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["solar", "pv"],
        notes="Provisional option only. Specialist design and installation required.",
        is_active=True,
    ),
    dict(
        code="solar_battery_storage_10kwh",
        category="solar_battery",
        name="Battery Storage — 10 kWh Provisional",
        customer_name="Battery Storage 10 kWh",
        customer_description="10 kWh home battery storage — provisional allowance only. "
                             "Final design and installation by specialist.",
        supplier_name="Generic / TBC",
        unit="set", unit_cost=None, currency="EUR",
        price_type="allowance", default_quantity=1.0, quantity_rule="package_fixed",
        included_by_default=False, customer_visible=True, internal_only=False,
        image_source_type="none", image_approval_status="missing",
        package_tags=["solar", "battery"],
        notes="Provisional option only. Specialist design and installation required.",
        is_active=True,
    ),
]

try:
    inserted = 0
    skipped  = 0
    for row in SEED:
        exists = db.query(FinishCatalogueItem).filter_by(code=row["code"]).first()
        if exists:
            skipped += 1
            continue
        db.add(FinishCatalogueItem(**row))
        inserted += 1
    db.commit()
    print(f"Seeded {inserted} items ({skipped} already existed).")
finally:
    db.close()
