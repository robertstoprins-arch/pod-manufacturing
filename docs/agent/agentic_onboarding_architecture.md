# Agentic Manufacturer Onboarding — Architecture

**Status:** Design document. The onboarding agent system is not built yet.
This document describes the target architecture so the current code is shaped
correctly to receive it.

**Last updated:** 2026-06-07

---

## Why This Exists

Manufacture Suite is built as a reusable AI-first manufacturing operating system,
not a one-off pod configurator. Every product and workflow is driven by a
ProductTemplate schema. Today the schema is hand-written for Office Pod / Garden Pod.

In the future, a manufacturer should be able to onboard by providing their own
documents and letting an agent extract and map the configuration — without any
developer work.

---

## Target Onboarding Flow

```
Manufacturer provides inputs
  ├── Onboarding survey (web form)
  ├── Uploaded files: spreadsheets, price lists, BOM schedules
  ├── Product catalogue (PDF or URL)
  ├── Supplier lists
  ├── Website pages
  ├── Historical quotes (PDF or CSV)
  └── Internal process documents

↓

Extraction Agent
  ├── Reads all provided inputs
  ├── Extracts business variables (see extraction targets below)
  ├── Maps variables into the ProductTemplate schema
  ├── Marks low-confidence mappings for review
  └── Produces draft_template JSON

↓

Reviewer Agent
  ├── Checks draft_template for completeness
  ├── Flags missing required fields
  ├── Checks for conflicting rules or impossible constraints
  ├── Checks that customer-facing wording is appropriate
  └── Produces review_report with pass / flag / fail per section

↓

Human Review (Roberts or authorised manufacturer admin)
  ├── Sees draft_template + review_report side by side
  ├── Can edit any field in the draft
  ├── Must explicitly approve each section marked as low-confidence
  └── Approves or rejects the full template

↓ (approved)

Template Activation
  ├── Template added to TEMPLATES registry (backend/app/product_templates.py)
  ├── Frontend copy committed to src/config/productTemplates.js
  ├── /get-quote flow auto-renders the new template
  ├── BOM engine receives the new build-up rules
  ├── Pricing engine receives the new rate rules
  └── Closed-loop workflow is live for the manufacturer
```

---

## What the Extraction Agent Must Map

### 1. Business Targets
- Target customer type (trade / end-user / both)
- Product categories the manufacturer offers
- Sales model (supply only / supply and install)
- Geographic region and delivery areas
- Preferred quote flow and approval steps

### 2. Product Variables
From catalogues, brochures, and price lists:
- Product names and descriptions
- Available dimensions (min/max width and length)
- Standard sizes if offered as fixed options
- Available options (finishes, glazing, rooflight, access)
- Add-ons and optional extras
- Installation options
- Delivery options

### 3. Constraints
From engineering specs and internal rules:
- Min/max dimension combinations
- Allowed and disallowed option combinations
- Dependency rules (e.g. wetroom finish requires tanking)
- Required engineering sign-offs above certain sizes
- Lead-time constraints by product type

### 4. Materials
From BOM schedules and price lists:
- Material names and descriptions
- Units (m², lm, each, kg)
- Standard estimated unit prices
- Waste factors
- Datasheet URLs
- DoP / certificate links
- Evidence category (verified / partial / provisional / missing)

### 5. Assemblies and Build-ups
From build-up schedules and specification documents:
- Wall, floor, roof, and wet wall build-up layers
- Layer order, thicknesses, and materials per layer
- Calculation methods (sqm, perimeter, each)
- Fixing and consumable rules
- U-value requirements

### 6. Pricing Rules
From price lists and quote templates:
- Sqm rates by product type
- Unit rates for options and extras
- Standard allowances (MEP rough-in, furniture, foundations)
- Markup rules and tier thresholds
- VAT / tax settings and currency
- Delivery pricing (zone-based or flat)
- Installation rates (days, sqm, or fixed)
- Labour rates
- Provisional sums

### 7. Suppliers
From supplier lists and purchase orders:
- Supplier names and categories
- Contact details (email, phone)
- Standard lead times
- Payment terms
- Price lists and effective dates
- Preferred supplier per material category

### 8. Workflow Rules
From internal process documents and SOPs:
- Quote approval steps (who approves what value threshold)
- RFQ rules (which suppliers receive which categories)
- Procurement triggers (auto-RFQ on acceptance, manual, etc.)
- Production readiness checks
- QA and handover requirements

### 9. Customer-Facing Content
From marketing materials and website:
- Quote questionnaire wording
- Product descriptions for customer portal
- Assumptions and exclusions statements
- Follow-up email templates
- Lead source fields

---

## Safety Rules for the Onboarding Agent

These rules are non-negotiable. The agent must follow them regardless of
confidence level.

| Rule | Reasoning |
|------|-----------|
| Agent may suggest mappings. | It does not have authority to activate them. |
| Agent may generate draft schemas. | Drafts are not deployed until human-approved. |
| Agent may classify materials, products, and suppliers. | Low-risk; easily corrected. |
| Agent must NOT activate a template without human approval. | Incorrect templates produce wrong quotes and wrong BOMs. |
| Low-confidence mappings must be marked `confidence: "low"` with a reason. | Human reviewer must explicitly resolve each one. |
| Pricing rules require explicit human approval before activation. | A wrong rate sends a wrong price to a customer. |
| Product constraints require explicit human approval. | A wrong dimension constraint produces undeliverable products. |
| Customer-facing wording requires explicit human approval before publishing. | Brand and legal risk. |
| Markup rules are never extracted or mapped automatically. | Markup is commercially sensitive. Manufacturer sets it manually. |

---

## Draft Template Schema

A draft produced by the onboarding agent follows the same ProductTemplate
schema (see `backend/app/product_templates.py`) with additional metadata fields:

```json
{
  "id": "manufacturer_slug__product_type",
  "name": "...",
  "status": "draft",
  "onboarding_metadata": {
    "manufacturer_id": "...",
    "extracted_at": "2026-06-07T...",
    "source_files": ["price_list.xlsx", "build_up_schedule.pdf"],
    "extractor_agent_version": "1.0.0",
    "reviewer_agent_version": "1.0.0",
    "review_report": {
      "overall": "needs_review",
      "sections": {
        "product_variables": "pass",
        "constraints": "flag",
        "materials": "pass",
        "pricing_rules": "flag",
        "customer_wording": "needs_review"
      }
    }
  },
  "fields": [
    {
      "key": "pod_type",
      "label": "...",
      "...",
      "extraction_confidence": "high",
      "extraction_source": "price_list.xlsx:Sheet1:A2-A8",
      "extraction_note": null
    },
    {
      "key": "width_m",
      "...",
      "extraction_confidence": "low",
      "extraction_source": "build_up_schedule.pdf:page3",
      "extraction_note": "Only found max width, min width assumed 1.8m. Please verify."
    }
  ]
}
```

---

## Current Implementation (as of 2026-06-07)

The template infrastructure is in place:

| File | Purpose |
|------|---------|
| `backend/app/product_templates.py` | Canonical template registry. Add new templates here. |
| `backend/app/api/enquiry.py` | Serves templates via API. Validates answers against template schema. Stores structured answers in `spec_snapshot`. |
| `src/config/productTemplates.js` | Frontend copy. Form renders from this. |
| `src/pages/GetQuote.jsx` | Template-driven multi-step questionnaire renderer. |

**Active templates:** `office_pod` (Office Pod / Garden Pod)

**Database:** `quotes.spec_snapshot` stores structured answers:
```json
{
  "product_template_id": "office_pod",
  "product_template_version": "1.0.0",
  "questionnaire_answers": {
    "pod_type": "office",
    "quantity": 2,
    "width_m": 3.5,
    "length_m": 5.0,
    "location": "Dublin, Ireland",
    "intended_use": "office",
    "timeline": "3months"
  },
  "contact": {
    "first_name": "...",
    "last_name": "...",
    "email": "..."
  }
}
```

**What is NOT yet built:**
- Onboarding survey UI
- File upload + parsing pipeline
- Extraction agent
- Reviewer agent
- Human approval UI for draft templates
- Multi-manufacturer isolation (all quotes currently go to the same workspace)

---

## Adding a Second Product Template Now (Manual Path)

Until the onboarding agent exists, adding a new product template requires:

1. Define the template dict in `backend/app/product_templates.py`
2. Add it to `TEMPLATES` with `status: "draft"` initially
3. Add a matching object to `src/config/productTemplates.js` and `PRODUCT_TEMPLATES`
4. Test the `/enquiry/templates/{id}` endpoint
5. Verify the form renders correctly at `/get-quote`
6. Set `status: "active"` on both sides
7. Update `getDefaultTemplate()` if needed (currently returns first active template)

The form handles multiple active templates by selecting the first active one.
A product-selector step (before contact) should be added when there are two
or more active templates.
