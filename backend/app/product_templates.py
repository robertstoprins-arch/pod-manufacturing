"""
Product Template Registry
=========================
Canonical definition of all product questionnaire templates for the
/get-quote flow and future agentic onboarding.

Each template defines:
  - The steps shown in the quote form
  - Every customer-facing field (type, options, validation, labels)
  - Internal variable mappings to the pricing engine and BOM

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
    "version": "1.0.0",
    "status": "active",   # active | draft | archived

    # Steps shown in the multi-step form.
    # The 'nav_label' is the short text shown in the progress bar.
    "steps": [
        {"id": "contact", "title": "Your Contact Details",  "nav_label": "Contact"},
        {"id": "product", "title": "Pod Configuration",     "nav_label": "Pod Type"},
        {"id": "project", "title": "Project Details",       "nav_label": "Project"},
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
            "customer_label": "Quantity",
            "type": "number",
            "step": "product",
            "required": True,
            "default": 1,
            "validation": {"min": 1, "max": 100},
            "pricing_variable": "quantity",
            "bom_variable": "quantity",
        },
        {
            "key": "size_option",
            "label": "Approximate size",
            "customer_label": "Approximate size (optional)",
            "type": "select_tag",
            "step": "product",
            "required": False,
            "options": [
                {"value": "small",  "label": "Small",  "description": "Under 6m²"},
                {"value": "medium", "label": "Medium", "description": "6–12m²"},
                {"value": "large",  "label": "Large",  "description": "Over 12m²"},
            ],
        },
        {
            "key": "width_m",
            "label": "Width (m)",
            "customer_label": "Width (m)",
            "type": "number",
            "step": "product",
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
            "step": "product",
            "required": False,
            "placeholder": "e.g. 5.0",
            "validation": {"min": 1.0, "max": 15.0, "step": 0.1},
            "pricing_variable": "length_m",
            "bom_variable": "length",
        },

        # ── Step 3: Project ───────────────────────────────────────────────
        {
            "key": "location",
            "label": "Location",
            "customer_label": "Project location (City / Country)",
            "type": "text",
            "step": "project",
            "required": False,
            "placeholder": "e.g. Dublin, Ireland",
        },
        {
            "key": "intended_use",
            "label": "Intended use",
            "customer_label": "Intended use",
            "type": "select_tag",
            "step": "project",
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
            "step": "project",
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
            "step": "project",
            "required": False,
            "placeholder": "Finishes, access constraints, site conditions, anything else we should know…",
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

    # Explains how questionnaire answers feed into the pricing and BOM engines.
    # This is documentation for the onboarding agent and developers.
    "pricing_variable_notes": {
        "product_type":  "Selects the assembly set (wall/roof/floor build-ups) in the BOM engine.",
        "quantity":      "Multiplies all BOM line quantities and cost totals.",
        "width_m":       "Used to calculate wall and floor area (sqm) for material take-off.",
        "length_m":      "Used to calculate wall and floor area (sqm) for material take-off.",
        "lead_time_preference": "Informational only at quote stage. May affect delivery pricing later.",
    },

    # Variables the future onboarding agent should try to extract and populate
    # from manufacturer-provided documents.
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
    # Add future templates here by key.
    # Example:
    #   "bathroom_pod": BATHROOM_POD,
    #   "wall_panelling": WALL_PANELLING,
    # Each is activated by setting status = "active".
    # Draft templates are excluded from the public listing.
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
