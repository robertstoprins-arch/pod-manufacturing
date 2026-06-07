/**
 * Product Template Registry — frontend copy
 *
 * This mirrors backend/app/product_templates.py exactly.
 * The backend is the canonical source; this copy exists so the public
 * /get-quote form renders without an API round-trip on load.
 *
 * Adding a new template:
 *   1. Define the template object below (same schema as OFFICE_POD).
 *   2. Add it to PRODUCT_TEMPLATES.
 *   3. Add the matching definition to backend/app/product_templates.py.
 *   4. Set status: 'active' on both sides before publishing.
 *
 * Future agentic onboarding:
 *   The onboarding agent produces a draft template via the backend API.
 *   After human approval, the frontend copy is generated from the approved
 *   backend schema and committed here. The form renders it automatically.
 *   See docs/agent/agentic_onboarding_architecture.md.
 */

// ---------------------------------------------------------------------------
// Office Pod / Garden Pod — first active template
// ---------------------------------------------------------------------------

export const OFFICE_POD = {
  id: 'office_pod',
  name: 'Office Pod / Garden Pod',
  description: 'Insulated acoustic workspace, meeting pod, or garden room.',
  version: '1.0.0',
  status: 'active',

  steps: [
    { id: 'contact', title: 'Your Contact Details', nav_label: 'Contact'  },
    { id: 'product', title: 'Pod Configuration',    nav_label: 'Pod Type' },
    { id: 'project', title: 'Project Details',      nav_label: 'Project'  },
  ],

  fields: [
    // ── Contact ─────────────────────────────────────────────────────────
    { key: 'first_name',   label: 'First name',    customer_label: 'First name',    type: 'text',  step: 'contact', required: true  },
    { key: 'last_name',    label: 'Last name',     customer_label: 'Last name',     type: 'text',  step: 'contact', required: true  },
    { key: 'email',        label: 'Email address', customer_label: 'Email address', type: 'email', step: 'contact', required: true  },
    { key: 'phone',        label: 'Phone',         customer_label: 'Phone',         type: 'tel',   step: 'contact', required: false },
    { key: 'company_name', label: 'Company name',  customer_label: 'Company name',  type: 'text',  step: 'contact', required: false },

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
    },
    {
      key: 'quantity',
      label: 'Quantity',
      customer_label: 'Quantity',
      type: 'number',
      step: 'product',
      required: true,
      default: 1,
      validation: { min: 1, max: 100 },
      pricing_variable: 'quantity',
      bom_variable: 'quantity',
    },
    {
      key: 'size_option',
      label: 'Approximate size',
      customer_label: 'Approximate size (optional)',
      type: 'select_tag',
      step: 'product',
      required: false,
      options: [
        { value: 'small',  label: 'Small',  description: 'Under 6m²' },
        { value: 'medium', label: 'Medium', description: '6–12m²'    },
        { value: 'large',  label: 'Large',  description: 'Over 12m²' },
      ],
    },
    {
      key: 'width_m',
      label: 'Width (m)',
      customer_label: 'Width (m)',
      type: 'number',
      step: 'product',
      required: false,
      placeholder: 'e.g. 3.5',
      validation: { min: 1.0, max: 10.0, step: 0.1 },
      pricing_variable: 'width_m',
      bom_variable: 'width',
    },
    {
      key: 'length_m',
      label: 'Length (m)',
      customer_label: 'Length (m)',
      type: 'number',
      step: 'product',
      required: false,
      placeholder: 'e.g. 5.0',
      validation: { min: 1.0, max: 15.0, step: 0.1 },
      pricing_variable: 'length_m',
      bom_variable: 'length',
    },

    // ── Project ──────────────────────────────────────────────────────────
    {
      key: 'location',
      label: 'Location',
      customer_label: 'Project location (City / Country)',
      type: 'text',
      step: 'project',
      required: false,
      placeholder: 'e.g. Dublin, Ireland',
    },
    {
      key: 'intended_use',
      label: 'Intended use',
      customer_label: 'Intended use',
      type: 'select_tag',
      step: 'project',
      required: false,
      options: [
        { value: 'hotel',       label: 'Hotel / Hospitality' },
        { value: 'residential', label: 'Residential'         },
        { value: 'student',     label: 'Student Housing'     },
        { value: 'healthcare',  label: 'Healthcare'          },
        { value: 'office',      label: 'Office / Commercial' },
        { value: 'other',       label: 'Other'               },
      ],
    },
    {
      key: 'timeline',
      label: 'Timeline',
      customer_label: 'When do you need it?',
      type: 'select_tag',
      step: 'project',
      required: false,
      options: [
        { value: 'asap',     label: 'As soon as possible' },
        { value: '3months',  label: 'Within 3 months'     },
        { value: '6months',  label: 'Within 6 months'     },
        { value: '12months', label: 'Within 12 months'    },
      ],
      pricing_variable: 'lead_time_preference',
    },
    {
      key: 'notes',
      label: 'Notes',
      customer_label: 'Notes or special requirements (optional)',
      type: 'textarea',
      step: 'project',
      required: false,
      placeholder: 'Finishes, access constraints, site conditions, anything else we should know…',
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
  // Add future templates here:
  //   bathroom_pod: BATHROOM_POD,
  //   wall_panelling: WALL_PANELLING,
}

/** Returns the first active template (used as the default for /get-quote). */
export function getDefaultTemplate() {
  return Object.values(PRODUCT_TEMPLATES).find(t => t.status === 'active') ?? null
}

/** Returns a template by id, or null. */
export function getTemplate(id) {
  return PRODUCT_TEMPLATES[id] ?? null
}

/** Returns all fields for a given step id. */
export function stepFields(template, stepId) {
  return template.fields.filter(f => f.step === stepId)
}
