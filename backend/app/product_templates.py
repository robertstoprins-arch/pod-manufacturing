"""
Product Template Registry
=========================
Canonical definition of all product questionnaire templates for the
/get-quote flow and future agentic onboarding.

Each template defines:
  - The steps shown in the quote form
  - Every customer-facing field (type, options, validation, labels)
  - Internal variable mappings to the pricing engine and BOM
  - Indicative pricing estimates for early-stage ballparks

Adding a new manufacturer product template:
  1. Define a new dict in this file following the OFFICE_POD structure.
  2. Add it to TEMPLATES.
  3. The /enquiry/templates endpoints will serve it automatically.
  4. Build a matching frontend entry in src/config/productTemplates.js.

Future agentic onboarding:
  The onboarding agent reads a manufacturer's survey/files and produces
  a draft template in this exact schema. A reviewer agent checks it.
  A human approves it before it is added to TEMPLATES and activated.
  See docs/agent/agentic_onboarding_architecture.md for the full flow.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Office Pod / Garden Pod — first active template
# ---------------------------------------------------------------------------

OFFICE_POD: dict = {
    "id": "office_pod",
    "name": "Office Pod / Garden Pod",
    "description": "Insulated acoustic workspace, meeting pod, or garden room.",
    "version": "2.0.0",
    "status": "active",   # active | draft | archived

    # Steps shown in the multi-step form.
    # The 'nav_label' is the short text shown in the progress bar.
    "steps": [
        {"id": "contact",    "title": "Your Contact Details",          "nav_label": "Contact"},
        {"id": "product",    "title": "Pod Type",                      "nav_label": "Pod Type"},
        {"id": "dimensions", "title": "Dimensions",                    "nav_label": "Dimensions"},
        {"id": "openings",   "title": "Doors, Windows & Rooflights",   "nav_label": "Openings"},
        {"id": "finishes",   "title": "Finishes",                      "nav_label": "Finishes"},
        {"id": "services",   "title": "Heating, Ventilation & Electrical", "nav_label": "Services"},
        {"id": "foundation", "title": "Foundation & Base",             "nav_label": "Foundation"},
        {"id": "delivery",   "title": "Delivery & Installation",       "nav_label": "Delivery"},
        {"id": "review",     "title": "Review & Submit",               "nav_label": "Review"},
    ],

    # All fields in order.
    # key          — internal variable name (used in answers JSON and BOM mapping)
    # label        — short internal label
    # customer_label — longer customer-facing prompt shown above the field
    # type         — text | email | tel | number | select_card | select_tag | textarea
    # step         — which step id this field belongs to
    # required     — whether the field must have a value before advancing
    # default      — initial value (None = empty)
    # placeholder  — input hint text
    # options      — list of {value, label, description?} for select types
    # validation   — {min?, max?, step?} for number fields
    # pricing_variable — name in the pricing engine this answer maps to
    # bom_variable     — name in the BOM engine this answer maps to
    "fields": [

        # ── Step 1: Contact ──────────────────────────────────────────────
        {
            "key": "first_name",
            "label": "First name",
            "customer_label": "First name",
            "type": "text",
            "step": "contact",
            "required": True,
        },
        {
            "key": "last_name",
            "label": "Last name",
            "customer_label": "Last name",
            "type": "text",
            "step": "contact",
            "required": True,
        },
        {
            "key": "email",
            "label": "Email address",
            "customer_label": "Email address",
            "type": "email",
            "step": "contact",
            "required": True,
        },
        {
            "key": "phone",
            "label": "Phone",
            "customer_label": "Phone",
            "type": "tel",
            "step": "contact",
            "required": False,
        },
        {
            "key": "company_name",
            "label": "Company name",
            "customer_label": "Company name",
            "type": "text",
            "step": "contact",
            "required": False,
        },

        # ── Step 2: Product ───────────────────────────────────────────────
        {
            "key": "pod_type",
            "label": "Pod type",
            "customer_label": "What type of pod do you need?",
            "type": "select_card",
            "step": "product",
            "required": True,
            "options": [
                {"value": "office", "label": "Office Pod",
                 "description": "Acoustic workspace or meeting pod"},
                {"value": "garden", "label": "Garden Pod",
                 "description": "Insulated garden room or studio"},
                {"value": "custom", "label": "Custom",
                 "description": "Something else — describe in notes"},
            ],
            "pricing_variable": "product_type",
            "bom_variable": "pod_type",
        },
        {
            "key": "quantity",
            "label": "Quantity",
            "customer_label": "How many pods do you need?",
            "type": "number",
            "step": "product",
            "required": True,
            "default": 1,
            "validation": {"min": 1, "max": 100},
            "pricing_variable": "quantity",
            "bom_variable": "quantity",
        },

        # ── Step 3: Dimensions ────────────────────────────────────────────
        {
            "key": "width_m",
            "label": "Width (m)",
            "customer_label": "Width (m)",
            "type": "number",
            "step": "dimensions",
            "required": False,
            "placeholder": "e.g. 3.5",
            "validation": {"min": 1.0, "max": 10.0, "step": 0.1},
            "pricing_variable": "width_m",
            "bom_variable": "width",
        },
        {
            "key": "length_m",
            "label": "Length (m)",
            "customer_label": "Length (m)",
            "type": "number",
            "step": "dimensions",
            "required": False,
            "placeholder": "e.g. 5.0",
            "validation": {"min": 1.0, "max": 15.0, "step": 0.1},
            "pricing_variable": "length_m",
            "bom_variable": "length",
        },
        {
            "key": "height_m",
            "label": "Height (m)",
            "customer_label": "Internal height (m)",
            "type": "number",
            "step": "dimensions",
            "required": False,
            "placeholder": "e.g. 2.5",
            "validation": {"min": 2.0, "max": 4.5, "step": 0.1},
            "pricing_variable": "height_m",
            "bom_variable": "height",
        },

        # ── Step 4: Openings ──────────────────────────────────────────────
        {
            "key": "door_count",
            "label": "Number of doors",
            "customer_label": "How many external doors?",
            "type": "number",
            "step": "openings",
            "required": False,
            "default": 1,
            "validation": {"min": 0, "max": 10},
            "bom_variable": "door_count",
        },
        {
            "key": "door_type",
            "label": "Door type",
            "customer_label": "Door style",
            "type": "select_tag",
            "step": "openings",
            "required": False,
            "options": [
                {"value": "single",   "label": "Single Door"},
                {"value": "double",   "label": "Double / French Doors"},
                {"value": "sliding",  "label": "Sliding Door"},
                {"value": "bi_fold",  "label": "Bi-fold Door"},
            ],
            "bom_variable": "door_type",
        },
        {
            "key": "window_count",
            "label": "Number of windows",
            "customer_label": "How many windows?",
            "type": "number",
            "step": "openings",
            "required": False,
            "default": 2,
            "validation": {"min": 0, "max": 20},
            "bom_variable": "window_count",
        },
        {
            "key": "window_type",
            "label": "Window type",
            "customer_label": "Window style",
            "type": "select_tag",
            "step": "openings",
            "required": False,
            "options": [
                {"value": "fixed",     "label": "Fixed"},
                {"value": "casement",  "label": "Casement / Opening"},
                {"value": "tilt_turn", "label": "Tilt & Turn"},
            ],
            "bom_variable": "window_type",
        },
        {
            "key": "rooflight_count",
            "label": "Number of rooflights",
            "customer_label": "Rooflights / skylights",
            "type": "number",
            "step": "openings",
            "required": False,
            "default": 0,
            "validation": {"min": 0, "max": 10},
            "bom_variable": "rooflight_count",
        },

        # ── Step 5: Finishes ──────────────────────────────────────────────
        {
            "key": "external_finish",
            "label": "External finish",
            "customer_label": "External cladding / finish",
            "type": "select_card",
            "step": "finishes",
            "required": False,
            "options": [
                {"value": "timber_clad",      "label": "Timber Cladding",
                 "description": "Natural or treated timber boards"},
                {"value": "composite",        "label": "Composite Panel",
                 "description": "Low-maintenance fibre cement or composite"},
                {"value": "brick_slip",       "label": "Brick Slip",
                 "description": "Traditional brick-effect facing"},
                {"value": "render",           "label": "Render",
                 "description": "Smooth or textured silicone render"},
                {"value": "corrugated_metal", "label": "Corrugated Metal",
                 "description": "Galvanised or powder-coated steel sheet"},
            ],
            "pricing_variable": "external_finish",
            "bom_variable": "external_finish",
        },
        {
            "key": "internal_finish_package",
            "label": "Internal finish",
            "customer_label": "Internal finish package",
            "type": "select_card",
            "step": "finishes",
            "required": False,
            "options": [
                {"value": "basic",    "label": "Basic",
                 "description": "Painted MDF lining panels"},
                {"value": "standard", "label": "Standard",
                 "description": "Plasterboard + emulsion paint"},
                {"value": "premium",  "label": "Premium",
                 "description": "Plasterboard, coving, and feature wall finishes"},
            ],
            "pricing_variable": "internal_finish",
            "bom_variable": "internal_finish_package",
        },

        # ── Step 6: Services ──────────────────────────────────────────────
        {
            "key": "heating_option",
            "label": "Heating",
            "customer_label": "Heating",
            "type": "select_tag",
            "step": "services",
            "required": False,
            "options": [
                {"value": "none",           "label": "No heating"},
                {"value": "electric_panel", "label": "Electric Panel Heaters"},
                {"value": "underfloor",     "label": "Underfloor Heating"},
                {"value": "air_source",     "label": "Air Source Heat Pump"},
            ],
            "pricing_variable": "heating_option",
            "bom_variable": "heating_option",
        },
        {
            "key": "ventilation_option",
            "label": "Ventilation",
            "customer_label": "Ventilation",
            "type": "select_tag",
            "step": "services",
            "required": False,
            "options": [
                {"value": "natural", "label": "Natural Ventilation"},
                {"value": "mvhr",    "label": "MVHR Unit"},
                {"value": "louvres", "label": "Louvre Panels"},
            ],
            "pricing_variable": "ventilation_option",
            "bom_variable": "ventilation_option",
        },
        {
            "key": "electrical_package",
            "label": "Electrical package",
            "customer_label": "Electrical package",
            "type": "select_tag",
            "step": "services",
            "required": False,
            "options": [
                {"value": "basic",    "label": "Basic (sockets + lighting)"},
                {"value": "standard", "label": "Standard (sockets, lighting, data)"},
                {"value": "full",     "label": "Full (sockets, lighting, data, consumer unit)"},
            ],
            "pricing_variable": "electrical_package",
            "bom_variable": "electrical_package",
        },

        # ── Step 7: Foundation ────────────────────────────────────────────
        {
            "key": "foundation_option",
            "label": "Foundation type",
            "customer_label": "Foundation / base type",
            "type": "select_card",
            "step": "foundation",
            "required": False,
            "options": [
                {"value": "groundworks",    "label": "Concrete Pad",
                 "description": "Traditional groundworks and concrete slab"},
                {"value": "screw_pile",     "label": "Screw Pile",
                 "description": "Minimal excavation, suitable for most ground conditions"},
                {"value": "pad_stone",      "label": "Pad Stone / Timber Frame",
                 "description": "Raised timber frame on pad stones"},
                {"value": "existing_slab",  "label": "Existing Slab",
                 "description": "Pod placed on an existing concrete slab"},
            ],
            "pricing_variable": "foundation_option",
            "bom_variable": "foundation_option",
        },

        # ── Step 8: Delivery ──────────────────────────────────────────────
        {
            "key": "delivery_install_option",
            "label": "Delivery & installation",
            "customer_label": "Delivery & installation",
            "type": "select_card",
            "step": "delivery",
            "required": False,
            "options": [
                {"value": "supply_only",    "label": "Supply Only",
                 "description": "Pod delivered flat-pack or modular; customer installs"},
                {"value": "supply_install", "label": "Supply & Install",
                 "description": "We deliver and install the pod on your prepared base"},
                {"value": "turnkey",        "label": "Turnkey",
                 "description": "Full package: supply, install, groundworks, and connections"},
            ],
            "pricing_variable": "delivery_option",
            "bom_variable": "delivery_install_option",
        },

        # ── Step 9: Review ────────────────────────────────────────────────
        {
            "key": "location",
            "label": "Location",
            "customer_label": "Project location (City / Country)",
            "type": "text",
            "step": "review",
            "required": False,
            "placeholder": "e.g. Dublin, Ireland",
        },
        {
            "key": "intended_use",
            "label": "Intended use",
            "customer_label": "Intended use",
            "type": "select_tag",
            "step": "review",
            "required": False,
            "options": [
                {"value": "hotel",       "label": "Hotel / Hospitality"},
                {"value": "residential", "label": "Residential"},
                {"value": "student",     "label": "Student Housing"},
                {"value": "healthcare",  "label": "Healthcare"},
                {"value": "office",      "label": "Office / Commercial"},
                {"value": "other",       "label": "Other"},
            ],
        },
        {
            "key": "timeline",
            "label": "Timeline",
            "customer_label": "When do you need it?",
            "type": "select_tag",
            "step": "review",
            "required": False,
            "options": [
                {"value": "asap",     "label": "As soon as possible"},
                {"value": "3months",  "label": "Within 3 months"},
                {"value": "6months",  "label": "Within 6 months"},
                {"value": "12months", "label": "Within 12 months"},
            ],
            "pricing_variable": "lead_time_preference",
        },
        {
            "key": "notes",
            "label": "Notes",
            "customer_label": "Notes or special requirements (optional)",
            "type": "textarea",
            "step": "review",
            "required": False,
            "placeholder": "Access constraints, site conditions, anything else we should know…",
        },
    ],

    # Product constraints — used for validation and displayed to customers.
    "constraints": {
        "min_width_m":  1.8,
        "max_width_m":  8.0,
        "min_length_m": 1.8,
        "max_length_m": 12.0,
        "notes": "Dimensions outside these ranges require a custom engineering assessment.",
    },

    # Indicative pricing rates used to compute a ballpark estimate from
    # questionnaire answers. Displayed to the customer as an estimate only.
    # All figures are EUR ex-VAT unless noted.
    "pricing_estimates": {
        "base_rate_per_m2_ex_vat": 1200,
        "vat_rate": 0.23,
        "addons": {
            # External finish — per m² of floor area (used as proxy for cladding area)
            "timber_clad":           {"per_m2": 150,  "flat": 0,    "label": "Timber Cladding"},
            "composite":             {"per_m2": 0,    "flat": 0,    "label": "Composite Panel"},
            "brick_slip":            {"per_m2": 200,  "flat": 0,    "label": "Brick Slip"},
            "render":                {"per_m2": 0,    "flat": 0,    "label": "Render"},
            "corrugated_metal":      {"per_m2": -50,  "flat": 0,    "label": "Corrugated Metal"},
            # Height premium — flat uplift when internal height exceeds threshold
            "height_premium":        {"threshold_m": 3.0, "flat": 500},
            # Internal finish — per m² uplift above basic (basic = base rate inclusive)
            "internal_standard":     {"per_m2": 55,   "flat": 0,    "label": "Standard Internal Finish"},
            "internal_premium":      {"per_m2": 130,  "flat": 0,    "label": "Premium Internal Finish"},
            # Openings — per unit allowances
            "door_single":           {"per_unit": 650,              "label": "Single Door"},
            "door_double":           {"per_unit": 1200,             "label": "Double / French Doors"},
            "door_sliding":          {"per_unit": 1400,             "label": "Sliding Door"},
            "door_bi_fold":          {"per_unit": 1600,             "label": "Bi-fold Door"},
            "door_default":          {"per_unit": 700,              "label": "Door (type TBC)"},
            "window_fixed":          {"per_unit": 380,              "label": "Fixed Window"},
            "window_casement":       {"per_unit": 520,              "label": "Casement Window"},
            "window_tilt_turn":      {"per_unit": 620,              "label": "Tilt & Turn Window"},
            "window_default":        {"per_unit": 420,              "label": "Window (type TBC)"},
            "rooflight_unit":        {"per_unit": 780,              "label": "Rooflight / Skylight"},
            # Heating
            "underfloor_heating":    {"per_m2": 80,   "flat": 0,    "label": "Underfloor Heating"},
            "air_source_heat_pump":  {"per_m2": 0,    "flat": 3000, "label": "Air Source Heat Pump"},
            # Ventilation
            "mvhr":                  {"per_m2": 0,    "flat": 1500, "label": "MVHR Ventilation Unit"},
            # Electrical
            "standard_electrical":   {"per_m2": 0,    "flat": 250,  "label": "Standard Electrical Package"},
            "full_electrical":        {"per_m2": 0,    "flat": 500,  "label": "Full Electrical Package"},
            # Foundation
            "foundation_groundworks":{"per_m2": 0,    "flat": 3500, "label": "Concrete Pad / Groundworks"},
            "foundation_pad_stone":  {"per_m2": 0,    "flat": 1200, "label": "Pad Stone / Timber Frame"},
            "screw_pile":            {"per_m2": 0,    "flat": 2500, "label": "Screw Pile Foundation"},
            # Delivery & install
            "supply_install":        {"per_m2": 0,    "flat": 2000, "label": "Supply & Install"},
            "turnkey":               {"per_m2": 0,    "flat": 5000, "label": "Turnkey Package"},
        },
        "disclaimer": (
            "This is an indicative estimate only. "
            "Final pricing depends on detailed specification review, "
            "site conditions, and material lead times."
        ),
    },

    # Explains how questionnaire answers feed into the pricing and BOM engines.
    "pricing_variable_notes": {
        "product_type":  "Selects the assembly set (wall/roof/floor build-ups) in the BOM engine.",
        "quantity":      "Multiplies all BOM line quantities and cost totals.",
        "width_m":       "Used to calculate wall and floor area (sqm) for material take-off.",
        "length_m":      "Used to calculate wall and floor area (sqm) for material take-off.",
        "height_m":      "Used to calculate wall area height and volume. Premium applies above 3.0m.",
        "external_finish": "Selects cladding build-up and adjusts sqm rate.",
        "internal_finish": "Selects internal lining assembly.",
        "heating_option":  "Adds heating system to MEP BOM.",
        "ventilation_option": "Adds ventilation assembly to MEP BOM.",
        "electrical_package": "Sets electrical containment and fitting allowances.",
        "foundation_option":  "Adds relevant groundworks BOM line.",
        "delivery_option":    "Adds delivery and installation cost line.",
        "lead_time_preference": "Informational only at quote stage.",
    },

    # Variables the future onboarding agent should try to extract.
    "onboarding_extraction_targets": [
        "pod_type options and descriptions",
        "size constraints (min/max dimensions)",
        "standard assembly build-ups (wall/floor/roof layers)",
        "material names, units, and standard estimated prices",
        "supplier name and contact details",
        "preferred supplier per material",
        "pricing rates (sqm labour, delivery, installation)",
        "standard allowances (MEP, furniture, foundations)",
        "customer-facing wording and disclaimers",
        "lead time constraints by pod type",
    ],
}


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, dict] = {
    "office_pod": OFFICE_POD,
}


def get_template(template_id: str) -> dict | None:
    return TEMPLATES.get(template_id)


def list_active_templates() -> list[dict]:
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "version": t["version"],
            "status": t["status"],
        }
        for t in TEMPLATES.values()
        if t.get("status") == "active"
    ]
