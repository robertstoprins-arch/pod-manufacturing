import { useEffect, useState } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function getTokenFromPath() {
  const match = window.location.pathname.match(/\/quote-view\/([^/]+)/)
  return match ? match[1] : null
}

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

const ACTION_CFG = {
  accepted:           { label: 'Quote Accepted',           cls: 'bg-green-50 border-green-200 text-green-800',  icon: '✓' },
  changes_requested:  { label: 'Changes Requested',        cls: 'bg-amber-50 border-amber-200 text-amber-800',  icon: '↩' },
  declined:           { label: 'Quote Declined',           cls: 'bg-red-50 border-red-200 text-red-700',        icon: '✕' },
}

export default function ClientQuoteView() {
  const token = getTokenFromPath()
  const [quote, setQuote] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [action, setAction] = useState(null)   // 'accepted' | 'changes_requested' | 'declined'
  const [note, setNote] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const [confirmed, setConfirmed] = useState(false)

  useEffect(() => {
    if (!token) { setError('Invalid link — no token found.'); setLoading(false); return }
    publicFetch(`/quotes/view/${token}`)
      .then(data => { setQuote(data); if (data.already_responded) setConfirmed(true) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [token])

  async function handleSubmit() {
    if (!action) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const data = await publicFetch(`/quotes/view/${token}/respond`, {
        method: 'POST',
        body: JSON.stringify({ action, note: note || null }),
      })
      setQuote(data)
      setConfirmed(true)
    } catch (e) {
      setSubmitError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return (
    <Page><Card><p style={{ color: '#6b7280', textAlign: 'center', padding: '32px 0' }}>Loading your quote…</p></Card></Page>
  )

  if (error) return (
    <Page><Card>
      <div style={s.errBox}>
        <strong>Unable to load this quote</strong>
        <p style={{ margin: '4px 0 0' }}>{error}</p>
        <p style={{ margin: '8px 0 0', fontSize: 12, color: '#ef4444' }}>
          If you believe this is an error, please contact us directly.
        </p>
      </div>
    </Card></Page>
  )

  const cfg = ACTION_CFG[quote.client_response]

  return (
    <Page>
      <Card>
        {/* Header */}
        <div style={s.header}>
          <div style={s.logo}>Top-R Solutions</div>
          <div>
            <h1 style={s.h1}>{quote.title}</h1>
            <p style={s.subtitle}>
              {quote.quote_number && <span>{quote.quote_number} · </span>}
              {quote.revision}
              {quote.client_name && <span> · {quote.client_name}</span>}
            </p>
          </div>
        </div>

        {/* Already responded banner */}
        {confirmed && cfg && (
          <div style={{ ...s.respondedBanner, background: cfg.cls.includes('green') ? '#ecfdf5' : cfg.cls.includes('amber') ? '#fffbeb' : '#fef2f2', border: `1px solid ${cfg.cls.includes('green') ? '#6ee7b7' : cfg.cls.includes('amber') ? '#fcd34d' : '#fca5a5'}` }}>
            <span style={{ fontSize: 22, marginRight: 12 }}>{cfg.icon}</span>
            <div>
              <div style={{ fontWeight: 600 }}>{cfg.label}</div>
              {quote.client_response_note && <div style={{ fontSize: 13, marginTop: 2, opacity: 0.8 }}>{quote.client_response_note}</div>}
            </div>
          </div>
        )}

        {/* Spec summary */}
        {quote.spec_summary && Object.values(quote.spec_summary).some(Boolean) && (
          <div style={s.section}>
            <div style={s.sectionTitle}>Pod Specification</div>
            <div style={s.specGrid}>
              {quote.spec_summary.width_m && <SpecItem label="Width" value={`${quote.spec_summary.width_m} m`} />}
              {quote.spec_summary.length_m && <SpecItem label="Length" value={`${quote.spec_summary.length_m} m`} />}
              {quote.spec_summary.wall_height_m && <SpecItem label="Wall Height" value={`${quote.spec_summary.wall_height_m} m`} />}
              {quote.spec_summary.floor_area_m2 && <SpecItem label="Floor Area" value={`${quote.spec_summary.floor_area_m2} m²`} />}
              {quote.spec_summary.roof_type && <SpecItem label="Roof Type" value={quote.spec_summary.roof_type} />}
            </div>
            {quote.spec_summary.openings?.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#9ca3af', textTransform: 'uppercase', marginBottom: 6 }}>Openings</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {quote.spec_summary.openings.map((o, i) => (
                    <span key={i} style={s.tag}>{o.type || 'Opening'} {o.width_m}×{o.height_m}m</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Pricing */}
        <div style={s.section}>
          <div style={s.sectionTitle}>Pricing</div>
          <div style={s.priceTable}>
            {quote.total_ex_vat != null && (
              <div style={s.priceRow}>
                <span style={s.priceLabel}>Total (ex. VAT)</span>
                <span style={s.priceValue}>{quote.currency} {Number(quote.total_ex_vat).toLocaleString()}</span>
              </div>
            )}
            {quote.total_inc_vat != null && (
              <div style={{ ...s.priceRow, borderTop: '2px solid #e5e7eb', paddingTop: 10, marginTop: 4 }}>
                <span style={{ ...s.priceLabel, fontWeight: 700, color: '#111827' }}>Total (inc. VAT)</span>
                <span style={{ ...s.priceValue, fontWeight: 700, fontSize: 20, color: '#111827' }}>{quote.currency} {Number(quote.total_inc_vat).toLocaleString()}</span>
              </div>
            )}
            {quote.deposit_percent != null && (
              <div style={{ ...s.priceRow, marginTop: 8 }}>
                <span style={s.priceLabel}>Deposit Required ({quote.deposit_percent}%)</span>
                <span style={{ ...s.priceValue, color: '#2563eb' }}>
                  {quote.currency} {quote.deposit_amount != null
                    ? Number(quote.deposit_amount).toLocaleString()
                    : quote.total_ex_vat != null
                      ? (Number(quote.total_ex_vat) * Number(quote.deposit_percent) / 100).toLocaleString()
                      : '—'}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Validity */}
        {quote.expires_at && (
          <div style={s.validityRow}>
            <span>Quote valid until: </span>
            <strong>{new Date(quote.expires_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}</strong>
          </div>
        )}

        {/* Notes */}
        {quote.notes && (
          <div style={s.section}>
            <div style={s.sectionTitle}>Notes & Assumptions</div>
            <p style={{ fontSize: 13, color: '#4b5563', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{quote.notes}</p>
          </div>
        )}

        {/* Response actions */}
        {!confirmed && (
          <div style={s.section}>
            <div style={s.sectionTitle}>Your Response</div>
            <div style={s.actionButtons}>
              {[
                ['accepted', 'Accept Quote', '#16a34a', '#dcfce7', '#bbf7d0'],
                ['changes_requested', 'Request Changes', '#d97706', '#fffbeb', '#fde68a'],
                ['declined', 'Decline', '#dc2626', '#fef2f2', '#fecaca'],
              ].map(([val, label, color, bg, border]) => (
                <button
                  key={val}
                  onClick={() => setAction(action === val ? null : val)}
                  style={{
                    flex: 1,
                    padding: '10px 16px',
                    borderRadius: 8,
                    border: `2px solid ${action === val ? color : '#e5e7eb'}`,
                    background: action === val ? bg : '#fff',
                    color: action === val ? color : '#374151',
                    fontWeight: 600,
                    fontSize: 14,
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                >
                  {label}
                </button>
              ))}
            </div>

            {action && (
              <div style={{ marginTop: 16 }}>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 6 }}>
                  {action === 'accepted' ? 'Any comments? (optional)' : action === 'changes_requested' ? 'What would you like to change?' : 'Reason for declining (optional)'}
                </label>
                <textarea
                  rows={3}
                  value={note}
                  onChange={e => setNote(e.target.value)}
                  placeholder={action === 'changes_requested' ? 'Please describe the changes you need…' : ''}
                  style={s.textarea}
                />
                {submitError && <p style={{ color: '#dc2626', fontSize: 12, marginTop: 6 }}>{submitError}</p>}
                <button
                  onClick={handleSubmit}
                  disabled={submitting || (action === 'changes_requested' && !note.trim())}
                  style={{
                    ...s.submitBtn,
                    background: action === 'accepted' ? '#16a34a' : action === 'declined' ? '#dc2626' : '#d97706',
                    opacity: submitting ? 0.7 : 1,
                    marginTop: 12,
                  }}
                >
                  {submitting ? 'Submitting…' : action === 'accepted' ? 'Confirm Acceptance' : action === 'changes_requested' ? 'Send Request' : 'Confirm Decline'}
                </button>
              </div>
            )}
          </div>
        )}

        <div style={s.footer}>
          Questions? Contact us at <a href="mailto:info@top-r.com" style={{ color: '#2563eb' }}>info@top-r.com</a>
        </div>
      </Card>
    </Page>
  )
}

function Page({ children }) {
  return <div style={{ minHeight: '100vh', background: '#f3f4f6', padding: '32px 16px', fontFamily: 'system-ui, sans-serif' }}>{children}</div>
}

function Card({ children }) {
  return <div style={{ maxWidth: 680, margin: '0 auto', background: '#fff', borderRadius: 12, padding: 32, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>{children}</div>
}

function SpecItem({ label, value }) {
  return (
    <div style={{ background: '#f9fafb', borderRadius: 8, padding: '10px 14px' }}>
      <div style={{ fontSize: 11, color: '#9ca3af', fontWeight: 600, textTransform: 'uppercase', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 15, fontWeight: 600, color: '#111827' }}>{value}</div>
    </div>
  )
}

const s = {
  header:     { display: 'flex', alignItems: 'flex-start', gap: 20, paddingBottom: 20, borderBottom: '2px solid #e5e7eb', marginBottom: 24 },
  logo:       { fontWeight: 700, fontSize: 16, color: '#1f2937', minWidth: 120, paddingTop: 4 },
  h1:         { margin: '0 0 4px', fontSize: 20, color: '#111827', fontWeight: 700 },
  subtitle:   { margin: 0, fontSize: 13, color: '#6b7280' },
  section:    { marginBottom: 24 },
  sectionTitle: { fontSize: 11, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 },
  specGrid:   { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 10 },
  tag:        { fontSize: 11, background: '#f3f4f6', border: '1px solid #e5e7eb', borderRadius: 4, padding: '3px 8px', color: '#374151' },
  priceTable: { background: '#f9fafb', borderRadius: 10, padding: '16px 20px' },
  priceRow:   { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0' },
  priceLabel: { fontSize: 14, color: '#6b7280' },
  priceValue: { fontSize: 16, fontWeight: 600, color: '#111827' },
  validityRow: { fontSize: 13, color: '#6b7280', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 8, padding: '10px 14px', marginBottom: 24 },
  actionButtons: { display: 'flex', gap: 10 },
  textarea:   { width: '100%', border: '1px solid #d1d5db', borderRadius: 8, padding: '10px 12px', fontSize: 13, resize: 'vertical', boxSizing: 'border-box' },
  submitBtn:  { color: '#fff', border: 'none', borderRadius: 8, padding: '12px 28px', fontSize: 15, fontWeight: 600, cursor: 'pointer', width: '100%' },
  respondedBanner: { display: 'flex', alignItems: 'center', borderRadius: 10, padding: '16px 20px', marginBottom: 24 },
  errBox:     { background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '16px 20px', color: '#dc2626' },
  footer:     { borderTop: '1px solid #e5e7eb', paddingTop: 16, marginTop: 24, fontSize: 12, color: '#9ca3af', textAlign: 'center' },
}
