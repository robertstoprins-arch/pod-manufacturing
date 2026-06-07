import { useState, useEffect } from 'react'
import { useApi } from '../api/useApi'
import { OFFICE_POD } from '../config/productTemplates.js'

// Map a questionnaire field value to its human-readable option label.
function fieldOptionLabel(key, value) {
  if (value == null || value === '') return null
  const field = OFFICE_POD.fields.find(f => f.key === key)
  if (!field?.options) return String(value)
  const opt = field.options.find(o => o.value === value)
  return opt?.label ?? String(value)
}

// ── Status config ──────────────────────────────────────────────────────────────

const STATUS_CFG = {
  draft:          { cls: 'bg-gray-100 text-gray-500 border-gray-200',    dot: 'bg-gray-400',   label: 'Draft' },
  sent:           { cls: 'bg-blue-50 text-blue-700 border-blue-200',     dot: 'bg-blue-500',   label: 'Sent' },
  follow_up_due:  { cls: 'bg-amber-50 text-amber-700 border-amber-200',  dot: 'bg-amber-400',  label: 'Follow-Up Due' },
  accepted:       { cls: 'bg-green-50 text-green-700 border-green-200',  dot: 'bg-green-500',  label: 'Accepted' },
  lost:           { cls: 'bg-red-50 text-red-600 border-red-200',        dot: 'bg-red-400',    label: 'Lost' },
  expired:        { cls: 'bg-orange-50 text-orange-600 border-orange-200', dot: 'bg-orange-400', label: 'Expired' },
  converted:      { cls: 'bg-teal-50 text-teal-700 border-teal-200',     dot: 'bg-teal-500',   label: 'Converted' },
}

function StatusBadge({ status }) {
  const cfg = STATUS_CFG[status] ?? STATUS_CFG.draft
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border font-medium ${cfg.cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  )
}

// ── Shared modal shell ─────────────────────────────────────────────────────────

function Modal({ title, subtitle, onClose, children, footer }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden flex flex-col max-h-[90vh]">
        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <div>
            <div className="font-semibold text-gray-900">{title}</div>
            {subtitle && <div className="text-xs text-gray-400 mt-0.5">{subtitle}</div>}
          </div>
          <button type="button" onClick={onClose} className="text-gray-300 hover:text-gray-600 text-xl leading-none mt-0.5">✕</button>
        </div>
        <div className="px-6 py-4 space-y-3 overflow-y-auto flex-1">{children}</div>
        {footer && <div className="px-6 py-3 border-t border-gray-100 flex justify-end gap-2 shrink-0">{footer}</div>}
      </div>
    </div>
  )
}

function Field({ label, value, onChange, placeholder = '', type = 'text', textarea = false }) {
  const cls = 'w-full bg-white border border-gray-200 rounded px-2.5 py-1.5 text-sm text-gray-900 focus:outline-none focus:border-gray-500 transition-colors'
  return (
    <div>
      <label className="block text-[11px] font-medium text-gray-500 mb-1">{label}</label>
      {textarea
        ? <textarea value={value ?? ''} placeholder={placeholder} onChange={e => onChange(e.target.value)} rows={3} className={cls + ' resize-none'} />
        : <input type={type} value={value ?? ''} placeholder={placeholder} onChange={e => onChange(e.target.value)} className={cls} />
      }
    </div>
  )
}

function SelectField({ label, value, onChange, options }) {
  return (
    <div>
      <label className="block text-[11px] font-medium text-gray-500 mb-1">{label}</label>
      <select value={value ?? ''} onChange={e => onChange(e.target.value)}
        className="w-full bg-white border border-gray-200 rounded px-2.5 py-1.5 text-sm text-gray-900 focus:outline-none focus:border-gray-500">
        <option value="">— None —</option>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  )
}

function Btn({ onClick, children, variant = 'primary', disabled = false, small = false }) {
  const base = `${small ? 'px-2.5 py-1 text-xs' : 'px-3 py-1.5 text-sm'} rounded font-medium cursor-pointer transition-all active:scale-95 active:brightness-90 disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100`
  const variants = {
    primary:   'bg-gray-900 text-white hover:bg-gray-700 shadow-sm hover:shadow',
    secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-200 hover:border-gray-300',
    danger:    'bg-red-50 text-red-600 hover:bg-red-100 border border-red-200',
    success:   'bg-green-600 text-white hover:bg-green-700 shadow-sm hover:shadow',
  }
  return <button type="button" className={`${base} ${variants[variant]}`} onClick={onClick} disabled={disabled}>{children}</button>
}

// ── Summary cards ──────────────────────────────────────────────────────────────

function SummaryCards({ quotes }) {
  const count = (s) => quotes.filter(q => q.status === s).length
  const followUp = quotes.filter(q => q.status === 'follow_up_due').length
  const cards = [
    { label: 'Draft',          value: count('draft'),     color: 'text-gray-500' },
    { label: 'Sent',           value: count('sent'),      color: 'text-blue-600' },
    { label: 'Follow-Up Due',  value: followUp,           color: followUp > 0 ? 'text-amber-600' : 'text-gray-400' },
    { label: 'Accepted',       value: count('accepted'),  color: 'text-green-600' },
    { label: 'Lost',           value: count('lost'),      color: 'text-red-500' },
  ]
  return (
    <div className="grid grid-cols-5 gap-3 mb-6">
      {cards.map(c => (
        <div key={c.label} className="bg-white rounded-lg border border-gray-100 px-4 py-3">
          <div className={`text-2xl font-bold ${c.color}`}>{c.value}</div>
          <div className="text-[11px] text-gray-400 mt-0.5">{c.label}</div>
        </div>
      ))}
    </div>
  )
}

// ── New quote form ─────────────────────────────────────────────────────────────

const EMPTY_FORM = {
  title: '', client_id: '', lead_source: '', currency: 'EUR',
  total_ex_vat: '', total_inc_vat: '', deposit_percent: '',
  expires_at: '', notes: '', quote_number: '',
}

function NewQuoteModal({ onClose, onCreated, clients }) {
  const api = useApi()
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')

  const set = (k) => (v) => setForm(f => ({ ...f, [k]: v }))

  async function handleSave() {
    if (!form.title.trim()) { setErr('Title is required'); return }
    setSaving(true)
    try {
      const body = {
        title: form.title,
        client_id: form.client_id || null,
        quote_number: form.quote_number || null,
        lead_source: form.lead_source || null,
        currency: form.currency || 'EUR',
        total_ex_vat: form.total_ex_vat ? parseFloat(form.total_ex_vat) : null,
        total_inc_vat: form.total_inc_vat ? parseFloat(form.total_inc_vat) : null,
        deposit_percent: form.deposit_percent ? parseFloat(form.deposit_percent) : null,
        expires_at: form.expires_at || null,
        notes: form.notes || null,
      }
      const q = await api('/quotes', { method: 'POST', body: JSON.stringify(body) })
      onCreated(q)
    } catch (e) {
      setErr(e.message ?? 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const clientOpts = clients.map(c => ({ value: c.id, label: c.name + (c.company_name ? ` — ${c.company_name}` : '') }))

  return (
    <Modal title="New Quote" onClose={onClose} footer={
      <>
        {err && <span className="text-xs text-red-500 mr-auto">{err}</span>}
        <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
        <Btn onClick={handleSave} disabled={saving}>{saving ? 'Saving…' : 'Create Quote'}</Btn>
      </>
    }>
      <Field label="Title *" value={form.title} onChange={set('title')} placeholder="e.g. Garden Pod — Smith Residence" />
      <Field label="Quote Number" value={form.quote_number} onChange={set('quote_number')} placeholder="e.g. Q-2026-001" />
      <SelectField label="Client" value={form.client_id} onChange={set('client_id')} options={clientOpts} />
      <Field label="Lead Source" value={form.lead_source} onChange={set('lead_source')} placeholder="Website / referral / etc." />
      <div className="grid grid-cols-2 gap-3">
        <Field label="Total excl. VAT" value={form.total_ex_vat} onChange={set('total_ex_vat')} type="number" placeholder="0.00" />
        <Field label="Total incl. VAT" value={form.total_inc_vat} onChange={set('total_inc_vat')} type="number" placeholder="0.00" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Currency" value={form.currency} onChange={set('currency')} placeholder="EUR" />
        <Field label="Deposit %" value={form.deposit_percent} onChange={set('deposit_percent')} type="number" placeholder="30" />
      </div>
      <Field label="Expires" value={form.expires_at} onChange={set('expires_at')} type="date" />
      <Field label="Notes (internal)" value={form.notes} onChange={set('notes')} textarea />
    </Modal>
  )
}

// ── Quote detail panel ─────────────────────────────────────────────────────────

const STATUS_OPTS = [
  { value: 'draft',         label: 'Draft' },
  { value: 'sent',          label: 'Sent' },
  { value: 'follow_up_due', label: 'Follow-Up Due' },
  { value: 'accepted',      label: 'Accepted' },
  { value: 'lost',          label: 'Lost' },
  { value: 'expired',       label: 'Expired' },
  { value: 'converted',     label: 'Converted' },
]

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function QuoteDetailModal({ quote: initialQuote, clients, onClose, onUpdated }) {
  const api = useApi()
  const [quote, setQuote] = useState(initialQuote)
  const [events, setEvents] = useState([])
  const [tab, setTab] = useState('details')
  const [saving, setSaving] = useState(false)
  const [newStatus, setNewStatus] = useState(initialQuote.status)
  const [lostReason, setLostReason] = useState(initialQuote.lost_reason ?? '')
  const [statusNote, setStatusNote] = useState('')
  const [manualNote, setManualNote] = useState('')
  const [err, setErr] = useState('')
  const [rfq, setRfq] = useState(null)
  const [rfqLoading, setRfqLoading] = useState(false)
  const [rfqErr, setRfqErr] = useState('')
  const [rfqSuppliers, setRfqSuppliers] = useState([])
  const [showSendModal, setShowSendModal] = useState(false)
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [emailPreview, setEmailPreview] = useState(null)
  const [emailLoading, setEmailLoading] = useState(false)
  const [rfqResponses, setRfqResponses] = useState(null)
  const [responsesLoading, setResponsesLoading] = useState(false)
  const [clientLink, setClientLink] = useState(quote.client_token ? `${window.location.origin}/quote-view/${quote.client_token}` : null)
  const [generatingLink, setGeneratingLink] = useState(false)
  const [paymentUpdating, setPaymentUpdating] = useState(false)
  const [invoiceDownloading, setInvoiceDownloading] = useState(false)
  const [rfqView, setRfqView] = useState('bom')   // 'bom' | 'comparison'
  const [comparison, setComparison] = useState(null)
  const [compLoading, setCompLoading] = useState(false)
  const [compErr, setCompErr] = useState('')

  useEffect(() => {
    api(`/quotes/${quote.id}/events`).then(setEvents).catch(() => {})
  }, [quote.id])

  async function handleStatusUpdate() {
    setSaving(true)
    setErr('')
    try {
      const updated = await api(`/quotes/${quote.id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus, note: statusNote || null, lost_reason: lostReason || null }),
      })
      setQuote(updated)
      onUpdated(updated)
      const evs = await api(`/quotes/${quote.id}/events`)
      setEvents(evs)
      setStatusNote('')
    } catch (e) {
      setErr(e.message ?? 'Update failed')
    } finally {
      setSaving(false)
    }
  }

  async function handleAddNote() {
    if (!manualNote.trim()) return
    setSaving(true)
    try {
      await api(`/quotes/${quote.id}/events`, {
        method: 'POST',
        body: JSON.stringify({ event_type: 'note', note: manualNote }),
      })
      setManualNote('')
      const evs = await api(`/quotes/${quote.id}/events`)
      setEvents(evs)
    } catch (e) {
      setErr(e.message ?? 'Failed to add note')
    } finally {
      setSaving(false)
    }
  }

  const clientName = clients.find(c => c.id === quote.client_id)?.name ?? quote.client_name ?? '—'

  async function handleMarkDepositReceived() {
    setPaymentUpdating(true)
    try {
      const updated = await api(`/quotes/${quote.id}/payment`, {
        method: 'PATCH',
        body: JSON.stringify({ payment_status: 'deposit_received' }),
      })
      setQuote(updated)
      onUpdated(updated)
      const evs = await api(`/quotes/${quote.id}/events`)
      setEvents(evs)
    } catch (e) {
      setErr(e.message ?? 'Failed to update payment status')
    } finally {
      setPaymentUpdating(false)
    }
  }

  async function downloadDepositInvoice() {
    if (invoiceDownloading) return
    setInvoiceDownloading(true)
    try {
      const blob = await api(`/quotes/${quote.id}/deposit-invoice.pdf`, { _blob: true })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `deposit-invoice-${quote.quote_number || quote.id}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert(`Failed to download invoice: ${e.message}`)
    } finally {
      setInvoiceDownloading(false)
    }
  }

  async function loadRfq() {
    setRfqLoading(true)
    setRfqErr('')
    try {
      const [data, sups] = await Promise.all([
        api(`/quotes/${quote.id}/rfq`),
        rfqSuppliers.length ? Promise.resolve(rfqSuppliers) : api('/suppliers'),
      ])
      setRfq(data)
      if (sups !== rfqSuppliers) setRfqSuppliers(sups)
    } catch (e) {
      setRfqErr(e.message ?? 'Failed to generate RFQ')
    } finally {
      setRfqLoading(false)
    }
  }

  function downloadRfq() {
    if (!rfq) return
    const blob = new Blob([JSON.stringify(rfq, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${rfq.rfq_id || 'rfq'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function generateClientLink() {
    setGeneratingLink(true)
    try {
      const data = await api(`/quotes/${quote.id}/client-link`, {
        method: 'POST',
        body: JSON.stringify({ expires_days: 30 }),
      })
      const link = `${window.location.origin}/quote-view/${data.token}`
      setClientLink(link)
      setQuote(q => ({ ...q, client_token: data.token }))
      onUpdated({ ...quote, client_token: data.token })
    } catch (e) {
      setErr(e.message ?? 'Failed to generate link')
    } finally {
      setGeneratingLink(false)
    }
  }

  async function loadResponses() {
    setResponsesLoading(true)
    try {
      const data = await api(`/quotes/${quote.id}/rfq/responses`)
      setRfqResponses(data)
    } catch (_) {}
    finally { setResponsesLoading(false) }
  }

  async function loadComparison() {
    setCompLoading(true)
    setCompErr('')
    try {
      const data = await api(`/quotes/${quote.id}/rfq/comparison`)
      setComparison(data)
    } catch (e) {
      setCompErr(e.message ?? 'Failed to load comparison')
    } finally {
      setCompLoading(false)
    }
  }

  async function openEmailModal() {
    setEmailLoading(true)
    setErr('')
    try {
      const data = await api(`/quotes/${quote.id}/email-preview`)
      setEmailPreview(data)
      setShowEmailModal(true)
    } catch (e) {
      setErr(e.message ?? 'Failed to load email preview')
    } finally {
      setEmailLoading(false)
    }
  }

  async function handleSendEmail(subject, body, followUpDays) {
    try {
      const result = await api(`/quotes/${quote.id}/send-to-client`, {
        method: 'POST',
        body: JSON.stringify({ subject, body, follow_up_days: followUpDays }),
      })
      setQuote(q => ({ ...q, status: result.status, sent_at: result.sent_at, client_token: result.client_portal_url.split('/').pop() }))
      onUpdated({ ...quote, status: result.status, sent_at: result.sent_at })
      const evs = await api(`/quotes/${quote.id}/events`)
      setEvents(evs)
      setShowEmailModal(false)
      return result
    } catch (e) {
      throw e
    }
  }

  const tabs = ['details', 'status', 'events', ...(quote.pod_spec_id ? ['rfq'] : [])]

  return (
    <Modal
      title={quote.title}
      subtitle={`${quote.quote_number ?? 'No number'} · ${clientName}`}
      onClose={onClose}
    >
      {/* Tabs */}
      <div className="flex gap-1 -mt-1 mb-2 border-b border-gray-100 pb-2">
        {tabs.map(t => {
          const errorCount = t === 'rfq' && rfq
            ? (rfq.spec_summary?.warnings?.filter(w => w.severity === 'error').length ?? 0)
            : 0
          return (
            <button key={t} onClick={() => { setTab(t); if (t === 'rfq' && !rfq) loadRfq() }}
              className={`relative px-3 py-1 text-xs rounded font-medium uppercase tracking-wide transition-colors ${tab === t ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-800'}`}>
              {t}
              {errorCount > 0 && (
                <span className="ml-1 inline-flex items-center justify-center w-4 h-4 bg-red-500 text-white text-[9px] rounded-full font-bold">{errorCount}</span>
              )}
            </button>
          )
        })}
      </div>

      {tab === 'details' && (
        <div className="space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-x-6 gap-y-2">
            <InfoRow label="Status"><StatusBadge status={quote.status} /></InfoRow>
            <InfoRow label="Revision">{quote.revision}</InfoRow>
            <InfoRow label="Lead Source">{quote.lead_source ?? '—'}</InfoRow>
            <InfoRow label="Currency">{quote.currency}</InfoRow>
            <InfoRow label="Total excl. VAT">{quote.total_ex_vat != null ? `${quote.currency} ${Number(quote.total_ex_vat).toLocaleString()}` : '—'}</InfoRow>
            <InfoRow label="Total incl. VAT">{quote.total_inc_vat != null ? `${quote.currency} ${Number(quote.total_inc_vat).toLocaleString()}` : '—'}</InfoRow>
            <InfoRow label="Deposit %">{quote.deposit_percent != null ? `${quote.deposit_percent}%` : '—'}</InfoRow>
            <InfoRow label="Sent">{formatDate(quote.sent_at)}</InfoRow>
            <InfoRow label="Follow-Up">{formatDate(quote.follow_up_at)}</InfoRow>
            <InfoRow label="Expires">{formatDate(quote.expires_at)}</InfoRow>
            <InfoRow label="Accepted">{formatDate(quote.accepted_at)}</InfoRow>
            <InfoRow label="Lost">{formatDate(quote.lost_at)}</InfoRow>
            {quote.lost_reason && <InfoRow label="Lost Reason">{quote.lost_reason}</InfoRow>}
          </div>
          {quote.notes && (
            <div className="mt-2 bg-gray-50 rounded p-3 text-xs text-gray-600 whitespace-pre-wrap">{quote.notes}</div>
          )}

          {/* Enquiry Details — shown for quotes created via the web enquiry form */}
          {quote.spec_snapshot?.questionnaire_answers && (() => {
            const qa = quote.spec_snapshot.questionnaire_answers
            const pe = quote.spec_snapshot.pricing_estimate

            const row = (label, val) => (val != null && val !== '') ? { label, value: String(val) } : null
            const m   = (v, unit) => v != null && v !== '' ? `${v} ${unit}` : null

            const doorLabel = qa.door_count != null
              ? `${qa.door_count}${qa.door_type ? ` × ${fieldOptionLabel('door_type', qa.door_type)}` : ''}`
              : null
            const windowLabel = qa.window_count != null
              ? `${qa.window_count}${qa.window_type ? ` × ${fieldOptionLabel('window_type', qa.window_type)}` : ''}`
              : null

            const groups = [
              { title: 'Pod', rows: [
                row('Type',     fieldOptionLabel('pod_type', qa.pod_type)),
                row('Quantity', qa.quantity),
              ]},
              { title: 'Dimensions', rows: [
                row('Width',   m(qa.width_m,  'm')),
                row('Length',  m(qa.length_m, 'm')),
                row('Height',  m(qa.height_m, 'm')),
              ]},
              { title: 'Openings', rows: [
                row('Doors',      doorLabel),
                row('Windows',    windowLabel),
                row('Rooflights', qa.rooflight_count || null),
              ]},
              { title: 'Finishes', rows: [
                row('External', fieldOptionLabel('external_finish',        qa.external_finish)),
                row('Internal', fieldOptionLabel('internal_finish_package', qa.internal_finish_package)),
              ]},
              { title: 'Services', rows: [
                row('Heating',     fieldOptionLabel('heating_option',     qa.heating_option)),
                row('Ventilation', fieldOptionLabel('ventilation_option', qa.ventilation_option)),
                row('Electrical',  fieldOptionLabel('electrical_package', qa.electrical_package)),
              ]},
              { title: 'Site', rows: [
                row('Foundation', fieldOptionLabel('foundation_option',       qa.foundation_option)),
                row('Delivery',   fieldOptionLabel('delivery_install_option', qa.delivery_install_option)),
                row('Location',   qa.location),
                row('Use',        fieldOptionLabel('intended_use', qa.intended_use)),
                row('Timeline',   fieldOptionLabel('timeline',     qa.timeline)),
              ]},
            ].map(g => ({ ...g, rows: g.rows.filter(Boolean) })).filter(g => g.rows.length > 0)

            if (!groups.length) return null
            return (
              <div className="mt-3 border border-blue-100 bg-blue-50 rounded-lg overflow-hidden">
                <div className="px-3 py-2 bg-blue-50 border-b border-blue-100">
                  <div className="text-[10px] font-semibold text-blue-400 uppercase tracking-wide">Enquiry Details</div>
                </div>
                <div className="p-3 space-y-3">
                  {groups.map(g => (
                    <div key={g.title}>
                      <div className="text-[10px] font-semibold text-blue-300 uppercase tracking-wide mb-1">{g.title}</div>
                      <div className="grid grid-cols-2 gap-x-6 gap-y-0.5">
                        {g.rows.map(r => (
                          <InfoRow key={r.label} label={r.label}>{r.value}</InfoRow>
                        ))}
                      </div>
                    </div>
                  ))}
                  {qa.notes && (
                    <div className="text-[11px] text-gray-500 italic whitespace-pre-wrap border-t border-blue-100 pt-2 mt-1">{qa.notes}</div>
                  )}
                  {pe?.status === 'estimated' && (
                    <div className="border-t border-blue-100 pt-2 mt-1">
                      <div className="flex items-baseline justify-between mb-1">
                        <div className="text-[10px] font-semibold text-blue-300 uppercase tracking-wide">Indicative Estimate</div>
                        <div className="text-xs font-semibold text-gray-700">
                          €{Number(pe.total_ex_vat).toLocaleString()} ex VAT
                          <span className="text-[10px] text-gray-400 font-normal ml-1">(€{Number(pe.total_inc_vat).toLocaleString()} inc)</span>
                        </div>
                      </div>
                      <div className="text-[10px] text-gray-400 mb-2">{pe.floor_area_m2} m² · qty {pe.quantity}</div>
                      {pe.provisional_breakdown?.length > 0 && (() => {
                        const byCategory = pe.provisional_breakdown.reduce((acc, item) => {
                          if (!acc[item.category]) acc[item.category] = []
                          acc[item.category].push(item)
                          return acc
                        }, {})
                        const catLabels = {
                          structure: 'Structure', external_finish: 'External Finish',
                          internal_finish: 'Internal Finish', openings: 'Openings',
                          services: 'Services', foundation: 'Foundation', delivery: 'Delivery',
                        }
                        return (
                          <div className="rounded border border-blue-100 overflow-hidden mb-2">
                            <table className="w-full text-[10px]">
                              <thead>
                                <tr className="bg-blue-50 text-blue-400 uppercase tracking-wide">
                                  <th className="px-2 py-1 text-left font-semibold">Item</th>
                                  <th className="px-2 py-1 text-right font-semibold w-16">Qty</th>
                                  <th className="px-2 py-1 text-right font-semibold w-10">Unit</th>
                                  <th className="px-2 py-1 text-right font-semibold w-20">Subtotal</th>
                                </tr>
                              </thead>
                              <tbody>
                                {Object.entries(byCategory).map(([cat, items]) => (
                                  <>
                                    <tr key={`cat-${cat}`} className="bg-blue-50/50">
                                      <td colSpan={4} className="px-2 py-0.5 text-blue-300 font-semibold uppercase tracking-wide">{catLabels[cat] ?? cat}</td>
                                    </tr>
                                    {items.map((item, i) => (
                                      <tr key={`${cat}-${i}`} className="border-t border-blue-50">
                                        <td className="px-2 py-1 text-gray-600">{item.description}</td>
                                        <td className="px-2 py-1 text-right text-gray-500">{item.qty}</td>
                                        <td className="px-2 py-1 text-right text-gray-400">{item.unit}</td>
                                        <td className="px-2 py-1 text-right text-gray-700 font-medium">€{Number(item.subtotal_ex_vat).toLocaleString()}</td>
                                      </tr>
                                    ))}
                                  </>
                                ))}
                                <tr className="border-t-2 border-blue-200 bg-blue-50">
                                  <td colSpan={3} className="px-2 py-1 font-semibold text-gray-700">Total ex VAT</td>
                                  <td className="px-2 py-1 text-right font-semibold text-gray-900">€{Number(pe.total_ex_vat).toLocaleString()}</td>
                                </tr>
                              </tbody>
                            </table>
                          </div>
                        )
                      })()}
                      {!pe.provisional_breakdown?.length && pe.addons_applied?.length > 0 && (
                        <div className="text-[11px] text-blue-400 mt-1 mb-2">{pe.addons_applied.join(' · ')}</div>
                      )}
                      <div className="text-[10px] text-gray-400 italic">{pe.disclaimer}</div>
                    </div>
                  )}
                </div>
              </div>
            )
          })()}

          {/* Deposit & payment — shown when quote has pricing */}
          {(quote.deposit_amount != null || quote.deposit_percent != null || quote.total_ex_vat != null) && (
            <div className="mt-3 border border-gray-100 rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-gray-700">Deposit & Payment</div>
                  {quote.deposit_percent != null && (
                    <div className="text-[11px] text-gray-400 mt-0.5">
                      {quote.deposit_percent}% deposit ·{' '}
                      {quote.deposit_amount != null
                        ? `${quote.currency} ${Number(quote.deposit_amount).toLocaleString()}`
                        : quote.total_ex_vat != null
                          ? `${quote.currency} ${(Number(quote.total_ex_vat) * Number(quote.deposit_percent) / 100).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                          : '—'}
                    </div>
                  )}
                </div>
                <div className="flex gap-2 items-center">
                  {quote.payment_status && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                      quote.payment_status === 'deposit_received' ? 'bg-green-50 text-green-700'
                      : quote.payment_status === 'paid_in_full' ? 'bg-teal-50 text-teal-700'
                      : quote.payment_status === 'overdue' ? 'bg-red-50 text-red-600'
                      : 'bg-amber-50 text-amber-700'
                    }`}>
                      {quote.payment_status === 'deposit_received' ? 'Deposit Received'
                        : quote.payment_status === 'paid_in_full' ? 'Paid in Full'
                        : quote.payment_status === 'overdue' ? 'Overdue'
                        : 'Awaiting Deposit'}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex gap-2 flex-wrap">
                <Btn small variant="secondary" onClick={downloadDepositInvoice} disabled={invoiceDownloading}>
                  {invoiceDownloading ? 'Downloading…' : 'Download Invoice PDF'}
                </Btn>
                {quote.payment_status !== 'deposit_received' && quote.payment_status !== 'paid_in_full' && (
                  <Btn small onClick={handleMarkDepositReceived} disabled={paymentUpdating}>
                    {paymentUpdating ? 'Updating…' : 'Mark Deposit Received'}
                  </Btn>
                )}
              </div>
            </div>
          )}

          {/* Client portal */}
          <div className="mt-3 border border-gray-100 rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold text-gray-700">Client Quote Portal</div>
                <div className="text-[11px] text-gray-400 mt-0.5">Private link for client to view and accept this quote</div>
              </div>
              <div className="flex gap-2">
                <Btn small onClick={generateClientLink} disabled={generatingLink}>
                  {generatingLink ? 'Generating…' : clientLink ? 'Regenerate Link' : 'Generate Link'}
                </Btn>
                {quote.client_email && (
                  <Btn small variant="success" onClick={openEmailModal} disabled={emailLoading}>
                    {emailLoading ? 'Loading…' : 'Send to Client'}
                  </Btn>
                )}
              </div>
            </div>
            {clientLink && (
              <div className="flex items-center gap-2">
                <code className="text-[11px] text-blue-600 bg-blue-50 rounded px-2 py-1 flex-1 truncate">{clientLink}</code>
                <Btn small variant="secondary" onClick={() => navigator.clipboard.writeText(clientLink)}>Copy</Btn>
              </div>
            )}
            {quote.client_viewed_at && (
              <div className="text-[11px] text-gray-500">
                Viewed: {formatDate(quote.client_viewed_at)}
                {quote.client_responded_at && (
                  <span> · Response: <span className={`font-medium ${quote.client_response === 'accepted' ? 'text-green-600' : quote.client_response === 'declined' ? 'text-red-500' : 'text-amber-600'}`}>
                    {quote.client_response === 'accepted' ? 'Accepted' : quote.client_response === 'declined' ? 'Declined' : 'Changes Requested'}
                  </span></span>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'status' && (
        <div className="space-y-3">
          <SelectField label="New Status" value={newStatus} onChange={setNewStatus} options={STATUS_OPTS} />
          {newStatus === 'lost' && (
            <Field label="Lost Reason" value={lostReason} onChange={setLostReason} placeholder="Price / timing / competitor / etc." />
          )}
          <Field label="Note" value={statusNote} onChange={setStatusNote} textarea placeholder="Optional — what happened?" />
          {err && <p className="text-xs text-red-500">{err}</p>}
          <div className="flex justify-end">
            <Btn onClick={handleStatusUpdate} disabled={saving || newStatus === quote.status}>
              {saving ? 'Saving…' : 'Update Status'}
            </Btn>
          </div>
        </div>
      )}

      {tab === 'events' && (
        <div className="space-y-3">
          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {events.length === 0 && <p className="text-xs text-gray-400">No events yet.</p>}
            {[...events].reverse().map(ev => (
              <div key={ev.id} className="bg-gray-50 rounded p-3">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-xs font-medium text-gray-700 capitalize">{ev.event_type.replace(/_/g, ' ')}</span>
                  <span className="text-[10px] text-gray-400">{formatDate(ev.created_at)}</span>
                </div>
                {(ev.old_status || ev.new_status) && (
                  <div className="text-[10px] text-gray-400 mb-1">
                    {ev.old_status && <StatusBadge status={ev.old_status} />}
                    {ev.old_status && ev.new_status && <span className="mx-1">→</span>}
                    {ev.new_status && <StatusBadge status={ev.new_status} />}
                  </div>
                )}
                {ev.note && <p className="text-xs text-gray-600">{ev.note}</p>}
              </div>
            ))}
          </div>
          <div className="border-t border-gray-100 pt-3 space-y-2">
            <Field label="Add Note" value={manualNote} onChange={setManualNote} textarea placeholder="Log a call, follow-up, meeting…" />
            <div className="flex justify-end">
              <Btn onClick={handleAddNote} disabled={saving || !manualNote.trim()}>Add Note</Btn>
            </div>
          </div>
        </div>
      )}

      {tab === 'rfq' && (
        <div className="space-y-3">
          {rfqLoading && <p className="text-xs text-gray-400 text-center py-8">Generating RFQ package…</p>}
          {rfqErr && <p className="text-xs text-red-500">{rfqErr}</p>}
          {rfq && !rfqLoading && (
            <>
              {/* Summary bar */}
              <div className="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-3">
                <div>
                  <div className="flex items-center gap-2">
                    <div className="text-xs font-semibold text-gray-700">{rfq.rfq_id}</div>
                    {rfq.rfq_readiness === 'Ready' && (
                      <span className="text-[10px] bg-green-100 text-green-700 border border-green-200 px-1.5 py-0.5 rounded font-medium">Ready</span>
                    )}
                    {rfq.rfq_readiness === 'Needs Attention' && (
                      <span className="text-[10px] bg-amber-100 text-amber-700 border border-amber-200 px-1.5 py-0.5 rounded font-medium">Needs Attention</span>
                    )}
                    {rfq.rfq_readiness === 'Blocked' && (
                      <span className="text-[10px] bg-red-100 text-red-700 border border-red-200 px-1.5 py-0.5 rounded font-medium">Blocked</span>
                    )}
                  </div>
                  <div className="text-[11px] text-gray-400 mt-0.5">
                    {rfq.total_items} items · {rfq.total_suppliers} supplier{rfq.total_suppliers !== 1 ? 's' : ''}
                    {rfq.spec_summary?.estimated_total != null && (
                      <span> · est. {rfq.project.currency} {Number(rfq.spec_summary.estimated_total).toLocaleString()}</span>
                    )}
                    {rfq.spec_summary?.has_estimates && <span className="text-amber-500"> (inc. estimates)</span>}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Btn small variant="secondary" onClick={() => navigator.clipboard.writeText(JSON.stringify(rfq, null, 2))}>Copy JSON</Btn>
                  <Btn small variant="secondary" onClick={downloadRfq}>Download</Btn>
                  <Btn small onClick={() => {
                    const hasErrors = rfq.spec_summary?.warnings?.some(w => w.severity === 'error')
                    if (hasErrors) {
                      if (!window.confirm('This RFQ has error-level warnings (missing prices or evidence). Send anyway?')) return
                    }
                    setShowSendModal(true)
                  }}>Send to Suppliers</Btn>
                </div>
              </div>

              {/* BOM / Comparison toggle */}
              <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
                {[['bom', 'BOM'], ['comparison', 'Compare Responses']].map(([v, label]) => (
                  <button
                    key={v}
                    onClick={() => { setRfqView(v); if (v === 'comparison' && !comparison) loadComparison() }}
                    className={`text-xs px-3 py-1 rounded-md transition-colors ${rfqView === v ? 'bg-white text-gray-900 shadow-sm font-medium' : 'text-gray-500 hover:text-gray-700'}`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {/* BOM view */}
              {rfqView === 'bom' && (
                <>
                  {/* Structured warnings — grouped by severity */}
                  {rfq.spec_summary?.warnings?.length > 0 && (() => {
                    const ws = rfq.spec_summary.warnings
                    const errors   = ws.filter(w => w.severity === 'error')
                    const warnings = ws.filter(w => w.severity === 'warning')
                    const infos    = ws.filter(w => w.severity === 'info')
                    return (
                      <div className="space-y-2">
                        {errors.length > 0 && (
                          <div className="bg-red-50 border border-red-200 rounded p-3 space-y-1">
                            <p className="text-[11px] font-semibold text-red-700">{errors.length} error{errors.length > 1 ? 's' : ''} — must fix before sending</p>
                            {errors.map((w, i) => (
                              <p key={i} className="text-[11px] text-red-600">· {w.message}</p>
                            ))}
                          </div>
                        )}
                        {warnings.length > 0 && (
                          <div className="bg-amber-50 border border-amber-200 rounded p-3 space-y-1">
                            <p className="text-[11px] font-semibold text-amber-700">{warnings.length} warning{warnings.length > 1 ? 's' : ''}</p>
                            {warnings.map((w, i) => (
                              <p key={i} className="text-[11px] text-amber-600">· {w.message}</p>
                            ))}
                          </div>
                        )}
                        {infos.length > 0 && (
                          <details className="group">
                            <summary className="text-[11px] text-gray-400 cursor-pointer hover:text-gray-600 select-none">{infos.length} info note{infos.length > 1 ? 's' : ''} (expand)</summary>
                            <div className="mt-1 bg-gray-50 border border-gray-100 rounded p-3 space-y-1">
                              {infos.map((w, i) => (
                                <p key={i} className="text-[11px] text-gray-500">· {w.message}</p>
                              ))}
                            </div>
                          </details>
                        )}
                      </div>
                    )
                  })()}

                  {/* No items banner */}
                  {rfq.total_items === 0 && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-xs text-amber-800 space-y-1.5">
                      <p className="font-semibold">RFQ package is empty</p>
                      <p>This can happen for two reasons:</p>
                      <ul className="list-disc list-inside space-y-1 text-amber-700">
                        <li><span className="font-medium">Pod spec has no geometry</span> — open the pod spec and set dimensions so quantities can be calculated.</li>
                        <li><span className="font-medium">Materials have no preferred supplier</span> — go to <span className="font-semibold">Material Library</span>, open any material, and set its <span className="font-semibold">Preferred Supplier</span>.</li>
                      </ul>
                    </div>
                  )}

                  {/* Estimates note */}
                  {rfq.spec_summary?.has_estimates && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 text-xs text-amber-700">
                      Total includes <span className="font-semibold">estimated rates</span> (amber est. badge) — lines without a confirmed supplier price. Add supplier prices or confirm quotes to clear these.
                    </div>
                  )}

                  <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                    {rfq.supplier_groups.map((group, gi) => {
                      // Group visual style
                      const isOpenings   = group.is_openings
                      const isConfirmed  = group.confirmed
                      const isSuggested  = group.suggested
                      const isUnassigned = !isOpenings && !isConfirmed && !isSuggested
                      const borderCls = isOpenings   ? 'border-amber-200'
                                      : isConfirmed  ? 'border-teal-200'
                                      : isSuggested  ? 'border-gray-200'
                                      : 'border-amber-200'
                      const headerCls = isOpenings   ? 'bg-amber-50'
                                      : isConfirmed  ? 'bg-teal-50'
                                      : isSuggested  ? 'bg-gray-50'
                                      : 'bg-amber-50'
                      const titleCls  = isOpenings   ? 'text-amber-700'
                                      : isConfirmed  ? 'text-teal-700'
                                      : isSuggested  ? 'text-gray-600'
                                      : 'text-amber-700'
                      return (
                        <div key={gi} className={`border rounded-lg overflow-hidden ${borderCls}`}>
                          <div className={`px-4 py-2 flex items-center justify-between ${headerCls}`}>
                            <div className="flex items-center gap-2">
                              <span className={`text-xs font-semibold ${titleCls}`}>
                                {isOpenings   ? 'Openings (Provisional — supplier quotes required)' : group.supplier_name}
                              </span>
                              {isConfirmed  && <span className="text-[10px] bg-teal-100 text-teal-600 border border-teal-200 px-1.5 py-0.5 rounded font-medium">confirmed</span>}
                              {isSuggested  && <span className="text-[10px] bg-gray-100 text-gray-500 border border-gray-200 px-1.5 py-0.5 rounded font-medium">suggested</span>}
                              {isUnassigned && <span className="text-[10px] bg-amber-100 text-amber-600 border border-amber-200 px-1.5 py-0.5 rounded font-medium">unassigned</span>}
                            </div>
                            {group.estimated_subtotal != null && (
                              <span className="text-[11px] text-gray-500">
                                est. {rfq.project.currency} {Number(group.estimated_subtotal).toLocaleString()}
                              </span>
                            )}
                          </div>
                          <table className="w-full text-xs">
                            <thead className="border-b border-gray-100">
                              <tr>
                                <th className="text-left px-4 py-1.5 text-[10px] font-medium text-gray-400 uppercase">Material</th>
                                <th className="text-right px-3 py-1.5 text-[10px] font-medium text-gray-400 uppercase">Qty</th>
                                <th className="text-left px-2 py-1.5 text-[10px] font-medium text-gray-400 uppercase">Unit</th>
                                <th className="text-right px-3 py-1.5 text-[10px] font-medium text-gray-400 uppercase">Est. Cost</th>
                                {!isOpenings && <th className="px-3 py-1.5 text-[10px] font-medium text-gray-400 uppercase text-left">Supplier</th>}
                              </tr>
                            </thead>
                            <tbody>
                              {group.items.map(item => (
                                <tr key={item.line_id} className={`border-t border-gray-50 ${item.price_source === 'estimate' ? 'bg-amber-50/40' : ''}`}>
                                  <td className="px-4 py-2 text-gray-800">
                                    <div>{item.description}</div>
                                    {item.required_evidence?.length > 0 && (
                                      <div className="text-[10px] text-amber-500">⚠ {item.required_evidence.join(', ')}</div>
                                    )}
                                  </td>
                                  <td className="px-3 py-2 text-right text-gray-600 font-mono">{item.quantity}</td>
                                  <td className="px-2 py-2 text-gray-400">{item.unit}</td>
                                  <td className="px-3 py-2 text-right text-gray-600">
                                    {item.estimated_line_cost != null ? (
                                      <span className="flex items-center justify-end gap-1">
                                        {item.price_source === 'estimate' && (
                                          <span className="text-[9px] bg-amber-100 text-amber-600 border border-amber-200 px-1 py-0.5 rounded font-medium">est.</span>
                                        )}
                                        {item.currency} {Number(item.estimated_line_cost).toLocaleString()}
                                      </span>
                                    ) : (
                                      <span className="text-red-400 font-medium">no price</span>
                                    )}
                                  </td>
                                  {!isOpenings && (
                                    <td className="px-3 py-2">
                                      {item.material_id ? (
                                        <select
                                          defaultValue=""
                                          className="text-[11px] border border-gray-200 rounded px-1.5 py-1 text-gray-700 bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 max-w-[130px]"
                                          onChange={async e => {
                                            const supplierId = e.target.value
                                            if (!supplierId) return
                                            try {
                                              await api(`/materials/${item.material_id}/evidence`, {
                                                method: 'PATCH',
                                                body: JSON.stringify({ preferred_supplier_id: supplierId }),
                                              })
                                              await loadRfq()
                                            } catch (err) {
                                              alert(`Failed to assign supplier: ${err.message}`)
                                            }
                                          }}
                                        >
                                          <option value="">— assign supplier —</option>
                                          {rfqSuppliers.filter(s => !s.archived).map(s => (
                                            <option key={s.id} value={s.id}>{s.name}</option>
                                          ))}
                                        </select>
                                      ) : (
                                        <span className="text-gray-300 text-[11px]">—</span>
                                      )}
                                    </td>
                                  )}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )
                    })}
                  </div>
                  {/* Responses panel */}
                  <RfqResponsesPanel
                    quoteId={quote.id}
                    responses={rfqResponses}
                    loading={responsesLoading}
                    onLoad={loadResponses}
                    onDelete={async (reqId) => {
                      await api(`/quotes/${quote.id}/rfq/requests/${reqId}`, { method: 'DELETE' })
                      loadResponses()
                    }}
                  />
                </>
              )}

              {/* Comparison view */}
              {rfqView === 'comparison' && (
                <RfqComparisonView
                  comparison={comparison}
                  loading={compLoading}
                  error={compErr}
                  onReload={loadComparison}
                  quoteCurrency={quote.currency}
                  quoteId={quote.id}
                  api={api}
                />
              )}
            </>
          )}
          {!rfq && !rfqLoading && !rfqErr && (
            <div className="text-center py-8 space-y-3">
              <p className="text-sm text-gray-500">Generate a procurement RFQ package from this quote's BOM.</p>
              <p className="text-xs text-gray-400">Materials will be grouped by supplier. You can download the JSON or copy it to send.</p>
              <Btn onClick={loadRfq}>Generate RFQ Package</Btn>
            </div>
          )}

          {showSendModal && rfq && (
            <SendRfqModal
              rfq={rfq}
              quoteId={quote.id}
              onClose={() => setShowSendModal(false)}
              onSent={() => { setShowSendModal(false); loadResponses() }}
            />
          )}
        </div>
      )}

      {showEmailModal && emailPreview && (
        <SendQuoteEmailModal
          preview={emailPreview}
          onClose={() => setShowEmailModal(false)}
          onSend={handleSendEmail}
        />
      )}
    </Modal>
  )
}

// ── Send Quote Email Modal ────────────────────────────────────────────────────

function SendQuoteEmailModal({ preview, onClose, onSend }) {
  const [subject, setSubject]     = useState(preview.subject)
  const [body, setBody]           = useState(preview.body)
  const [followUpDays, setFollowUpDays] = useState(3)
  const [sending, setSending]     = useState(false)
  const [result, setResult]       = useState(null)
  const [err, setErr]             = useState('')

  async function handleSend() {
    setSending(true)
    setErr('')
    try {
      const res = await onSend(subject, body, followUpDays)
      setResult(res)
    } catch (e) {
      setErr(e.message ?? 'Send failed')
    } finally {
      setSending(false)
    }
  }

  if (result) {
    const ok = result.email_status === 'sent'
    const logged = result.email_status === 'logged_not_sent'
    return (
      <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-sm">
        <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-6 space-y-4">
          <div className={`text-center space-y-2`}>
            <div className={`text-3xl ${ok ? 'text-green-500' : logged ? 'text-amber-500' : 'text-red-500'}`}>
              {ok ? '✓' : logged ? '⚠' : '✕'}
            </div>
            <div className="font-semibold text-gray-900">
              {ok ? 'Quote sent!' : logged ? 'Quote not sent — no email provider' : 'Send failed'}
            </div>
            <div className="text-xs text-gray-500">{result.email_message}</div>
            {logged && (
              <div className="text-[11px] bg-amber-50 border border-amber-200 rounded p-2 text-amber-700">
                Set <code className="font-mono">RESEND_API_KEY</code> in Render environment variables to enable email delivery.
                The quote status has been updated to "sent" and the event was logged.
              </div>
            )}
          </div>
          <div className="flex justify-center">
            <button type="button" onClick={onClose}
              className="px-4 py-2 bg-gray-900 text-white text-sm rounded font-medium hover:bg-gray-700">
              Done
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden flex flex-col max-h-[90vh]">
        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <div>
            <div className="font-semibold text-gray-900">Send Quote to Client</div>
            <div className="text-xs text-gray-400 mt-0.5">
              {preview.to ?? 'No email on file'}
              {preview.has_price ? '' : preview.is_indicative ? ' · includes indicative estimate' : ' · no price yet'}
            </div>
          </div>
          <button type="button" onClick={onClose} className="text-gray-300 hover:text-gray-600 text-xl leading-none mt-0.5">✕</button>
        </div>
        <div className="px-6 py-4 space-y-3 overflow-y-auto flex-1">
          <div>
            <label className="block text-[11px] font-medium text-gray-500 mb-1">To</label>
            <div className="text-sm text-gray-700 bg-gray-50 rounded px-2.5 py-1.5">{preview.to ?? <span className="text-red-500">No email address</span>}</div>
          </div>
          <div>
            <label className="block text-[11px] font-medium text-gray-500 mb-1">Subject</label>
            <input value={subject} onChange={e => setSubject(e.target.value)}
              className="w-full bg-white border border-gray-200 rounded px-2.5 py-1.5 text-sm focus:outline-none focus:border-gray-500" />
          </div>
          <div>
            <label className="block text-[11px] font-medium text-gray-500 mb-1">Message</label>
            <textarea value={body} onChange={e => setBody(e.target.value)} rows={7}
              className="w-full bg-white border border-gray-200 rounded px-2.5 py-1.5 text-sm focus:outline-none focus:border-gray-500 resize-none" />
          </div>
          <div className="bg-blue-50 border border-blue-100 rounded p-2.5">
            <div className="text-[10px] font-semibold text-blue-400 uppercase tracking-wide mb-1">Client Portal Link</div>
            <code className="text-[11px] text-blue-600 break-all">{preview.client_portal_url}</code>
            <div className="text-[10px] text-blue-300 mt-1">This link will be embedded in the email. The client can view and respond to the quote.</div>
          </div>
          <div>
            <label className="block text-[11px] font-medium text-gray-500 mb-1">Follow-up reminder (days)</label>
            <input type="number" min={1} max={30} value={followUpDays} onChange={e => setFollowUpDays(Number(e.target.value))}
              className="w-24 bg-white border border-gray-200 rounded px-2.5 py-1.5 text-sm focus:outline-none focus:border-gray-500" />
          </div>
          {err && <p className="text-xs text-red-500">{err}</p>}
        </div>
        <div className="px-6 py-3 border-t border-gray-100 flex justify-end gap-2 shrink-0">
          <button type="button" onClick={onClose}
            className="px-3 py-1.5 text-sm rounded font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-200">
            Cancel
          </button>
          <button type="button" onClick={handleSend} disabled={sending || !preview.to}
            className="px-3 py-1.5 text-sm rounded font-medium bg-green-600 text-white hover:bg-green-700 disabled:opacity-40">
            {sending ? 'Sending…' : 'Send Quote'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Send RFQ Modal ─────────────────────────────────────────────────────────────

const APP_URL = import.meta.env.VITE_APP_URL || window.location.origin

function SendRfqModal({ rfq, quoteId, onClose, onSent }) {
  const api = useApi()
  const [targets, setTargets] = useState(
    rfq.supplier_groups.map(g => ({ supplier_name: g.supplier_name, supplier_email: '', items: g.items }))
  )
  const [expiresDays, setExpiresDays] = useState(14)
  const [sending, setSending] = useState(false)
  const [sentLinks, setSentLinks] = useState(null)
  const [err, setErr] = useState('')

  function updateTarget(idx, field, value) {
    setTargets(prev => prev.map((t, i) => i === idx ? { ...t, [field]: value } : t))
  }

  async function handleSend() {
    setSending(true)
    setErr('')
    try {
      const result = await api(`/quotes/${quoteId}/rfq/send`, {
        method: 'POST',
        body: JSON.stringify({ targets, expires_days: expiresDays }),
      })
      setSentLinks(result)
      onSent()
    } catch (e) {
      setErr(e.message ?? 'Failed to send')
    } finally {
      setSending(false)
    }
  }

  if (sentLinks) return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden flex flex-col max-h-[90vh]">
        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <div className="font-semibold text-gray-900">RFQ links created</div>
          <button type="button" onClick={onClose} className="text-gray-300 hover:text-gray-600 text-xl leading-none mt-0.5">✕</button>
        </div>
        <div className="px-6 py-4 space-y-3 overflow-y-auto flex-1">
          <p className="text-xs text-gray-500">Copy and send these links to your suppliers. Each link is unique and expires in {expiresDays} days.</p>
          {sentLinks.map(req => (
            <div key={req.id} className="border border-gray-100 rounded-lg p-3 space-y-1.5">
              <div className="text-xs font-semibold text-gray-700">{req.supplier_name}</div>
              {req.supplier_email && <div className="text-[11px] text-gray-400">{req.supplier_email}</div>}
              <div className="flex items-center gap-2">
                <code className="text-[11px] text-blue-600 bg-blue-50 rounded px-2 py-1 flex-1 truncate">
                  {APP_URL}/rfq-respond/{req.token}
                </code>
                <Btn small variant="secondary" onClick={() => navigator.clipboard.writeText(`${APP_URL}/rfq-respond/${req.token}`)}>
                  Copy
                </Btn>
              </div>
            </div>
          ))}
        </div>
        <div className="px-6 py-3 border-t border-gray-100 flex justify-end shrink-0">
          <Btn onClick={onClose}>Done</Btn>
        </div>
      </div>
    </div>
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden flex flex-col max-h-[90vh]">
        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <div>
            <div className="font-semibold text-gray-900">Send RFQ to Suppliers</div>
            <div className="text-xs text-gray-400 mt-0.5">Each supplier gets a unique private link to fill in their pricing</div>
          </div>
          <button type="button" onClick={onClose} className="text-gray-300 hover:text-gray-600 text-xl leading-none mt-0.5">✕</button>
        </div>
        <div className="px-6 py-4 space-y-3 overflow-y-auto flex-1">
          {targets.map((t, idx) => (
            <div key={idx} className="border border-gray-100 rounded-lg p-3 space-y-2">
              <div className="text-xs font-semibold text-gray-700">{t.supplier_name}</div>
              <div className="text-[11px] text-gray-400">{t.items.length} item{t.items.length !== 1 ? 's' : ''}</div>
              <div>
                <label className="block text-[11px] font-medium text-gray-500 mb-1">Supplier email (optional)</label>
                <input
                  type="email"
                  value={t.supplier_email}
                  onChange={e => updateTarget(idx, 'supplier_email', e.target.value)}
                  placeholder="supplier@example.com"
                  className="w-full bg-white border border-gray-200 rounded px-2.5 py-1.5 text-sm focus:outline-none focus:border-gray-500"
                />
              </div>
            </div>
          ))}
          <div>
            <label className="block text-[11px] font-medium text-gray-500 mb-1">Link expires after (days)</label>
            <input
              type="number"
              min={1}
              max={90}
              value={expiresDays}
              onChange={e => setExpiresDays(parseInt(e.target.value) || 14)}
              className="w-24 bg-white border border-gray-200 rounded px-2.5 py-1.5 text-sm focus:outline-none focus:border-gray-500"
            />
          </div>
          {err && <p className="text-xs text-red-500">{err}</p>}
        </div>
        <div className="px-6 py-3 border-t border-gray-100 flex justify-end gap-2 shrink-0">
          <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
          <Btn onClick={handleSend} disabled={sending}>{sending ? 'Creating links…' : `Create ${targets.length} link${targets.length !== 1 ? 's' : ''}`}</Btn>
        </div>
      </div>
    </div>
  )
}

// ── RFQ Responses Panel ────────────────────────────────────────────────────────

const RESP_STATUS = {
  pending:   { cls: 'bg-gray-100 text-gray-500', label: 'Pending' },
  viewed:    { cls: 'bg-blue-50 text-blue-600',  label: 'Viewed' },
  responded: { cls: 'bg-green-50 text-green-700', label: 'Responded' },
  expired:   { cls: 'bg-orange-50 text-orange-600', label: 'Expired' },
}

function RfqResponsesPanel({ quoteId, responses, loading, onLoad, onDelete }) {
  const [expanded, setExpanded] = useState(null)

  if (responses === null && !loading) return (
    <div className="border-t border-gray-100 pt-3">
      <Btn small variant="secondary" onClick={onLoad}>Show sent requests &amp; responses</Btn>
    </div>
  )

  if (loading) return (
    <div className="border-t border-gray-100 pt-3">
      <p className="text-xs text-gray-400">Loading responses…</p>
    </div>
  )

  return (
    <div className="border-t border-gray-100 pt-3 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-gray-600">Sent requests & responses ({responses.length})</p>
        <Btn small variant="secondary" onClick={onLoad}>Refresh</Btn>
      </div>
      {responses.length === 0 && (
        <p className="text-xs text-gray-400">No RFQ requests sent yet.</p>
      )}
      {responses.map(req => {
        const sc = RESP_STATUS[req.status] ?? RESP_STATUS.pending
        const isOpen = expanded === req.id
        return (
          <div key={req.id} className="border border-gray-100 rounded-lg overflow-hidden">
            <div
              className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-gray-50"
              onClick={() => setExpanded(isOpen ? null : req.id)}
            >
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-800">{req.supplier_name}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${sc.cls}`}>{sc.label}</span>
              </div>
              <div className="flex items-center gap-3">
                {req.response_total != null && (
                  <span className="text-xs font-semibold text-green-700">
                    {req.response_currency || '—'} {Number(req.response_total).toLocaleString()}
                  </span>
                )}
                <span className="text-[10px] text-gray-400">{new Date(req.created_at).toLocaleDateString()}</span>
                <span className="text-gray-300 text-xs">{isOpen ? '▲' : '▼'}</span>
              </div>
            </div>

            {isOpen && (
              <div className="border-t border-gray-50 px-3 py-2 space-y-2 bg-gray-50/50">
                <div className="flex flex-wrap gap-4 text-[11px] text-gray-500">
                  {req.supplier_email && <span>Email: {req.supplier_email}</span>}
                  {req.expires_at && <span>Expires: {new Date(req.expires_at).toLocaleDateString()}</span>}
                  {req.viewed_at && <span>Viewed: {new Date(req.viewed_at).toLocaleDateString()}</span>}
                  {req.responded_at && <span>Responded: {new Date(req.responded_at).toLocaleDateString()}</span>}
                </div>
                <div className="flex items-center gap-2">
                  <code className="text-[11px] text-blue-600 bg-blue-50 rounded px-2 py-1 flex-1 truncate">
                    {APP_URL}/rfq-respond/{req.token}
                  </code>
                  <Btn small variant="secondary" onClick={() => navigator.clipboard.writeText(`${APP_URL}/rfq-respond/${req.token}`)}>Copy link</Btn>
                </div>
                {req.response_notes && (
                  <p className="text-[11px] text-gray-600 italic">"{req.response_notes}"</p>
                )}
                {req.response_lines?.length > 0 && (
                  <table className="w-full text-xs mt-1">
                    <thead>
                      <tr>
                        <th className="text-left py-1 text-[10px] font-medium text-gray-400 uppercase">Item</th>
                        <th className="text-right py-1 text-[10px] font-medium text-gray-400 uppercase">Unit Price</th>
                        <th className="text-right py-1 text-[10px] font-medium text-gray-400 uppercase">Total</th>
                        <th className="py-1 text-[10px] font-medium text-gray-400 uppercase">Lead</th>
                        <th className="py-1 text-[10px] font-medium text-gray-400 uppercase">Avail.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {req.response_lines.map(line => (
                        <tr key={line.id} className="border-t border-gray-100">
                          <td className="py-1 pr-2 text-gray-700">{line.description || `#${line.line_id}`}</td>
                          <td className="py-1 text-right font-mono text-gray-600">
                            {line.unit_price != null ? `${line.currency || ''} ${Number(line.unit_price).toFixed(2)}` : '—'}
                          </td>
                          <td className="py-1 text-right font-mono text-gray-600">
                            {line.total_price != null ? `${Number(line.total_price).toFixed(2)}` : '—'}
                          </td>
                          <td className="py-1 pl-2 text-gray-500">{line.lead_time_days != null ? `${line.lead_time_days}d` : '—'}</td>
                          <td className="py-1 pl-2 text-gray-500">{line.availability || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                <div className="flex justify-end pt-1">
                  <button
                    onClick={() => onDelete(req.id)}
                    className="text-[11px] text-red-400 hover:text-red-600"
                  >
                    Delete request
                  </button>
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── RFQ Comparison View ────────────────────────────────────────────────────────

function RfqComparisonView({ comparison, loading, error, onReload, quoteCurrency, quoteId, api }) {
  const [awarding, setAwarding] = useState(null)  // rfq_request_id being processed

  if (loading) return <p className="text-xs text-gray-400 text-center py-8">Loading comparison…</p>
  if (error) return <p className="text-xs text-red-500">{error}</p>

  if (!comparison) return (
    <div className="text-center py-8 space-y-2">
      <p className="text-sm text-gray-500">Compare supplier responses side-by-side.</p>
      <Btn small onClick={onReload}>Load Comparison</Btn>
    </div>
  )

  if (!comparison.has_responses) return (
    <div className="text-center py-8 space-y-1">
      <p className="text-sm text-gray-500">No supplier responses yet.</p>
      <p className="text-xs text-gray-400">Send RFQ links to suppliers and wait for them to submit pricing.</p>
      <Btn small variant="secondary" onClick={onReload}>Refresh</Btn>
    </div>
  )

  const { suppliers, lines, totals, cheapest_total_supplier, margin } = comparison
  const cur = quoteCurrency || 'EUR'
  const anyAwarded = suppliers.some(s => s.is_awarded)

  async function handleAward(s) {
    if (!window.confirm(`Award this RFQ to ${s.supplier_name}?`)) return
    setAwarding(s.rfq_request_id)
    try {
      await api(`/quotes/${quoteId}/rfq/requests/${s.rfq_request_id}/award`, { method: 'POST' })
      await onReload()
    } catch (e) {
      alert(`Award failed: ${e.message}`)
    } finally {
      setAwarding(null)
    }
  }

  async function handleUnaward(s) {
    if (!window.confirm(`Remove award from ${s.supplier_name}?`)) return
    setAwarding(s.rfq_request_id)
    try {
      await api(`/quotes/${quoteId}/rfq/requests/${s.rfq_request_id}/award`, { method: 'DELETE' })
      await onReload()
    } catch (e) {
      alert(`Failed: ${e.message}`)
    } finally {
      setAwarding(null)
    }
  }

  return (
    <div className="space-y-3">
      {/* Supplier totals bar */}
      <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${suppliers.length}, 1fr)` }}>
        {suppliers.map(s => (
          <div
            key={s.supplier_name}
            className={`rounded-lg p-3 border text-center ${
              s.is_awarded ? 'bg-blue-50 border-blue-300 ring-1 ring-blue-300'
              : s.is_cheapest ? 'bg-green-50 border-green-200'
              : 'bg-gray-50 border-gray-100'
            }`}
          >
            <div className={`text-xs font-semibold truncate ${s.is_awarded ? 'text-blue-800' : s.is_cheapest ? 'text-green-800' : 'text-gray-700'}`}>
              {s.supplier_name}
              {s.is_awarded && <span className="ml-1 text-[10px] bg-blue-100 text-blue-700 px-1 rounded">Awarded</span>}
              {!s.is_awarded && s.is_cheapest && <span className="ml-1 text-[10px] bg-green-100 text-green-700 px-1 rounded">Lowest</span>}
            </div>
            <div className={`text-sm font-bold mt-1 ${s.is_awarded ? 'text-blue-700' : s.is_cheapest ? 'text-green-700' : 'text-gray-800'}`}>
              {s.total != null ? `${s.response_currency || cur} ${Number(s.total).toLocaleString()}` : '—'}
            </div>
            {s.responded_at && (
              <div className="text-[10px] text-gray-400 mt-0.5">{new Date(s.responded_at).toLocaleDateString()}</div>
            )}
            <div className="mt-2">
              {s.is_awarded ? (
                <button
                  onClick={() => handleUnaward(s)}
                  disabled={awarding === s.rfq_request_id}
                  className="text-[10px] text-blue-500 hover:text-blue-700 underline cursor-pointer disabled:opacity-40"
                >
                  {awarding === s.rfq_request_id ? 'Updating…' : 'Remove award'}
                </button>
              ) : (
                <Btn
                  small
                  variant={s.is_cheapest && !anyAwarded ? 'success' : 'secondary'}
                  onClick={() => handleAward(s)}
                  disabled={awarding === s.rfq_request_id}
                >
                  {awarding === s.rfq_request_id ? 'Awarding…' : 'Award'}
                </Btn>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Margin card */}
      {margin && (
        <div className={`rounded-lg px-4 py-3 border flex items-center justify-between ${margin.gross_margin >= 0 ? 'bg-blue-50 border-blue-100' : 'bg-red-50 border-red-100'}`}>
          <div>
            <div className="text-[10px] font-medium text-gray-500 uppercase tracking-wide">Estimated Margin (vs cheapest procurement)</div>
            <div className={`text-sm font-bold mt-0.5 ${margin.gross_margin >= 0 ? 'text-blue-700' : 'text-red-600'}`}>
              {cur} {Number(margin.gross_margin).toLocaleString()}
              {margin.gross_margin_pct != null && (
                <span className="text-xs font-normal ml-2">({margin.gross_margin_pct}%)</span>
              )}
            </div>
          </div>
          <div className="text-right text-[11px] text-gray-500 space-y-0.5">
            <div>Quoted: <span className="font-medium text-gray-700">{cur} {Number(margin.quoted_ex_vat).toLocaleString()}</span></div>
            <div>Procurement: <span className="font-medium text-gray-700">{cur} {Number(margin.cheapest_procurement_total).toLocaleString()}</span></div>
          </div>
        </div>
      )}

      {/* Line comparison table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-gray-50">
              <th className="text-left px-3 py-2 text-[10px] font-medium text-gray-400 uppercase sticky left-0 bg-gray-50 min-w-[160px]">Item</th>
              <th className="text-right px-2 py-2 text-[10px] font-medium text-gray-400 uppercase">Qty</th>
              <th className="text-left px-2 py-2 text-[10px] font-medium text-gray-400 uppercase">Unit</th>
              <th className="text-right px-2 py-2 text-[10px] font-medium text-gray-400 uppercase">Est. Unit</th>
              {suppliers.map(s => (
                <th key={s.supplier_name} className={`text-right px-3 py-2 text-[10px] font-medium uppercase whitespace-nowrap ${s.is_cheapest ? 'text-green-600' : 'text-gray-400'}`}>
                  {s.supplier_name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lines.map((line, i) => (
              <tr key={line.line_id} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}>
                <td className="px-3 py-2 text-gray-800 sticky left-0 bg-inherit">
                  <div className="font-medium leading-snug">{line.description}</div>
                  {line.element_type && <div className="text-[10px] text-gray-400">{line.element_type}</div>}
                </td>
                <td className="px-2 py-2 text-right font-mono text-gray-600">{line.quantity ?? '—'}</td>
                <td className="px-2 py-2 text-gray-400">{line.unit || '—'}</td>
                <td className="px-2 py-2 text-right text-gray-400 font-mono">
                  {line.estimated_unit_price != null ? Number(line.estimated_unit_price).toFixed(2) : '—'}
                </td>
                {suppliers.map(s => {
                  const cell = line.suppliers?.[s.supplier_name]
                  const isCheapest = line.cheapest_supplier === s.supplier_name
                  return (
                    <td key={s.supplier_name} className={`px-3 py-2 text-right font-mono ${isCheapest ? 'text-green-700 font-semibold' : 'text-gray-700'}`}>
                      {cell ? (
                        <div>
                          <div>{cell.unit_price != null ? Number(cell.unit_price).toFixed(2) : '—'}</div>
                          {cell.lead_time_days != null && (
                            <div className="text-[10px] text-gray-400 font-normal">{cell.lead_time_days}d</div>
                          )}
                          {cell.substitute_offered && (
                            <div className="text-[10px] text-amber-500 font-normal">sub</div>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-200">—</span>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
            {/* Totals row */}
            <tr className="border-t-2 border-gray-200 bg-gray-50 font-semibold">
              <td className="px-3 py-2 text-gray-700 sticky left-0 bg-gray-50" colSpan={4}>Total</td>
              {suppliers.map(s => (
                <td key={s.supplier_name} className={`px-3 py-2 text-right font-mono ${s.is_cheapest ? 'text-green-700' : 'text-gray-700'}`}>
                  {totals[s.supplier_name] != null ? Number(totals[s.supplier_name]).toLocaleString() : '—'}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      {/* Supplier notes */}
      {suppliers.some(s => s.response_notes) && (
        <div className="space-y-1">
          <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wide">Supplier notes</p>
          {suppliers.filter(s => s.response_notes).map(s => (
            <div key={s.supplier_name} className="text-xs text-gray-600">
              <span className="font-medium">{s.supplier_name}:</span> {s.response_notes}
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-end">
        <Btn small variant="secondary" onClick={onReload}>Refresh</Btn>
      </div>
    </div>
  )
}

function InfoRow({ label, children }) {
  return (
    <div>
      <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wide">{label}</div>
      <div className="text-sm text-gray-800 mt-0.5">{children}</div>
    </div>
  )
}

// ── Tab filters ────────────────────────────────────────────────────────────────

const TABS = ['all', 'draft', 'sent', 'follow_up_due', 'accepted', 'lost', 'expired', 'converted']

// ── Main page ──────────────────────────────────────────────────────────────────

export default function QuotesPage() {
  const api = useApi()
  const [quotes, setQuotes] = useState([])
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('all')
  const [showNew, setShowNew] = useState(false)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    Promise.all([
      api('/quotes'),
      api('/clients'),
    ]).then(([q, c]) => {
      setQuotes(q)
      setClients(c)
    }).finally(() => setLoading(false))
  }, [])

  function handleCreated(q) {
    setQuotes(prev => [q, ...prev])
    setShowNew(false)
    setSelected(q)
  }

  function handleUpdated(updated) {
    setQuotes(prev => prev.map(q => q.id === updated.id ? updated : q))
    setSelected(updated)
  }

  const filtered = activeTab === 'all' ? quotes : quotes.filter(q => q.status === activeTab)

  const tabLabel = (t) => {
    if (t === 'all') return `All (${quotes.length})`
    const count = quotes.filter(q => q.status === t).length
    const cfg = STATUS_CFG[t]
    return `${cfg?.label ?? t} (${count})`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-gray-400">Loading quotes…</div>
    )
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Quotes</h1>
          <p className="text-sm text-gray-400 mt-0.5">Commercial pipeline — track every opportunity from lead to job</p>
        </div>
        <Btn onClick={() => setShowNew(true)}>+ New Quote</Btn>
      </div>

      <SummaryCards quotes={quotes} />

      {/* Status filter tabs */}
      <div className="flex gap-1 mb-4 overflow-x-auto pb-1">
        {TABS.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-3 py-1.5 rounded text-xs font-medium whitespace-nowrap transition-colors ${
              activeTab === t ? 'bg-gray-900 text-white' : 'bg-white border border-gray-200 text-gray-500 hover:text-gray-800'
            }`}>
            {tabLabel(t)}
          </button>
        ))}
      </div>

      {/* Quote cards */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 text-sm text-gray-400">
          {activeTab === 'all' ? 'No quotes yet. Create your first one.' : `No ${STATUS_CFG[activeTab]?.label ?? activeTab} quotes.`}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {filtered.map(q => {
            const client = clients.find(c => c.id === q.client_id)
            return (
              <button key={q.id} onClick={() => setSelected(q)}
                className="text-left bg-white rounded-lg border border-gray-100 p-4 hover:border-gray-300 hover:shadow-sm transition-all">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="font-medium text-sm text-gray-900 leading-snug">{q.title}</div>
                  <StatusBadge status={q.status} />
                </div>
                {(client || q.client_name) && (
                  <div className="text-xs text-gray-500 mb-1">{client?.name ?? q.client_name}</div>
                )}
                {q.quote_number && (
                  <div className="text-[11px] text-gray-400 mb-2">{q.quote_number} · {q.revision}</div>
                )}
                {q.total_inc_vat != null && (
                  <div className="text-sm font-semibold text-gray-800 mb-2">
                    {q.currency} {Number(q.total_inc_vat).toLocaleString()} incl. VAT
                  </div>
                )}
                <div className="flex gap-3 text-[10px] text-gray-400">
                  {q.sent_at && <span>Sent {formatDate(q.sent_at)}</span>}
                  {q.follow_up_at && q.status !== 'accepted' && q.status !== 'lost' && (
                    <span className={new Date(q.follow_up_at) < new Date() ? 'text-amber-500 font-medium' : ''}>
                      Follow-up {formatDate(q.follow_up_at)}
                    </span>
                  )}
                  {q.expires_at && <span>Exp. {formatDate(q.expires_at)}</span>}
                </div>
              </button>
            )
          })}
        </div>
      )}

      {showNew && (
        <NewQuoteModal
          clients={clients}
          onClose={() => setShowNew(false)}
          onCreated={handleCreated}
        />
      )}

      {selected && (
        <QuoteDetailModal
          quote={selected}
          clients={clients}
          onClose={() => setSelected(null)}
          onUpdated={handleUpdated}
        />
      )}
    </div>
  )
}
