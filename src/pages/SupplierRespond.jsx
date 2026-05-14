import { useEffect, useState } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Extract token from URL path like /rfq-respond/<token>
function getTokenFromPath() {
  const match = window.location.pathname.match(/\/rfq-respond\/([^/]+)/)
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

const AVAILABILITY_OPTIONS = ['In stock', 'Made to order', 'Lead time only', 'Not available']

export default function SupplierRespond() {
  const token = getTokenFromPath()
  const [rfq, setRfq] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lines, setLines] = useState([])
  const [globalNotes, setGlobalNotes] = useState('')
  const [globalCurrency, setGlobalCurrency] = useState('EUR')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  useEffect(() => {
    publicFetch(`/rfq/respond/${token}`)
      .then(data => {
        setRfq(data)
        setGlobalCurrency(data.currency || 'EUR')
        setLines(
          data.items.map(item => ({
            line_id: String(item.line_id),
            description: item.description,
            unit_price: '',
            quantity: item.quantity ?? '',
            lead_time_days: '',
            availability: '',
            substitute_offered: false,
            substitute_description: '',
            notes: '',
          }))
        )
        if (data.already_responded) setSubmitted(true)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [token])

  function updateLine(idx, field, value) {
    setLines(prev => prev.map((l, i) => i === idx ? { ...l, [field]: value } : l))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setSubmitError(null)
    try {
      const payload = {
        notes: globalNotes || null,
        currency: globalCurrency || null,
        lines: lines.map(l => ({
          line_id: l.line_id,
          unit_price: l.unit_price !== '' ? parseFloat(l.unit_price) : null,
          quantity: l.quantity !== '' ? parseFloat(l.quantity) : null,
          lead_time_days: l.lead_time_days !== '' ? parseInt(l.lead_time_days) : null,
          availability: l.availability || null,
          substitute_offered: l.substitute_offered,
          substitute_description: l.substitute_description || null,
          notes: l.notes || null,
        })),
      }
      await publicFetch(`/rfq/respond/${token}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setSubmitted(true)
    } catch (err) {
      setSubmitError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return (
    <div style={styles.page}>
      <div style={styles.card}>
        <p style={{ color: '#6b7280' }}>Loading RFQ…</p>
      </div>
    </div>
  )

  if (error) return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.errorBox}>
          <strong>Unable to load this RFQ</strong>
          <p style={{ margin: '4px 0 0' }}>{error}</p>
        </div>
      </div>
    </div>
  )

  if (submitted) return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.successBox}>
          <div style={{ fontSize: 40, marginBottom: 8 }}>✓</div>
          <h2 style={{ margin: '0 0 8px', color: '#065f46' }}>Response submitted</h2>
          <p style={{ color: '#047857', margin: 0 }}>
            Thank you, <strong>{rfq?.supplier_name}</strong>. Your pricing has been received.
            The team will be in touch if they have questions.
          </p>
        </div>
      </div>
    </div>
  )

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.logo}>Top-R Solutions</div>
          <div>
            <h1 style={styles.h1}>Request for Quotation</h1>
            <p style={styles.subtitle}>
              For: <strong>{rfq.quote_title}</strong>
              {rfq.quote_number && <> · {rfq.quote_number}</>}
              {rfq.client_name && <> · {rfq.client_name}</>}
            </p>
          </div>
        </div>

        <div style={styles.metaRow}>
          <span>Addressed to: <strong>{rfq.supplier_name}</strong></span>
          {rfq.expires_at && (
            <span style={{ color: '#dc2626' }}>
              Respond by: <strong>{new Date(rfq.expires_at).toLocaleDateString()}</strong>
            </span>
          )}
        </div>

        <p style={styles.instruction}>
          Please fill in your unit prices and lead times for each line below.
          Leave any lines you cannot supply blank. Submit once complete.
        </p>

        <form onSubmit={handleSubmit}>
          {/* Global settings */}
          <div style={styles.globalRow}>
            <label style={styles.label}>
              Currency
              <select
                value={globalCurrency}
                onChange={e => setGlobalCurrency(e.target.value)}
                style={styles.select}
              >
                {['EUR', 'GBP', 'USD', 'SEK', 'NOK', 'DKK'].map(c => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
          </div>

          {/* Line items */}
          <div style={{ overflowX: 'auto' }}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>#</th>
                  <th style={{ ...styles.th, textAlign: 'left', minWidth: 200 }}>Description</th>
                  <th style={styles.th}>Qty</th>
                  <th style={styles.th}>Unit</th>
                  <th style={styles.th}>Unit Price ({globalCurrency})</th>
                  <th style={styles.th}>Total</th>
                  <th style={styles.th}>Lead (days)</th>
                  <th style={styles.th}>Availability</th>
                  <th style={styles.th}>Notes</th>
                </tr>
              </thead>
              <tbody>
                {lines.map((line, idx) => {
                  const item = rfq.items[idx] || {}
                  const total = line.unit_price && line.quantity
                    ? (parseFloat(line.unit_price) * parseFloat(line.quantity)).toFixed(2)
                    : '—'
                  return (
                    <tr key={line.line_id} style={idx % 2 === 0 ? styles.rowEven : styles.rowOdd}>
                      <td style={styles.tdCenter}>{line.line_id}</td>
                      <td style={styles.td}>
                        <div style={{ fontWeight: 500 }}>{line.description}</div>
                        {item.supplier_ref && (
                          <div style={{ fontSize: 11, color: '#6b7280' }}>Ref: {item.supplier_ref}</div>
                        )}
                        {item.element_type && (
                          <div style={{ fontSize: 11, color: '#6b7280' }}>{item.element_type}</div>
                        )}
                      </td>
                      <td style={styles.tdCenter}>
                        <input
                          type="number"
                          step="any"
                          value={line.quantity}
                          onChange={e => updateLine(idx, 'quantity', e.target.value)}
                          style={{ ...styles.numInput, width: 64 }}
                        />
                      </td>
                      <td style={styles.tdCenter}>{item.unit || '—'}</td>
                      <td style={styles.tdCenter}>
                        <input
                          type="number"
                          step="any"
                          min="0"
                          placeholder="0.00"
                          value={line.unit_price}
                          onChange={e => updateLine(idx, 'unit_price', e.target.value)}
                          style={{ ...styles.numInput, width: 80 }}
                        />
                      </td>
                      <td style={styles.tdCenter}>{total}</td>
                      <td style={styles.tdCenter}>
                        <input
                          type="number"
                          min="0"
                          placeholder="—"
                          value={line.lead_time_days}
                          onChange={e => updateLine(idx, 'lead_time_days', e.target.value)}
                          style={{ ...styles.numInput, width: 56 }}
                        />
                      </td>
                      <td style={styles.tdCenter}>
                        <select
                          value={line.availability}
                          onChange={e => updateLine(idx, 'availability', e.target.value)}
                          style={{ ...styles.select, fontSize: 12, padding: '2px 4px' }}
                        >
                          <option value="">—</option>
                          {AVAILABILITY_OPTIONS.map(o => <option key={o}>{o}</option>)}
                        </select>
                      </td>
                      <td style={styles.td}>
                        <input
                          type="text"
                          placeholder="optional"
                          value={line.notes}
                          onChange={e => updateLine(idx, 'notes', e.target.value)}
                          style={{ ...styles.textInput, width: '100%', minWidth: 100 }}
                        />
                        <label style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 4, marginTop: 4 }}>
                          <input
                            type="checkbox"
                            checked={line.substitute_offered}
                            onChange={e => updateLine(idx, 'substitute_offered', e.target.checked)}
                          />
                          Substitute
                        </label>
                        {line.substitute_offered && (
                          <input
                            type="text"
                            placeholder="describe substitute"
                            value={line.substitute_description}
                            onChange={e => updateLine(idx, 'substitute_description', e.target.value)}
                            style={{ ...styles.textInput, width: '100%', minWidth: 100, marginTop: 4 }}
                          />
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Grand total preview */}
          {lines.some(l => l.unit_price && l.quantity) && (
            <div style={styles.totalRow}>
              Estimated Total: <strong>
                {globalCurrency}{' '}
                {lines.reduce((sum, l) => {
                  if (l.unit_price && l.quantity) return sum + parseFloat(l.unit_price) * parseFloat(l.quantity)
                  return sum
                }, 0).toFixed(2)}
              </strong>
            </div>
          )}

          {/* Overall notes */}
          <div style={{ marginTop: 20 }}>
            <label style={styles.label}>
              Overall notes / terms / conditions
              <textarea
                rows={3}
                value={globalNotes}
                onChange={e => setGlobalNotes(e.target.value)}
                placeholder="Payment terms, minimum order quantities, delivery conditions…"
                style={styles.textarea}
              />
            </label>
          </div>

          {submitError && (
            <div style={{ ...styles.errorBox, marginTop: 16 }}>{submitError}</div>
          )}

          <div style={{ marginTop: 24, textAlign: 'right' }}>
            <button
              type="submit"
              disabled={submitting}
              style={styles.submitBtn}
            >
              {submitting ? 'Submitting…' : 'Submit pricing'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

const styles = {
  page: {
    minHeight: '100vh',
    background: '#f3f4f6',
    padding: '32px 16px',
    fontFamily: 'system-ui, sans-serif',
  },
  card: {
    maxWidth: 1100,
    margin: '0 auto',
    background: '#fff',
    borderRadius: 12,
    padding: 32,
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  header: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 24,
    marginBottom: 16,
    paddingBottom: 16,
    borderBottom: '2px solid #e5e7eb',
  },
  logo: {
    fontWeight: 700,
    fontSize: 18,
    color: '#1f2937',
    minWidth: 140,
    paddingTop: 4,
  },
  h1: { margin: '0 0 4px', fontSize: 22, color: '#111827' },
  subtitle: { margin: 0, color: '#6b7280', fontSize: 14 },
  metaRow: {
    display: 'flex',
    gap: 24,
    flexWrap: 'wrap',
    fontSize: 14,
    color: '#374151',
    marginBottom: 12,
  },
  instruction: {
    fontSize: 14,
    color: '#6b7280',
    background: '#f9fafb',
    borderRadius: 6,
    padding: '10px 14px',
    marginBottom: 20,
  },
  globalRow: {
    display: 'flex',
    gap: 16,
    marginBottom: 16,
  },
  label: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    fontSize: 13,
    fontWeight: 500,
    color: '#374151',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 13,
  },
  th: {
    padding: '8px 10px',
    background: '#f9fafb',
    borderBottom: '1px solid #e5e7eb',
    fontWeight: 600,
    color: '#374151',
    textAlign: 'center',
    whiteSpace: 'nowrap',
  },
  td: { padding: '8px 10px', borderBottom: '1px solid #f3f4f6', verticalAlign: 'top' },
  tdCenter: { padding: '8px 10px', borderBottom: '1px solid #f3f4f6', textAlign: 'center', verticalAlign: 'top' },
  rowEven: { background: '#fff' },
  rowOdd: { background: '#fafafa' },
  numInput: {
    border: '1px solid #d1d5db',
    borderRadius: 4,
    padding: '4px 6px',
    textAlign: 'right',
    fontSize: 13,
  },
  textInput: {
    border: '1px solid #d1d5db',
    borderRadius: 4,
    padding: '4px 6px',
    fontSize: 12,
  },
  select: {
    border: '1px solid #d1d5db',
    borderRadius: 4,
    padding: '4px 8px',
    fontSize: 13,
    background: '#fff',
  },
  textarea: {
    width: '100%',
    border: '1px solid #d1d5db',
    borderRadius: 6,
    padding: '8px 10px',
    fontSize: 13,
    resize: 'vertical',
    marginTop: 4,
    boxSizing: 'border-box',
  },
  totalRow: {
    textAlign: 'right',
    padding: '12px 0',
    fontSize: 15,
    color: '#1f2937',
    borderTop: '2px solid #e5e7eb',
    marginTop: 4,
  },
  submitBtn: {
    background: '#2563eb',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    padding: '12px 32px',
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
  },
  errorBox: {
    background: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: 6,
    padding: '10px 14px',
    color: '#dc2626',
    fontSize: 13,
  },
  successBox: {
    background: '#ecfdf5',
    border: '1px solid #6ee7b7',
    borderRadius: 10,
    padding: 32,
    textAlign: 'center',
  },
}
