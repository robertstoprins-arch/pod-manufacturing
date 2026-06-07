/**
 * Public quote enquiry form.
 *
 * Renders a 9-step questionnaire driven by a ProductTemplate config.
 * Steps: Contact → Pod Type → Dimensions → Openings → Finishes →
 *        Services → Foundation → Delivery → Review & Submit
 *
 * The Review step shows location/use/timeline/notes fields then
 * a compact summary of all previous answers before submission.
 */

import { useState, useEffect, useRef } from 'react'
import { getDefaultTemplate, stepFields } from '../config/productTemplates'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

if (import.meta.env.DEV && !import.meta.env.VITE_API_URL) {
  console.warn('[GetQuote] VITE_API_URL is not set — using http://localhost:8000')
}

const DRAFT_KEY = 'get_quote_draft_office_pod'
const SUBMIT_TIMEOUT_MS = 90_000

async function publicFetch(path, opts = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = body?.detail || body?.message || res.statusText
    throw new Error(detail || `Server error (${res.status})`)
  }
  return res.json()
}

async function fetchWithTimeout(path, opts = {}, timeoutMs = SUBMIT_TIMEOUT_MS) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await publicFetch(path, { ...opts, signal: controller.signal })
  } finally {
    clearTimeout(timer)
  }
}

export default function GetQuote() {
  const template = getDefaultTemplate()

  const [answers, setAnswers] = useState(() => {
    // Restore draft from localStorage if available
    try {
      const saved = localStorage.getItem(DRAFT_KEY)
      if (saved) return JSON.parse(saved)
    } catch (_) {}
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
  const [submitMsg, setSubmitMsg] = useState('')
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  // warm-up banner: null | 'warming' | 'ready' | 'slow'
  const [warmup, setWarmup] = useState(null)
  const warmupDone = useRef(false)

  // Save draft to localStorage whenever answers change
  useEffect(() => {
    try { localStorage.setItem(DRAFT_KEY, JSON.stringify(answers)) } catch (_) {}
  }, [answers])

  // Warm up the backend when the page loads
  useEffect(() => {
    if (warmupDone.current) return
    warmupDone.current = true

    const slowTimer = setTimeout(() => setWarmup('warming'), 2000)

    fetch(`${API}/ping`, { method: 'GET' })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(() => { clearTimeout(slowTimer); setWarmup('ready') })
      .catch(() => { clearTimeout(slowTimer); setWarmup('slow') })
  }, [])

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

  const stepValid = currentFields
    .filter(f => f.required)
    .every(f => {
      const v = answers[f.key]
      return v !== '' && v !== null && v !== undefined
    })

  async function handleSubmit() {
    if (submitting) return
    setSubmitting(true)
    setError(null)
    setSubmitMsg('Submitting your quote request…')

    const contactFields = stepFields(template, 'contact').map(f => f.key)
    const productAnswers = {}
    Object.entries(answers).forEach(([k, v]) => {
      if (!contactFields.includes(k)) {
        const field = template.fields.find(f => f.key === k)
        if (field?.type === 'number' && v !== '' && v !== null && v !== undefined) {
          productAnswers[k] = Number(v)
        } else {
          productAnswers[k] = (v === '' || v === undefined) ? null : v
        }
      }
    })

    const payload = {
      first_name:          answers.first_name,
      last_name:           answers.last_name,
      email:               answers.email,
      phone:               answers.phone        || null,
      company_name:        answers.company_name || null,
      product_template_id: template.id,
      answers:             productAnswers,
    }

    const opts = { method: 'POST', body: JSON.stringify(payload) }

    const attempt = async (isRetry) => {
      if (isRetry) setSubmitMsg('Server is waking up — retrying…')
      return fetchWithTimeout('/enquiry', opts)
    }

    try {
      let data
      try {
        data = await attempt(false)
      } catch (firstErr) {
        const isNetwork = firstErr.name === 'AbortError' || firstErr.message === 'Failed to fetch' || firstErr.name === 'TypeError'
        if (isNetwork) {
          setSubmitMsg('Server is waking up — retrying in 3 seconds…')
          await new Promise(r => setTimeout(r, 3000))
          data = await attempt(true)
        } else {
          throw firstErr
        }
      }
      try { localStorage.removeItem(DRAFT_KEY) } catch (_) {}
      setResult(data)
    } catch (e) {
      const isNetwork = e.name === 'AbortError' || e.message === 'Failed to fetch' || e.name === 'TypeError'
      setError(
        isNetwork
          ? 'The quote server did not respond in time. Your answers are saved on this page — please wait 10 seconds and press Submit again.'
          : `Could not submit your enquiry: ${e.message}`
      )
    } finally {
      setSubmitting(false)
      setSubmitMsg('')
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
        {/* Warm-up banner */}
        {warmup === 'warming' && (
          <div style={s.warmupBanner}>
            <span style={s.warmupSpinner}>⟳</span>
            Preparing quote system… this may take a few seconds.
          </div>
        )}
        {warmup === 'slow' && (
          <div style={{ ...s.warmupBanner, background: '#fffbeb', borderColor: '#fcd34d', color: '#92400e' }}>
            The quote system is taking longer than usual to respond. You can still complete the form — if submission fails, please try again in a moment.
          </div>
        )}

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
            <div key={step.id} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{
                ...s.stepDot,
                background: stepIndex > i ? '#16a34a' : stepIndex === i ? '#2563eb' : '#e5e7eb',
                color:      stepIndex >= i ? '#fff' : '#9ca3af',
              }}>
                {stepIndex > i ? '✓' : i + 1}
              </div>
              <span style={{
                fontSize:   11,
                color:      stepIndex === i ? '#111827' : stepIndex > i ? '#6b7280' : '#9ca3af',
                fontWeight: stepIndex === i ? 600 : 400,
                display:    window.innerWidth < 500 ? 'none' : 'block',
              }}>
                {step.nav_label}
              </span>
              {i < steps.length - 1 && (
                <div style={{ flex: 1, height: 1, background: stepIndex > i ? '#bbf7d0' : '#e5e7eb', minWidth: 8 }} />
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
            template={template}
          />
        </div>

        {submitMsg && (
          <p style={{ fontSize: 13, color: '#2563eb', marginTop: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⟳</span>
            {submitMsg}
          </p>
        )}
        {error && (
          <div style={s.errorBox}>
            <strong>Submission failed</strong>
            <p style={{ margin: '4px 0 0', fontWeight: 400 }}>{error}</p>
          </div>
        )}

        {/* Navigation */}
        <div style={s.actions}>
          {stepIndex > 0 && (
            <button style={s.btnSecondary} onClick={() => setStepIndex(i => i - 1)} disabled={submitting}>
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
              style={{ ...s.btn, opacity: submitting ? 0.7 : 1, cursor: submitting ? 'not-allowed' : 'pointer' }}
              disabled={submitting}
              onClick={handleSubmit}
            >
              {submitting ? 'Submitting…' : 'Submit Enquiry'}
            </button>
          )}
        </div>

        <div style={s.footer}>
          Step {stepIndex + 1} of {steps.length} · Top-R Solutions ·{' '}
          <a href="mailto:info@top-r.com" style={{ color: '#2563eb' }}>info@top-r.com</a>
        </div>
      </Card>
    </Page>
  )
}

// ── Step renderer ─────────────────────────────────────────────────────────────

function StepRenderer({ step, fields, answers, set, template }) {
  // Contact step: custom 2-column layout
  if (step.id === 'contact') {
    return (
      <>
        <div style={s.sectionTitle}>{step.title}</div>
        <div style={s.row2}>
          <FieldInput field={fields.find(f => f.key === 'first_name')} answers={answers} set={set} />
          <FieldInput field={fields.find(f => f.key === 'last_name')}  answers={answers} set={set} />
        </div>
        <FieldInput field={fields.find(f => f.key === 'email')} answers={answers} set={set} />
        <div style={{ ...s.row2, marginTop: 12 }}>
          <FieldInput field={fields.find(f => f.key === 'phone')}        answers={answers} set={set} />
          <FieldInput field={fields.find(f => f.key === 'company_name')} answers={answers} set={set} />
        </div>
      </>
    )
  }

  // Dimensions step: width × length + height
  if (step.id === 'dimensions') {
    const wf = fields.find(f => f.key === 'width_m')
    const lf = fields.find(f => f.key === 'length_m')
    const hf = fields.find(f => f.key === 'height_m')
    return (
      <>
        <div style={s.sectionTitle}>{step.title}</div>
        <p style={{ fontSize: 13, color: '#6b7280', marginTop: 0, marginBottom: 16 }}>
          Enter the approximate footprint and height you have in mind. You can leave these blank if you're not sure yet.
        </p>
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#374151', marginBottom: 8 }}>Footprint</div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
            <InlineInput
              label="Width (m)"
              type="number"
              value={answers.width_m ?? ''}
              placeholder={wf?.placeholder}
              min={wf?.validation?.min} max={wf?.validation?.max} step={wf?.validation?.step}
              onChange={v => set('width_m', v)}
              style={{ width: 110 }}
            />
            <span style={{ paddingBottom: 10, color: '#9ca3af', fontSize: 16 }}>×</span>
            <InlineInput
              label="Length (m)"
              type="number"
              value={answers.length_m ?? ''}
              placeholder={lf?.placeholder}
              min={lf?.validation?.min} max={lf?.validation?.max} step={lf?.validation?.step}
              onChange={v => set('length_m', v)}
              style={{ width: 110 }}
            />
          </div>
          {answers.width_m && answers.length_m && (
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 6 }}>
              Floor area: {(parseFloat(answers.width_m) * parseFloat(answers.length_m)).toFixed(1)} m²
            </div>
          )}
        </div>
        <div style={{ marginBottom: 20 }}>
          <InlineInput
            label="Internal height (m) — optional"
            type="number"
            value={answers.height_m ?? ''}
            placeholder={hf?.placeholder}
            min={hf?.validation?.min} max={hf?.validation?.max} step={hf?.validation?.step}
            onChange={v => set('height_m', v)}
            style={{ width: 110 }}
          />
        </div>
      </>
    )
  }

  // Openings step: count + type pairs
  if (step.id === 'openings') {
    const doorCountF  = fields.find(f => f.key === 'door_count')
    const doorTypeF   = fields.find(f => f.key === 'door_type')
    const winCountF   = fields.find(f => f.key === 'window_count')
    const winTypeF    = fields.find(f => f.key === 'window_type')
    const roofF       = fields.find(f => f.key === 'rooflight_count')
    return (
      <>
        <div style={s.sectionTitle}>{step.title}</div>

        <div style={s.openingGroup}>
          <div style={s.openingLabel}>Doors</div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <InlineInput
              label="Count"
              type="number"
              value={answers.door_count ?? ''}
              min={doorCountF?.validation?.min} max={doorCountF?.validation?.max}
              onChange={v => set('door_count', v)}
              style={{ width: 70 }}
            />
            <div style={{ flex: 1, minWidth: 180 }}>
              <div style={{ fontSize: 12, color: '#374151', marginBottom: 6 }}>Style</div>
              <TagGroup field={doorTypeF} answers={answers} set={set} />
            </div>
          </div>
        </div>

        <div style={s.openingGroup}>
          <div style={s.openingLabel}>Windows</div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <InlineInput
              label="Count"
              type="number"
              value={answers.window_count ?? ''}
              min={winCountF?.validation?.min} max={winCountF?.validation?.max}
              onChange={v => set('window_count', v)}
              style={{ width: 70 }}
            />
            <div style={{ flex: 1, minWidth: 180 }}>
              <div style={{ fontSize: 12, color: '#374151', marginBottom: 6 }}>Style</div>
              <TagGroup field={winTypeF} answers={answers} set={set} />
            </div>
          </div>
        </div>

        <div style={s.openingGroup}>
          <div style={s.openingLabel}>Rooflights / Skylights</div>
          <InlineInput
            label="Count"
            type="number"
            value={answers.rooflight_count ?? ''}
            min={roofF?.validation?.min} max={roofF?.validation?.max}
            onChange={v => set('rooflight_count', v)}
            style={{ width: 70 }}
          />
        </div>
      </>
    )
  }

  // Review step: context fields + summary
  if (step.id === 'review') {
    return (
      <>
        <div style={s.sectionTitle}>Almost there</div>
        <p style={{ fontSize: 13, color: '#6b7280', marginTop: 0, marginBottom: 16 }}>
          Tell us a little more about your project, then review your selections before submitting.
        </p>
        {fields.map(field => (
          <div key={field.key} style={{ marginBottom: 18 }}>
            <FieldInput field={field} answers={answers} set={set} />
          </div>
        ))}
        <ReviewSummary template={template} answers={answers} />
      </>
    )
  }

  // Default: render fields in declaration order
  return (
    <>
      <div style={s.sectionTitle}>{step.title}</div>
      {fields.map(field => (
        <div key={field.key} style={{ marginBottom: 20 }}>
          <FieldInput field={field} answers={answers} set={set} />
        </div>
      ))}
    </>
  )
}

// ── Review summary ────────────────────────────────────────────────────────────

function ReviewSummary({ template, answers }) {
  const label = (fieldKey, val) => {
    if (!val && val !== 0) return null
    const field = template.fields.find(f => f.key === fieldKey)
    if (!field) return String(val)
    if (field.options) {
      const opt = field.options.find(o => o.value === val)
      return opt ? opt.label : String(val)
    }
    return String(val)
  }

  const rows = [
    { section: 'Pod',         items: [
      { k: 'Pod Type',   v: label('pod_type', answers.pod_type) },
      { k: 'Quantity',   v: answers.quantity > 0 ? answers.quantity : null },
    ]},
    { section: 'Dimensions',  items: [
      { k: 'Width',      v: answers.width_m  ? `${answers.width_m} m`  : null },
      { k: 'Length',     v: answers.length_m ? `${answers.length_m} m` : null },
      { k: 'Height',     v: answers.height_m ? `${answers.height_m} m` : null },
    ]},
    { section: 'Openings',    items: [
      { k: 'Doors',      v: answers.door_count != null && answers.door_count !== '' ? `${answers.door_count} × ${label('door_type', answers.door_type) || ''}`.trim().replace(/× $/, '') : null },
      { k: 'Windows',    v: answers.window_count != null && answers.window_count !== '' ? `${answers.window_count} × ${label('window_type', answers.window_type) || ''}`.trim().replace(/× $/, '') : null },
      { k: 'Rooflights', v: answers.rooflight_count ? answers.rooflight_count : null },
    ]},
    { section: 'Finishes',    items: [
      { k: 'External',   v: label('external_finish', answers.external_finish) },
      { k: 'Internal',   v: label('internal_finish_package', answers.internal_finish_package) },
    ]},
    { section: 'Services',    items: [
      { k: 'Heating',    v: label('heating_option', answers.heating_option) },
      { k: 'Ventilation',v: label('ventilation_option', answers.ventilation_option) },
      { k: 'Electrical', v: label('electrical_package', answers.electrical_package) },
    ]},
    { section: 'Foundation',  items: [
      { k: 'Type',       v: label('foundation_option', answers.foundation_option) },
    ]},
    { section: 'Delivery',    items: [
      { k: 'Option',     v: label('delivery_install_option', answers.delivery_install_option) },
    ]},
  ]

  const nonEmpty = rows.map(r => ({
    ...r,
    items: r.items.filter(i => i.v != null && i.v !== '' && i.v !== 'undefined'),
  })).filter(r => r.items.length > 0)

  if (!nonEmpty.length) return null

  return (
    <div style={{ marginTop: 24, border: '1px solid #e5e7eb', borderRadius: 10, overflow: 'hidden' }}>
      <div style={{ background: '#f9fafb', padding: '10px 16px', fontSize: 11, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        Your Selections
      </div>
      {nonEmpty.map(row => (
        <div key={row.section} style={{ borderTop: '1px solid #f3f4f6', padding: '10px 16px' }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#9ca3af', marginBottom: 6 }}>{row.section}</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '4px 16px' }}>
            {row.items.map(item => (
              <div key={item.k} style={{ fontSize: 12 }}>
                <span style={{ color: '#9ca3af' }}>{item.k}: </span>
                <span style={{ color: '#111827', fontWeight: 500 }}>{item.v}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Field renderers ───────────────────────────────────────────────────────────

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
          <TagGroup field={field} answers={answers} set={set} />
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

function TagGroup({ field, answers, set }) {
  if (!field) return null
  const value = answers[field.key] ?? ''
  return (
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
          {opt.label}
        </button>
      ))}
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Page({ children }) {
  return (
    <div style={{ minHeight: '100vh', background: '#f3f4f6', padding: '32px 16px', fontFamily: 'system-ui, sans-serif' }}>
      <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }`}</style>
      {children}
    </div>
  )
}

function Card({ children }) {
  return (
    <div style={{ maxWidth: 680, margin: '0 auto', background: '#fff', borderRadius: 12, padding: 32, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
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
  header:       { display: 'flex', alignItems: 'flex-start', gap: 20, paddingBottom: 20, borderBottom: '2px solid #e5e7eb', marginBottom: 24 },
  logo:         { fontWeight: 700, fontSize: 16, color: '#1f2937', minWidth: 120, paddingTop: 4 },
  h1:           { margin: '0 0 4px', fontSize: 20, color: '#111827', fontWeight: 700 },
  subtitle:     { margin: 0, fontSize: 13, color: '#6b7280' },
  progress:     { display: 'flex', alignItems: 'center', gap: 4, marginBottom: 28, overflowX: 'auto', paddingBottom: 4 },
  stepDot:      { width: 22, height: 22, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, flexShrink: 0 },
  stepBody:     { paddingTop: 4 },
  sectionTitle: { fontSize: 11, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 },
  row2:         { display: 'flex', gap: 12, marginBottom: 12 },
  input:        { width: '100%', border: '1px solid #d1d5db', borderRadius: 8, padding: '9px 12px', fontSize: 13, boxSizing: 'border-box', outline: 'none' },
  textarea:     { width: '100%', border: '1px solid #d1d5db', borderRadius: 8, padding: '10px 12px', fontSize: 13, resize: 'vertical', boxSizing: 'border-box' },
  podGrid:      { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 10 },
  podCard:      { textAlign: 'left', border: '2px solid', borderRadius: 10, padding: '12px 14px', cursor: 'pointer', transition: 'all 0.12s' },
  tagBtn:       { border: '1px solid', borderRadius: 6, padding: '6px 12px', fontSize: 12, cursor: 'pointer', fontWeight: 500 },
  actions:      { display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 28, paddingTop: 20, borderTop: '1px solid #f3f4f6' },
  btn:          { background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, padding: '11px 24px', fontSize: 14, fontWeight: 600, cursor: 'pointer' },
  btnSecondary: { background: '#fff', color: '#374151', border: '1px solid #d1d5db', borderRadius: 8, padding: '11px 20px', fontSize: 14, cursor: 'pointer' },
  refBox:       { background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 10, padding: '16px 24px', display: 'inline-block' },
  footer:       { borderTop: '1px solid #e5e7eb', paddingTop: 16, marginTop: 32, fontSize: 12, color: '#9ca3af', textAlign: 'center' },
  openingGroup:  { marginBottom: 20, padding: '14px 16px', background: '#f9fafb', borderRadius: 8, border: '1px solid #f3f4f6' },
  openingLabel:  { fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 10 },
  warmupBanner:  { background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 8, padding: '10px 14px', marginBottom: 16, fontSize: 13, color: '#1d4ed8', display: 'flex', alignItems: 'center', gap: 8 },
  warmupSpinner: { display: 'inline-block', animation: 'spin 1s linear infinite', fontSize: 16 },
  errorBox:      { background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', marginTop: 12, fontSize: 13, color: '#dc2626', fontWeight: 600 },
}
