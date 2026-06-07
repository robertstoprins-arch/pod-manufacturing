/**
 * Product Template Registry — frontend copy
 *
 * This mirrors backend/app/product_templates.py exactly.
 * The backend is the canonical source; this copy exists so the public
 * /get-quote form renders without an API round-trip on load.
 *
 * Visibility flags (on each field):
 *   customer_visible  — shown in the public /get-quote form
 *   internal_visible  — shown in the internal Manufacture Designer / quote panel
 *   pdf_visible       — included in the client quote PDF spec block
 *   portal_visible    — shown in the client portal spec summary
 *
 * Fields marked customer_visible: false are internal-only (e.g. roof pitch,
 * eaves height alias). GetQuote filters these out automatically via
 * stepFields(..., { visibleTo: 'customer_visible' }).
 *
 * Adding a new template:
 *   1. Define the template object below (same schema as OFFICE_POD).
 *   2. Add it to PRODUCT_TEMPLATES.
 *   3. Add the matching definition to backend/app/product_templates.py.
 *   4. Set status: 'active' on both sides before publishing.
 */

// ---------------------------------------------------------------------------
// Office Pod / Garden Pod
// ---------------------------------------------------------------------------

export const OFFICE_POD = {
  id: 'office_pod',
  name: 'Office Pod / Garden Pod',
  description: 'Insulated acoustic workspace, meeting pod, or garden room.',
  version: '2.1.0',
  status: 'active',

  steps: [
    { id: 'contact',    title: 'Your Contact Details',          nav_label: 'Contact'    },
    { id: 'product',    title: 'Pod Type',                      nav_label: 'Pod Type'   },
    { id: 'dimensions', title: 'Dimensions',                    nav_label: 'Dimensions' },
    { id: 'openings',   title: 'Doors, Windows & Rooflights',   nav_label: 'Openings'   },
    { id: 'finishes',   title: 'Finishes',                      nav_label: 'Finishes'   },
    { id: 'services',   title: 'Heating, Ventilation & Electrical', nav_label: 'Services' },
    { id: 'foundation', title: 'Foundation & Base',             nav_label: 'Foundation' },
    { id: 'delivery',   title: 'Delivery & Installation',       nav_label: 'Delivery'   },
    { id: 'review',     title: 'Review & Submit',               nav_label: 'Review'     },
  ],

  fields: [
    // ── Contact ─────────────────────────────────────────────────────────
    {
      key: 'first_name', label: 'First name', customer_label: 'First name',
      type: 'text', step: 'contact', required: true,
      customer_visible: true, internal_visible: false, pdf_visible: false, portal_visible: false,
    },
    {
      key: 'last_name', label: 'Last name', customer_label: 'Last name',
      type: 'text', step: 'contact', required: true,
      customer_visible: true, internal_visible: false, pdf_visible: false, portal_visible: false,
    },
    {
      key: 'email', label: 'Email address', customer_label: 'Email address',
      type: 'email', step: 'contact', required: true,
      customer_visible: true, internal_visible: false, pdf_visible: false, portal_visible: false,
    },
    {
      key: 'phone', label: 'Phone', customer_label: 'Phone',
      type: 'tel', step: 'contact', required: false,
      customer_visible: true, internal_visible: false, pdf_visible: false, portal_visible: false,
    },
    {
      key: 'company_name', label: 'Company name', customer_label: 'Company name',
      type: 'text', step: 'contact', required: false,
      customer_visible: true, internal_visible: false, pdf_visible: false, portal_visible: false,
    },

    // ── Product ──────────────────────────────────────────────────────────
    {
      key: 'pod_type',
      label: 'Pod type',
      customer_label: 'What type of pod do you need?',
      type: 'select_card',
      step: 'product',
      required: true,
      options: [
        { value: 'office', label: 'Office Pod',  description: 'Acoustic workspace or meeting pod' },
        { value: 'garden', label: 'Garden Pod',  description: 'Insulated garden room or studio'   },
        { value: 'custom', label: 'Custom',      description: 'Something else — describe in notes' },
      ],
      pricing_variable: 'product_type',
      bom_variable: 'pod_type',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },
    {
      key: 'quantity',
      label: 'Quantity',
      customer_label: 'How many pods do you need?',
      type: 'number',
      step: 'product',
      required: true,
      default: 1,
      validation: { min: 1, max: 100 },
      pricing_variable: 'quantity',
      bom_variable: 'quantity',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },

    // ── Dimensions ───────────────────────────────────────────────────────
    {
      key: 'width_m',
      label: 'Width (m)',
      customer_label: 'Width (m)',
      type: 'number',
      step: 'dimensions',
      required: false,
      placeholder: 'e.g. 3.5',
      validation: { min: 1.0, max: 10.0, step: 0.1 },
      pricing_variable: 'width_m',
      bom_variable: 'width',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },
    {
      key: 'length_m',
      label: 'Length (m)',
      customer_label: 'Length (m)',
      type: 'number',
      step: 'dimensions',
      required: false,
      placeholder: 'e.g. 5.0',
      validation: { min: 1.0, max: 15.0, step: 0.1 },
      pricing_variable: 'length_m',
      bom_variable: 'length',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },
    {
      key: 'height_m',
      label: 'Height (m)',
      customer_label: 'Internal height (m)',
      type: 'number',
      step: 'dimensions',
      required: false,
      placeholder: 'e.g. 2.5',
      validation: { min: 2.0, max: 4.5, step: 0.1 },
      pricing_variable: 'height_m',
      bom_variable: 'height',
      // In the internal Manufacture Designer this maps to wall_height_m (eaves height).
      // For customer-facing purposes these are treated as equivalent.
      internal_designer_key: 'wall_height_m',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },
    // Internal-only: roof geometry used by the Manufacture Designer and drawing engine.
    // Not shown on the public form (customer_visible: false).
    {
      key: 'roof_type',
      label: 'Roof type',
      customer_label: 'Roof type',
      type: 'select_tag',
      step: 'dimensions',
      required: false,
      default: 'duo_pitch',
      options: [
        { value: 'flat',      label: 'Flat'       },
        { value: 'mono_pitch', label: 'Mono Pitch' },
        { value: 'duo_pitch',  label: 'Duo Pitch'  },
      ],
      bom_variable: 'roof_type',
      customer_visible: false, internal_visible: true, pdf_visible: false, portal_visible: false,
    },
    {
      key: 'roof_pitch_deg',
      label: 'Roof pitch (°)',
      customer_label: 'Roof pitch (°)',
      type: 'number',
      step: 'dimensions',
      required: false,
      default: 15,
      placeholder: 'e.g. 15',
      validation: { min: 0, max: 89, step: 1 },
      bom_variable: 'roof_pitch_deg',
      customer_visible: false, internal_visible: true, pdf_visible: false, portal_visible: false,
    },

    // ── Openings ─────────────────────────────────────────────────────────
    {
      key: 'door_count',
      label: 'Number of doors',
      customer_label: 'How many external doors?',
      type: 'number',
      step: 'openings',
      required: false,
      default: 1,
      validation: { min: 0, max: 10 },
      bom_variable: 'door_count',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },
    {
      key: 'door_type',
      label: 'Door type',
      customer_label: 'Door style',
      type: 'select_tag',
      step: 'openings',
      required: false,
      options: [
        { value: 'single',   label: 'Single Door' },
        { value: 'double',   label: 'Double / French Doors' },
        { value: 'sliding',  label: 'Sliding Door' },
        { value: 'bi_fold',  label: 'Bi-fold Door' },
      ],
      bom_variable: 'door_type',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },
    {
      key: 'window_count',
      label: 'Number of windows',
      customer_label: 'How many windows?',
      type: 'number',
      step: 'openings',
      required: false,
      default: 2,
      validation: { min: 0, max: 20 },
      bom_variable: 'window_count',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },
    {
      key: 'window_type',
      label: 'Window type',
      customer_label: 'Window style',
      type: 'select_tag',
      step: 'openings',
      required: false,
      options: [
        { value: 'fixed',     label: 'Fixed' },
        { value: 'casement',  label: 'Casement / Opening' },
        { value: 'tilt_turn', label: 'Tilt & Turn' },
      ],
      bom_variable: 'window_type',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },
    {
      key: 'rooflight_count',
      label: 'Rooflights',
      customer_label: 'Rooflights / skylights',
      type: 'number',
      step: 'openings',
      required: false,
      default: 0,
      validation: { min: 0, max: 10 },
      bom_variable: 'rooflight_count',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },

    // ── Finishes ─────────────────────────────────────────────────────────
    {
      key: 'external_finish',
      label: 'External finish',
      customer_label: 'External cladding / finish',
      type: 'select_card',
      step: 'finishes',
      required: false,
      options: [
        { value: 'timber_clad',      label: 'Timber Cladding',    description: 'Natural or treated timber boards' },
        { value: 'composite',        label: 'Composite Panel',    description: 'Low-maintenance fibre cement or composite' },
        { value: 'brick_slip',       label: 'Brick Slip',         description: 'Traditional brick-effect facing' },
        { value: 'render',           label: 'Render',             description: 'Smooth or textured silicone render' },
        { value: 'corrugated_metal', label: 'Corrugated Metal',   description: 'Galvanised or powder-coated steel sheet' },
      ],
      pricing_variable: 'external_finish',
      bom_variable: 'external_finish',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },
    {
      key: 'internal_finish_package',
      label: 'Internal finish',
      customer_label: 'Internal finish package',
      type: 'select_card',
      step: 'finishes',
      required: false,
      options: [
        { value: 'basic',    label: 'Basic',    description: 'Painted MDF lining panels' },
        { value: 'standard', label: 'Standard', description: 'Plasterboard + emulsion paint' },
        { value: 'premium',  label: 'Premium',  description: 'Plasterboard, coving, and feature wall finishes' },
      ],
      pricing_variable: 'internal_finish',
      bom_variable: 'internal_finish_package',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },

    // ── Services ─────────────────────────────────────────────────────────
    {
      key: 'heating_option',
      label: 'Heating',
      customer_label: 'Heating',
      type: 'select_tag',
      step: 'services',
      required: false,
      options: [
        { value: 'none',           label: 'No heating' },
        { value: 'electric_panel', label: 'Electric Panel Heaters' },
        { value: 'underfloor',     label: 'Underfloor Heating' },
        { value: 'air_source',     label: 'Air Source Heat Pump' },
      ],
      pricing_variable: 'heating_option',
      bom_variable: 'heating_option',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },
    {
      key: 'ventilation_option',
      label: 'Ventilation',
      customer_label: 'Ventilation',
      type: 'select_tag',
      step: 'services',
      required: false,
      options: [
        { value: 'natural', label: 'Natural Ventilation' },
        { value: 'mvhr',    label: 'MVHR Unit' },
        { value: 'louvres', label: 'Louvre Panels' },
      ],
      pricing_variable: 'ventilation_option',
      bom_variable: 'ventilation_option',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },
    {
      key: 'electrical_package',
      label: 'Electrical package',
      customer_label: 'Electrical package',
      type: 'select_tag',
      step: 'services',
      required: false,
      options: [
        { value: 'basic',    label: 'Basic (sockets + lighting)' },
        { value: 'standard', label: 'Standard (sockets, lighting, data)' },
        { value: 'full',     label: 'Full (sockets, lighting, data, consumer unit)' },
      ],
      pricing_variable: 'electrical_package',
      bom_variable: 'electrical_package',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },

    // ── Foundation ───────────────────────────────────────────────────────
    {
      key: 'foundation_option',
      label: 'Foundation type',
      customer_label: 'Foundation / base type',
      type: 'select_card',
      step: 'foundation',
      required: false,
      options: [
        { value: 'groundworks',   label: 'Concrete Pad',        description: 'Traditional groundworks and concrete slab' },
        { value: 'screw_pile',    label: 'Screw Pile',          description: 'Minimal excavation, suitable for most ground conditions' },
        { value: 'pad_stone',     label: 'Pad Stone / Timber Frame', description: 'Raised timber frame on pad stones' },
        { value: 'existing_slab', label: 'Existing Slab',       description: 'Pod placed on an existing concrete slab' },
      ],
      pricing_variable: 'foundation_option',
      bom_variable: 'foundation_option',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },

    // ── Delivery ─────────────────────────────────────────────────────────
    {
      key: 'delivery_install_option',
      label: 'Delivery & installation',
      customer_label: 'Delivery & installation',
      type: 'select_card',
      step: 'delivery',
      required: false,
      options: [
        { value: 'supply_only',    label: 'Supply Only',     description: 'Pod delivered flat-pack or modular; customer installs' },
        { value: 'supply_install', label: 'Supply & Install', description: 'We deliver and install the pod on your prepared base' },
        { value: 'turnkey',        label: 'Turnkey',         description: 'Full package: supply, install, groundworks, and connections' },
      ],
      pricing_variable: 'delivery_option',
      bom_variable: 'delivery_install_option',
      customer_visible: true, internal_visible: true, pdf_visible: true, portal_visible: true,
    },

    // ── Review ───────────────────────────────────────────────────────────
    {
      key: 'location',
      label: 'Location',
      customer_label: 'Project location (City / Country)',
      type: 'text',
      step: 'review',
      required: false,
      placeholder: 'e.g. Dublin, Ireland',
      customer_visible: true, internal_visible: true, pdf_visible: false, portal_visible: false,
    },
    {
      key: 'intended_use',
      label: 'Intended use',
      customer_label: 'Intended use',
      type: 'select_tag',
      step: 'review',
      required: false,
      options: [
        { value: 'hotel',       label: 'Hotel / Hospitality' },
        { value: 'residential', label: 'Residential'         },
        { value: 'student',     label: 'Student Housing'     },
        { value: 'healthcare',  label: 'Healthcare'          },
        { value: 'office',      label: 'Office / Commercial' },
        { value: 'other',       label: 'Other'               },
      ],
      customer_visible: true, internal_visible: true, pdf_visible: false, portal_visible: false,
    },
    {
      key: 'timeline',
      label: 'Timeline',
      customer_label: 'When do you need it?',
      type: 'select_tag',
      step: 'review',
      required: false,
      options: [
        { value: 'asap',     label: 'As soon as possible' },
        { value: '3months',  label: 'Within 3 months'     },
        { value: '6months',  label: 'Within 6 months'     },
        { value: '12months', label: 'Within 12 months'    },
      ],
      pricing_variable: 'lead_time_preference',
      customer_visible: true, internal_visible: true, pdf_visible: false, portal_visible: false,
    },
    {
      key: 'notes',
      label: 'Notes',
      customer_label: 'Notes or special requirements (optional)',
      type: 'textarea',
      step: 'review',
      required: false,
      placeholder: 'Access constraints, site conditions, anything else we should know…',
      customer_visible: true, internal_visible: true, pdf_visible: false, portal_visible: false,
    },
  ],

  constraints: {
    min_width_m:  1.8,
    max_width_m:  8.0,
    min_length_m: 1.8,
    max_length_m: 12.0,
    notes: 'Dimensions outside these ranges require a custom engineering assessment.',
  },
}

// ---------------------------------------------------------------------------
// Registry
// ---------------------------------------------------------------------------

export const PRODUCT_TEMPLATES = {
  office_pod: OFFICE_POD,
}

/** Returns the first active template (used as the default for /get-quote). */
export function getDefaultTemplate() {
  return Object.values(PRODUCT_TEMPLATES).find(t => t.status === 'active') ?? null
}

/** Returns a template by id, or null. */
export function getTemplate(id) {
  return PRODUCT_TEMPLATES[id] ?? null
}

/**
 * Returns fields for a step.
 * Pass visibleTo: 'customer_visible' | 'internal_visible' | 'pdf_visible' | 'portal_visible'
 * to filter by visibility flag. Omit for all fields in the step.
 */
export function stepFields(template, stepId, { visibleTo } = {}) {
  return template.fields.filter(f => {
    if (f.step !== stepId) return false
    if (visibleTo && f[visibleTo] === false) return false
    return true
  })
}
