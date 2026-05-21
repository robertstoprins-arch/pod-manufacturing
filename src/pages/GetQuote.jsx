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

const POD_TYPES = [
  { value: 'bathroom', label: 'Bathroom Pod',  desc: 'Full bathroom with shower, WC and vanity' },
  { value: 'shower',   label: 'Shower Pod',    desc: 'Shower enclosure with wet room finish' },
  { value: 'wc',       label: 'WC Pod',        desc: 'Compact toilet compartment' },
  { value: 'office',   label: 'Office Pod',    desc: 'Acoustic workspace or meeting pod' },
  { value: 'kitchen',  label: 'Kitchen Pod',   desc: 'Compact kitchen or kitchenette unit' },
  { value: 'custom',   label: 'Custom',        desc: 'Something else — describe in notes' },
]

const TIMELINES = [
  { value: 'asap',     label: 'As soon as possible' },
  { value: '3months',  label: 'Within 3 months' },
  { value: '6months',  label: 'Within 6 months' },
  { value: '12months', label: 'Within 12 months' },
]

const USES = [
  { value: 'hotel',       label: 'Hotel / Hospitality' },
  { value: 'residential', label: 'Residential' },
  { value: 'student',     label: 'Student Housing' },
  { value: 'healthcare',  label: 'Healthcare' },
  { value: 'office',      label: 'Office / Commercial' },
  { value: 'other',       label: 'Other' },
]

export default function GetQuote() {
  const [step, setStep] = useState(1)
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone: '', company_name: '',
    pod_type: '', quantity: 1, size_option: '', width_m: '', length_m: '',
    location: '', intended_use: '', timeline: '', budget_range: '', notes: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const step1Valid = form.first_name && form.last_name && form.email
  const step2Valid = form.pod_type

  async function handleSubmit() {
    setSubmitting(true)
    setError(null)
    try {
      const payload = {
        ...form,
        quantity: parseInt(form.quantity) || 1,
        width_m:  form.width_m  ? parseFloat(form.width_m)  : null,
        length_m: form.length_m ? parseFloat(form.length_m) : null,
        phone:        form.phone        || null,
        company_name: form.company_name || null,
        size_option:  form.size_option  || null,
        location:     form.location     || null,
        intended_use: form.intended_use || null,
        timeline:     form.timeline     || null,
        budget_range: form.budget_range || null,
        notes:        form.notes        || null,
      }
      const data = await publicFetch('/enquiry', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (result) return (
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

        {/* Progress */}
        <div style={s.progress}>
          {[1, 2, 3].map(n => (
            <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{
                ...s.stepDot,
                background: step >= n ? '#2563eb' : '#e5e7eb',
                color: step >= n ? '#fff' : '#9ca3af',
              }}>{n}</div>
              <span style={{ fontSize: 12, color: step === n ? '#111827' : '#9ca3af', fontWeight: step === n ? 600 : 400 }}>
                {n === 1 ? 'Contact' : n === 2 ? 'Pod Type' : 'Project Details'}
              </span>
              {n < 3 && <div style={{ flex: 1, height: 1, background: '#e5e7eb', minWidth: 20 }} />}
            </div>
          ))}
        </div>

        {/* Step 1 — Contact */}
        {step === 1 && (
          <div style={s.stepBody}>
            <div style={s.sectionTitle}>Your contact details</div>
            <div style={s.row2}>
              <Input label="First name *" value={form.first_name} onChange={v => set('first_name', v)} />
              <Input label="Last name *"  value={form.last_name}  onChange={v => set('last_name', v)} />
            </div>
            <Input label="Email address *" type="email" value={form.email} onChange={v => set('email', v)} />
            <div style={s.row2}>
              <Input label="Phone"        value={form.phone}        onChange={v => set('phone', v)} />
              <Input label="Company name" value={form.company_name} onChange={v => set('company_name', v)} />
            </div>
            <div style={s.actions}>
              <button
                style={{ ...s.btn, opacity: step1Valid ? 1 : 0.5 }}
                disabled={!step1Valid}
                onClick={() => setStep(2)}
              >
                Next: Pod Type →
              </button>
            </div>
          </div>
        )}

        {/* Step 2 — Pod Type */}
        {step === 2 && (
          <div style={s.stepBody}>
            <div style={s.sectionTitle}>What type of pod do you need?</div>
            <div style={s.podGrid}>
              {POD_TYPES.map(pt => (
                <button
                  key={pt.value}
                  onClick={() => set('pod_type', pt.value)}
                  style={{
                    ...s.podCard,
                    borderColor: form.pod_type === pt.value ? '#2563eb' : '#e5e7eb',
                    background:  form.pod_type === pt.value ? '#eff6ff' : '#fff',
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: 14, color: form.pod_type === pt.value ? '#1d4ed8' : '#111827' }}>
                    {pt.label}
                  </div>
                  <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>{pt.desc}</div>
                </button>
              ))}
            </div>

            <div style={{ marginTop: 20 }}>
              <div style={s.sectionTitle}>Quantity</div>
              <input
                type="number" min={1} max={100}
                value={form.quantity}
                onChange={e => set('quantity', e.target.value)}
                style={{ ...s.input, width: 80 }}
              />
            </div>

            <div style={{ marginTop: 20 }}>
              <div style={s.sectionTitle}>Approximate size (optional)</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {['small', 'medium', 'large'].map(sz => (
                  <button key={sz} onClick={() => set('size_option', form.size_option === sz ? '' : sz)}
                    style={{ ...s.tagBtn, borderColor: form.size_option === sz ? '#2563eb' : '#e5e7eb', background: form.size_option === sz ? '#eff6ff' : '#fff', color: form.size_option === sz ? '#1d4ed8' : '#374151' }}>
                    {sz.charAt(0).toUpperCase() + sz.slice(1)} {sz === 'small' ? '(<6m²)' : sz === 'medium' ? '(6–12m²)' : '(>12m²)'}
                  </button>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 10, alignItems: 'center' }}>
                <Input label="Width (m)" type="number" value={form.width_m} onChange={v => set('width_m', v)} style={{ width: 100 }} />
                <span style={{ paddingTop: 20, color: '#9ca3af' }}>×</span>
                <Input label="Length (m)" type="number" value={form.length_m} onChange={v => set('length_m', v)} style={{ width: 100 }} />
              </div>
            </div>

            <div style={s.actions}>
              <button style={s.btnSecondary} onClick={() => setStep(1)}>← Back</button>
              <button
                style={{ ...s.btn, opacity: step2Valid ? 1 : 0.5 }}
                disabled={!step2Valid}
                onClick={() => setStep(3)}
              >
                Next: Project Details →
              </button>
            </div>
          </div>
        )}

        {/* Step 3 — Project details */}
        {step === 3 && (
          <div style={s.stepBody}>
            <div style={s.sectionTitle}>Project location</div>
            <Input label="City / Country" value={form.location} onChange={v => set('location', v)} />

            <div style={{ marginTop: 20 }}>
              <div style={s.sectionTitle}>Intended use</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {USES.map(u => (
                  <button key={u.value} onClick={() => set('intended_use', form.intended_use === u.value ? '' : u.value)}
                    style={{ ...s.tagBtn, borderColor: form.intended_use === u.value ? '#2563eb' : '#e5e7eb', background: form.intended_use === u.value ? '#eff6ff' : '#fff', color: form.intended_use === u.value ? '#1d4ed8' : '#374151' }}>
                    {u.label}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ marginTop: 20 }}>
              <div style={s.sectionTitle}>Timeline</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {TIMELINES.map(t => (
                  <button key={t.value} onClick={() => set('timeline', form.timeline === t.value ? '' : t.value)}
                    style={{ ...s.tagBtn, borderColor: form.timeline === t.value ? '#2563eb' : '#e5e7eb', background: form.timeline === t.value ? '#eff6ff' : '#fff', color: form.timeline === t.value ? '#1d4ed8' : '#374151' }}>
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ marginTop: 20 }}>
              <div style={s.sectionTitle}>Notes or special requirements (optional)</div>
              <textarea
                rows={4}
                value={form.notes}
                onChange={e => set('notes', e.target.value)}
                placeholder="Anything else we should know — finishes, access constraints, site conditions…"
                style={s.textarea}
              />
            </div>

            {error && <p style={{ color: '#dc2626', fontSize: 13, marginTop: 12 }}>{error}</p>}

            <div style={s.actions}>
              <button style={s.btnSecondary} onClick={() => setStep(2)}>← Back</button>
              <button
                style={{ ...s.btn, opacity: submitting ? 0.7 : 1 }}
                disabled={submitting}
                onClick={handleSubmit}
              >
                {submitting ? 'Sending…' : 'Submit Enquiry'}
              </button>
            </div>
          </div>
        )}

        <div style={s.footer}>
          Top-R Solutions · <a href="mailto:info@top-r.com" style={{ color: '#2563eb' }}>info@top-r.com</a>
        </div>
      </Card>
    </Page>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

import { useState } from 'react'

function Page({ children }) {
  return <div style={{ minHeight: '100vh', background: '#f3f4f6', padding: '32px 16px', fontFamily: 'system-ui, sans-serif' }}>{children}</div>
}

function Card({ children }) {
  return <div style={{ maxWidth: 640, margin: '0 auto', background: '#fff', borderRadius: 12, padding: 32, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>{children}</div>
}

function Input({ label, value, onChange, type = 'text', style: extraStyle }) {
  return (
    <div style={{ flex: 1, minWidth: 120, ...extraStyle }}>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#374151', marginBottom: 4 }}>{label}</label>
      <input
        type={type}
        value={value}
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
