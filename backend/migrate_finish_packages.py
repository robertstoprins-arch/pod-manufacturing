"""Create finish_packages + finish_package_items tables and seed 7 starter packages."""
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('../.env')
from app.db import engine, SessionLocal
from app.models import Base, FinishPackage, FinishPackageItem, FinishCatalogueItem

Base.metadata.create_all(engine, tables=[
    FinishPackage.__table__,
    FinishPackageItem.__table__,
])
print("Tables created: finish_packages, finish_package_items")

db = SessionLocal()

def _item(code: str) -> int:
    """Return catalogue item id by code, raise if missing."""
    obj = db.query(FinishCatalogueItem).filter_by(code=code).first()
    if obj is None:
        raise ValueError(f"Catalogue item not found: {code}")
    return obj.id


# Catalogue item id lookup (by code → id)
ITEMS = {
    # paint
    "int_paint_white_standard":          _item("int_paint_white_standard"),
    "int_paint_colour_feature":          _item("int_paint_colour_feature"),
    # flooring
    "flooring_lvt_oak":                  _item("flooring_lvt_oak"),
    "flooring_engineered_oak":           _item("flooring_engineered_oak"),
    # furniture
    "furniture_single_bed":              _item("furniture_single_bed"),
    "furniture_double_bed":              _item("furniture_double_bed"),
    "furniture_office_desk_chair":       _item("furniture_office_desk_chair"),
    # bathroom
    "sanitary_shower_enclosure_std":     _item("sanitary_shower_enclosure_std"),
    "toilet_close_coupled_std":          _item("toilet_close_coupled_std"),
    "toilet_wall_hung_std":              _item("toilet_wall_hung_std"),
    "vanity_unit_600_white":             _item("vanity_unit_600_white"),
    # kitchenette
    "kitchenette_base_1500":             _item("kitchenette_base_1500"),
    # lighting
    "lighting_recessed_led_pkg":         _item("lighting_recessed_led_pkg"),
    "lighting_pendant_feature":          _item("lighting_pendant_feature"),
    # cladding
    "ext_cladding_cement_board_grey":    _item("ext_cladding_cement_board_grey"),
    "ext_cladding_larch_natural":        _item("ext_cladding_larch_natural"),
    "ext_cladding_larch_charred":        _item("ext_cladding_larch_charred"),
    "ext_cladding_metal_zincalume":      _item("ext_cladding_metal_zincalume"),
    # solar / cctv
    "solar_pv_ready_provision":          _item("solar_pv_ready_provision"),
    "solar_pv_4kw_provisional":          _item("solar_pv_4kw_provisional"),
    "solar_battery_storage_10kwh":       _item("solar_battery_storage_10kwh"),
    "cctv_cat6_prewire":                 _item("cctv_cat6_prewire"),
    "cctv_4_camera_ip_pkg":              _item("cctv_4_camera_ip_pkg"),
}


# ── Package definitions ───────────────────────────────────────────────────────
# Each entry: (package_fields_dict, [(catalogue_code, qty, is_required, notes)])

PACKAGES = [
    # 1 ─ Standard Office
    (
        dict(
            code="pkg_office_standard",
            name="Standard Office Package",
            customer_name="Standard Home Office",
            customer_description=(
                "Everything you need for a productive home office: "
                "durable LVT flooring, white painted walls, desk + ergonomic chair, "
                "and a recessed LED lighting package."
            ),
            internal_description="LVT floor + white paint + office desk/chair + LED lighting.",
            package_category="office",
            default_selected=False,
            customer_visible=True,
            is_active=True,
            sort_order=10,
        ),
        [
            ("int_paint_white_standard",    1.0, True,  "Applied to all walls and ceiling"),
            ("flooring_lvt_oak",            1.0, True,  "LVT per m² floor area"),
            ("furniture_office_desk_chair", 1.0, True,  "1× desk + chair set"),
            ("lighting_recessed_led_pkg",   1.0, True,  "Recessed LED downlights package"),
        ],
    ),

    # 2 ─ Guest Sleep
    (
        dict(
            code="pkg_guest_sleep",
            name="Guest Sleep Package",
            customer_name="Guest Bedroom",
            customer_description=(
                "A comfortable guest bedroom: warm white painted walls, "
                "LVT flooring, double bed with mattress, and a soft LED lighting package."
            ),
            internal_description="White paint + LVT floor + double bed + LED lighting.",
            package_category="guest_sleep",
            default_selected=False,
            customer_visible=True,
            is_active=True,
            sort_order=20,
        ),
        [
            ("int_paint_white_standard",  1.0, True,  "White matt throughout"),
            ("flooring_lvt_oak",          1.0, True,  "LVT per m² floor area"),
            ("furniture_double_bed",      1.0, True,  "Double bed frame + mattress"),
            ("lighting_recessed_led_pkg", 1.0, True,  "LED downlights"),
            ("lighting_pendant_feature",  1.0, False, "Optional bedside pendant (not required)"),
        ],
    ),

    # 3 ─ Studio Living
    (
        dict(
            code="pkg_studio_living",
            name="Studio Living Package",
            customer_name="Studio Living Space",
            customer_description=(
                "A complete studio living space: LVT or engineered timber flooring, "
                "white painted walls, double bed, kitchenette allowance "
                "and a recessed LED lighting package."
            ),
            internal_description="LVT floor + white paint + double bed + kitchenette + LED lighting.",
            package_category="studio_living",
            default_selected=False,
            customer_visible=True,
            is_active=True,
            sort_order=30,
        ),
        [
            ("int_paint_white_standard",  1.0, True,  "White matt throughout"),
            ("flooring_lvt_oak",          1.0, True,  "LVT per m² floor area"),
            ("furniture_double_bed",      1.0, True,  "Double bed frame + mattress"),
            ("kitchenette_base_1500",     1.0, False, "Kitchenette optional — deselect if not required"),
            ("lighting_recessed_led_pkg", 1.0, True,  "LED downlights throughout"),
            ("lighting_pendant_feature",  1.0, False, "Optional feature pendant"),
        ],
    ),

    # 4 ─ Basic Bathroom
    (
        dict(
            code="pkg_bathroom_basic",
            name="Basic Bathroom Package",
            customer_name="Basic Bathroom",
            customer_description=(
                "A functional bathroom: close-coupled WC, 600mm wall-hung vanity unit "
                "with basin, and a shower enclosure allowance."
            ),
            internal_description="Close-coupled WC + vanity + shower. Budget allowances.",
            package_category="bathroom",
            default_selected=False,
            customer_visible=True,
            is_active=True,
            sort_order=40,
        ),
        [
            ("toilet_close_coupled_std",      1.0, True,  "Close-coupled WC + soft-close seat"),
            ("vanity_unit_600_white",          1.0, True,  "600mm vanity unit with basin"),
            ("sanitary_shower_enclosure_std",  1.0, True,  "Shower enclosure + tray + mixer"),
        ],
    ),

    # 5 ─ Premium Bathroom
    (
        dict(
            code="pkg_bathroom_premium",
            name="Premium Bathroom Package",
            customer_name="Premium Bathroom",
            customer_description=(
                "Upgraded bathroom: wall-hung WC with concealed cistern, "
                "600mm vanity unit, walk-in shower enclosure and designer tap/mirror allowance."
            ),
            internal_description="Wall-hung WC + vanity + shower. Premium allowances.",
            package_category="bathroom",
            default_selected=False,
            customer_visible=True,
            is_active=True,
            sort_order=50,
        ),
        [
            ("toilet_wall_hung_std",           1.0, True,  "Wall-hung WC + concealed cistern"),
            ("vanity_unit_600_white",          1.0, True,  "600mm vanity unit with basin"),
            ("sanitary_shower_enclosure_std",  1.0, True,  "Walk-in shower enclosure + tray + mixer"),
        ],
    ),

    # 6 ─ Standard External Finish
    (
        dict(
            code="pkg_ext_finish_standard",
            name="Standard External Finish Package",
            customer_name="Standard Exterior — Cement Board Grey",
            customer_description=(
                "Anthracite grey fibre cement board cladding with standard external "
                "trim allowance. Low maintenance, modern appearance."
            ),
            internal_description="Cement board cladding (grey) + standard trim.",
            package_category="external_finish",
            default_selected=True,
            customer_visible=True,
            is_active=True,
            sort_order=60,
        ),
        [
            ("ext_cladding_cement_board_grey", 1.0, True, "Fibre cement, anthracite grey — per m² wall area"),
        ],
    ),

    # 7 ─ Premium External Finish
    (
        dict(
            code="pkg_ext_finish_premium_larch",
            name="Premium External Finish — Natural Larch",
            customer_name="Premium Exterior — Natural Larch",
            customer_description=(
                "Western red larch horizontal cladding, natural untreated finish. "
                "Weathers to a silver-grey over time. Premium timber aesthetic."
            ),
            internal_description="Natural larch cladding + premium trim allowance.",
            package_category="external_finish",
            default_selected=False,
            customer_visible=True,
            is_active=True,
            sort_order=70,
        ),
        [
            ("ext_cladding_larch_natural", 1.0, True, "Natural larch — per m² wall area"),
        ],
    ),

    # 8 ─ Premium External Finish — Charred Larch
    (
        dict(
            code="pkg_ext_finish_charred_larch",
            name="Premium External Finish — Charred Larch",
            customer_name="Premium Exterior — Charred Larch",
            customer_description=(
                "Shou sugi ban charred larch cladding. Deep black finish, "
                "low maintenance and striking. For a bold architectural statement."
            ),
            internal_description="Charred larch cladding + premium trim.",
            package_category="external_finish",
            default_selected=False,
            customer_visible=True,
            is_active=True,
            sort_order=75,
        ),
        [
            ("ext_cladding_larch_charred", 1.0, True, "Charred larch — per m² wall area"),
        ],
    ),

    # 9 ─ Solar PV-Ready
    (
        dict(
            code="pkg_solar_pv_ready",
            name="Solar PV-Ready Provision",
            customer_name="Solar-Ready Roof",
            customer_description=(
                "Spare conduit runs, marked fixing/ballast zones and structural note. "
                "PV panels not included. Upgrade to full PV package separately."
            ),
            internal_description="PV-ready conduit + zone marking.",
            package_category="solar",
            default_selected=False,
            customer_visible=True,
            is_active=True,
            sort_order=80,
        ),
        [
            ("solar_pv_ready_provision", 1.0, True, "PV-ready roof provision"),
        ],
    ),

    # 10 ─ Solar + Battery
    (
        dict(
            code="pkg_solar_battery_full",
            name="Solar PV + Battery Package",
            customer_name="Solar PV + Battery Storage",
            customer_description=(
                "4 kWp solar PV system with 10 kWh battery storage — provisional allowances only. "
                "Final design and installation by appointed specialist. "
                "Grid connection and certification not included."
            ),
            internal_description="4 kWp PV + 10 kWh battery + PV-ready provision. Specialist required.",
            package_category="solar",
            default_selected=False,
            customer_visible=True,
            is_active=True,
            sort_order=85,
        ),
        [
            ("solar_pv_ready_provision",    1.0, True, "PV-ready roof provision included"),
            ("solar_pv_4kw_provisional",    1.0, True, "4 kWp solar PV — provisional allowance"),
            ("solar_battery_storage_10kwh", 1.0, True, "10 kWh battery storage — provisional allowance"),
        ],
    ),

    # 11 ─ CCTV + Data
    (
        dict(
            code="pkg_cctv_data",
            name="CCTV + Data Package",
            customer_name="CCTV & Network",
            customer_description=(
                "CAT6 network prewire plus 4-camera IP CCTV system. "
                "PoE switch and NVR allowance included. Brand TBC."
            ),
            internal_description="CAT6 prewire + 4-camera IP CCTV.",
            package_category="cctv",
            default_selected=False,
            customer_visible=True,
            is_active=True,
            sort_order=90,
        ),
        [
            ("cctv_cat6_prewire",  1.0, True, "CAT6 home-runs + back-boxes"),
            ("cctv_4_camera_ip_pkg", 1.0, True, "4-camera IP CCTV + NVR allowance"),
        ],
    ),
]


try:
    inserted_pkg = inserted_items = skipped = 0

    for pkg_fields, line_items in PACKAGES:
        existing = db.query(FinishPackage).filter_by(code=pkg_fields["code"]).first()
        if existing:
            skipped += 1
            continue

        pkg = FinishPackage(**pkg_fields)
        db.add(pkg)
        db.flush()  # get pkg.id before commit

        for code, qty, required, notes in line_items:
            cat_id = ITEMS[code]
            pi = FinishPackageItem(
                finish_package_id=pkg.id,
                finish_catalogue_item_id=cat_id,
                quantity=qty,
                is_required=required,
                notes=notes or None,
            )
            db.add(pi)
            inserted_items += 1

        inserted_pkg += 1

    db.commit()
    print(f"Seeded {inserted_pkg} packages with {inserted_items} line items ({skipped} skipped).")
finally:
    db.close()
