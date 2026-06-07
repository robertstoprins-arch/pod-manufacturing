/**
 * Public quote enquiry form.
 *
 * Renders a multi-step questionnaire driven by a ProductTemplate config.
 * The active template is loaded from src/config/productTemplates.js.
 *
 * To add a second product type:
 *   1. Define the template in productTemplates.js + backend product_templates.py.
 *   2. Set status: 'active' on the new template.
 *   3. If multiple templates are active, show a product-selector step before
 *      the contact step (not needed until there is more than one).
 *
 * Submitted answers are posted to POST /enquiry as:
 *   { first_name, last_name, email, phone, company_name,
 *     product_template_id, answers: { ...all product/project fields } }
 */

import { useState } from 'react'
import { getDefaultTemplate, stepFields } from '../config/productTemplates'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function publicFetch(path, opts = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

export default function GetQuote() {
  const template = getDefaultTemplate()

  // Build initial answers from field defaults
  const [answers, setAnswers] = useState(() => {
    const init = {}
    if (template) {
      template.fields.forEach(f => {
        init[f.key] = f.default !== undefined ? f.default : ''
      })
    }
    return init
  })

  const [stepIndex, setStepIndex] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  if (!template) {
    return (
      <Page>
        <Card>
          <p style={{ color: '#dc2626', textAlign: 'center', padding: 32 }}>
            No active product template found. Please contact us directly.
          </p>
        </Card>
      </Page>
    )
  }

  const set = (key, value) => setAnswers(a => ({ ...a, [key]: value }))
  const steps = template.steps
  const currentStep = steps[stepIndex]
  const currentFields = stepFields(template, currentStep.id)

  // Validate current step: all required fields in this step have a value
  const stepValid = currentFields
    .filter(f => f.required)
    .every(f => {
      const v = answers[f.key]
      return v !== '' && v !== null && v !== undefined
    })

  async function handleSubmit() {
    setSubmitting(true)
    setError(null)
    try {
      // Separate contact fields from product/project answers
      const contactFields = stepFields(template, 'contact').map(f => f.key)
      const productAnswers = {}
      Object.entries(answers).forEach(([k, v]) => {
        if (!contactFields.includes(k)) {
          // Coerce number fields
          const field = template.fields.find(f => f.key === k)
          if (field?.type === 'number' && v !== '' && v !== null) {
            productAnswers[k] = Number(v)
          } else {
            productAnswers[k] = v || null
          }
        }
      })

      const payload = {
        first_name:           answers.first_name,
        last_name:            answers.last_name,
        email:                answers.email,
        phone:                answers.phone        || null,
        company_name:         answers.company_name || null,
        product_template_id:  template.id,
        answers:              productAnswers,
      }

      const data = await publicFetch('/enquiry', {
        method: 'POST',
        body:   JSON.stringify(payload),
      })
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (result) {
    return (
      <Page>
        <Card>
          <div style={{ textAlign: 'center', padding: '32px 0' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>✓</div>
            <h2 style={{ margin: '0 0 8px', fontSize: 22, color: '#111827', fontWeight: 700 }}>
              Enquiry Received
            </h2>
            <p style={{ color: '#6b7280', fontSize: 14, margin: '0 0 24px' }}>
              {result.message}
            </p>
            <div style={s.refBox}>
              <div style={{ fontSize: 11, color: '#9ca3af', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>
                Your reference
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#111827', letterSpacing: 1 }}>
                {result.reference}
              </div>
            </div>
            <p style={{ color: '#9ca3af', fontSize: 12, marginTop: 24 }}>
              Questions? <a href="mailto:info@top-r.com" style={{ color: '#2563eb' }}>info@top-r.com</a>
            </p>
          </div>
        </Card>
      </Page>
    )
  }

  return (
    <Page>
      <Card>
        {/* Header */}
        <div style={s.header}>
          <div style={s.logo}>Top-R Solutions</div>
          <div>
            <h1 style={s.h1}>Get a Quote</h1>
            <p style={s.subtitle}>Tell us about your project and we'll get back to you within 24 hours.</p>
          </div>
        </div>

        {/* Progress bar */}
        <div style={s.progress}>
          {steps.map((step, i) => (
            <div key={step.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{
                ...s.stepDot,
                background: stepIndex >= i ? '#2563eb' : '#e5e7eb',
                color:      stepIndex >= i ? '#fff'    : '#9ca3af',
              }}>{i + 1}</div>
              <span style={{
                fontSize:   12,
                color:      stepIndex === i ? '#111827' : '#9ca3af',
                fontWeight: stepIndex === i ? 600 : 400,
              }}>
                {step.nav_label}
              </span>
              {i < steps.length - 1 && (
                <div style={{ flex: 1, height: 1, background: '#e5e7eb', minWidth: 20 }} />
              )}
            </div>
          ))}
        </div>

        {/* Step body */}
        <div style={s.stepBody}>
          <StepRenderer
            step={currentStep}
            fields={currentFields}
            answers={answers}
            set={set}
          />
        </div>

        {error && (
          <p style={{ color: '#dc2626', fontSize: 13, marginTop: 12 }}>{error}</p>
        )}

        {/* Navigation */}
        <div style={s.actions}>
          {stepIndex > 0 && (
            <button style={s.btnSecondary} onClick={() => setStepIndex(i => i - 1)}>
              ← Back
            </button>
          )}
          {stepIndex < steps.length - 1 ? (
            <button
              style={{ ...s.btn, opacity: stepValid ? 1 : 0.5 }}
              disabled={!stepValid}
              onClick={() => setStepIndex(i => i + 1)}
            >
              Next: {steps[stepIndex + 1].nav_label} →
            </button>
          ) : (
            <button
              style={{ ...s.btn, opacity: submitting ? 0.7 : 1 }}
              disabled={submitting}
              onClick={handleSubmit}
            >
              {submitting ? 'Sending…' : 'Submit Enquiry'}
            </button>
          )}
        </div>

        <div style={s.footer}>
          Top-R Solutions · <a href="mailto:info@top-r.com" style={{ color: '#2563eb' }}>info@top-r.com</a>
        </div>
      </Card>
    </Page>
  )
}

// ── Step renderer — dispatches each field to the right input component ───────

function StepRenderer({ step, fields, answers, set }) {
  // Group contact fields into pairs for 2-column layout
  if (step.id === 'contact') {
    return (
      <>
        <div style={s.sectionTitle}>{step.title}</div>
        <div style={s.row2}>
          <FieldInput field={fields.find(f => f.key === 'first_name')} answers={answers} set={set} />
          <FieldInput field={fields.find(f => f.key === 'last_name')}  answers={answers} set={set} />
        </div>
        <FieldInput field={fields.find(f => f.key === 'email')}        answers={answers} set={set} />
        <div style={{ ...s.row2, marginTop: 12 }}>
          <FieldInput field={fields.find(f => f.key === 'phone')}        answers={answers} set={set} />
          <FieldInput field={fields.find(f => f.key === 'company_name')} answers={answers} set={set} />
        </div>
      </>
    )
  }

  // All other steps: render fields in declaration order
  return (
    <>
      {fields.map(field => (
        <div key={field.key} style={{ marginBottom: 20 }}>
          <FieldInput field={field} answers={answers} set={set} />
        </div>
      ))}
    </>
  )
}

// ── Individual field renderer ─────────────────────────────────────────────────

function FieldInput({ field, answers, set }) {
  if (!field) return null
  const value = answers[field.key] ?? ''

  switch (field.type) {
    case 'select_card':
      return (
        <>
          <div style={s.sectionTitle}>{field.customer_label}</div>
          <div style={s.podGrid}>
            {field.options.map(opt => (
              <button
                key={opt.value}
                onClick={() => set(field.key, opt.value)}
                style={{
                  ...s.podCard,
                  borderColor: value === opt.value ? '#2563eb' : '#e5e7eb',
                  background:  value === opt.value ? '#eff6ff' : '#fff',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 14, color: value === opt.value ? '#1d4ed8' : '#111827' }}>
                  {opt.label}
                </div>
                {opt.description && (
                  <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>{opt.description}</div>
                )}
              </button>
            ))}
          </div>
        </>
      )

    case 'select_tag':
      return (
        <>
          <div style={s.sectionTitle}>{field.customer_label}</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {field.options.map(opt => (
              <button
                key={opt.value}
                onClick={() => set(field.key, value === opt.value ? '' : opt.value)}
                style={{
                  ...s.tagBtn,
                  borderColor: value === opt.value ? '#2563eb' : '#e5e7eb',
                  background:  value === opt.value ? '#eff6ff' : '#fff',
                  color:       value === opt.value ? '#1d4ed8' : '#374151',
                }}
              >
                {opt.label}{opt.description ? ` (${opt.description})` : ''}
              </button>
            ))}
          </div>
        </>
      )

    case 'textarea':
      return (
        <>
          <div style={s.sectionTitle}>{field.customer_label}</div>
          <textarea
            rows={4}
            value={value}
            onChange={e => set(field.key, e.target.value)}
            placeholder={field.placeholder || ''}
            style={s.textarea}
          />
        </>
      )

    case 'number': {
      const v = field.validation || {}
      // Special layout: width + length shown side by side
      if (field.key === 'length_m') return null  // rendered with width_m below
      if (field.key === 'width_m') {
        const lengthField = { key: 'length_m', customer_label: 'Length (m)', type: 'number',
          placeholder: 'e.g. 5.0', validation: { min: 1.0, max: 15.0, step: 0.1 } }
        return (
          <>
            <div style={s.sectionTitle}>Dimensions (optional)</div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <InlineInput
                label="Width (m)"
                type="number"
                value={answers.width_m ?? ''}
                placeholder={field.placeholder}
                min={field.validation?.min} max={field.validation?.max} step={field.validation?.step}
                onChange={v => set('width_m', v)}
                style={{ width: 110 }}
              />
              <span style={{ paddingTop: 18, color: '#9ca3af' }}>×</span>
              <InlineInput
                label="Length (m)"
                type="number"
                value={answers.length_m ?? ''}
                placeholder={lengthField.placeholder}
                min={lengthField.validation?.min} max={lengthField.validation?.max} step={lengthField.validation?.step}
                onChange={v => set('length_m', v)}
                style={{ width: 110 }}
              />
            </div>
          </>
        )
      }
      // Quantity (and any other standalone number field)
      return (
        <>
          <div style={s.sectionTitle}>{field.customer_label}</div>
          <input
            type="number"
            value={value}
            min={v.min} max={v.max} step={v.step || 1}
            placeholder={field.placeholder || ''}
            onChange={e => set(field.key, e.target.value)}
            style={{ ...s.input, width: 80 }}
          />
        </>
      )
    }

    default:
      return (
        <InlineInput
          label={`${field.customer_label}${field.required ? ' *' : ''}`}
          type={field.type}
          value={value}
          placeholder={field.placeholder || ''}
          onChange={v => set(field.key, v)}
        />
      )
  }
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Page({ children }) {
  return (
    <div style={{ minHeight: '100vh', background: '#f3f4f6', padding: '32px 16px', fontFamily: 'system-ui, sans-serif' }}>
      {children}
    </div>
  )
}

function Card({ children }) {
  return (
    <div style={{ maxWidth: 640, margin: '0 auto', background: '#fff', borderRadius: 12, padding: 32, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
      {children}
    </div>
  )
}

function InlineInput({ label, value, onChange, type = 'text', placeholder = '', min, max, step, style: extraStyle }) {
  return (
    <div style={{ flex: 1, minWidth: 120, ...extraStyle }}>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#374151', marginBottom: 4 }}>
        {label}
      </label>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        min={min} max={max} step={step}
        onChange={e => onChange(e.target.value)}
        style={s.input}
      />
    </div>
  )
}

// ── Styles ────────────────────────────────────────────────────────────────────

const s = {
  header:      { display: 'flex', alignItems: 'flex-start', gap: 20, paddingBottom: 20, borderBottom: '2px solid #e5e7eb', marginBottom: 24 },
  logo:        { fontWeight: 700, fontSize: 16, color: '#1f2937', minWidth: 120, paddingTop: 4 },
  h1:          { margin: '0 0 4px', fontSize: 20, color: '#111827', fontWeight: 700 },
  subtitle:    { margin: 0, fontSize: 13, color: '#6b7280' },
  progress:    { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 28 },
  stepDot:     { width: 24, height: 24, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, flexShrink: 0 },
  stepBody:    { paddingTop: 4 },
  sectionTitle:{ fontSize: 11, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 },
  row2:        { display: 'flex', gap: 12, marginBottom: 12 },
  input:       { width: '100%', border: '1px solid #d1d5db', borderRadius: 8, padding: '9px 12px', fontSize: 13, boxSizing: 'border-box', outline: 'none' },
  textarea:    { width: '100%', border: '1px solid #d1d5db', borderRadius: 8, padding: '10px 12px', fontSize: 13, resize: 'vertical', boxSizing: 'border-box' },
  podGrid:     { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 10 },
  podCard:     { textAlign: 'left', border: '2px solid', borderRadius: 10, padding: '12px 14px', cursor: 'pointer', transition: 'all 0.12s' },
  tagBtn:      { border: '1px solid', borderRadius: 6, padding: '6px 12px', fontSize: 12, cursor: 'pointer', fontWeight: 500 },
  actions:     { display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 28, paddingTop: 20, borderTop: '1px solid #f3f4f6' },
  btn:         { background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, padding: '11px 24px', fontSize: 14, fontWeight: 600, cursor: 'pointer' },
  btnSecondary:{ background: '#fff', color: '#374151', border: '1px solid #d1d5db', borderRadius: 8, padding: '11px 20px', fontSize: 14, cursor: 'pointer' },
  refBox:      { background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 10, padding: '16px 24px', display: 'inline-block' },
  footer:      { borderTop: '1px solid #e5e7eb', paddingTop: 16, marginTop: 32, fontSize: 12, color: '#9ca3af', textAlign: 'center' },
}
