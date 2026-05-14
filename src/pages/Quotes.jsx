import { useState, useEffect } from 'react'
import { apiFetch } from '../api/client'

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

function Btn({ onClick, children, variant = 'primary', disabled = false }) {
  const base = 'px-3 py-1.5 rounded text-sm font-medium transition-colors disabled:opacity-40'
  const variants = {
    primary: 'bg-gray-900 text-white hover:bg-gray-700',
    secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200',
    danger: 'bg-red-50 text-red-600 hover:bg-red-100',
    success: 'bg-green-600 text-white hover:bg-green-700',
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
      const q = await apiFetch('/quotes', { method: 'POST', body: JSON.stringify(body) })
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
  const [showSendModal, setShowSendModal] = useState(false)
  const [rfqResponses, setRfqResponses] = useState(null)
  const [responsesLoading, setResponsesLoading] = useState(false)

  useEffect(() => {
    apiFetch(`/quotes/${quote.id}/events`).then(setEvents).catch(() => {})
  }, [quote.id])

  async function handleStatusUpdate() {
    setSaving(true)
    setErr('')
    try {
      const updated = await apiFetch(`/quotes/${quote.id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus, note: statusNote || null, lost_reason: lostReason || null }),
      })
      setQuote(updated)
      onUpdated(updated)
      const evs = await apiFetch(`/quotes/${quote.id}/events`)
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
      await apiFetch(`/quotes/${quote.id}/events`, {
        method: 'POST',
        body: JSON.stringify({ event_type: 'note', note: manualNote }),
      })
      setManualNote('')
      const evs = await apiFetch(`/quotes/${quote.id}/events`)
      setEvents(evs)
    } catch (e) {
      setErr(e.message ?? 'Failed to add note')
    } finally {
      setSaving(false)
    }
  }

  const clientName = clients.find(c => c.id === quote.client_id)?.name ?? quote.client_name ?? '—'

  async function loadRfq() {
    setRfqLoading(true)
    setRfqErr('')
    try {
      const data = await apiFetch(`/quotes/${quote.id}/rfq`)
      setRfq(data)
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

  async function loadResponses() {
    setResponsesLoading(true)
    try {
      const data = await apiFetch(`/quotes/${quote.id}/rfq/responses`)
      setRfqResponses(data)
    } catch (_) {}
    finally { setResponsesLoading(false) }
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
        {tabs.map(t => (
          <button key={t} onClick={() => { setTab(t); if (t === 'rfq' && !rfq) loadRfq() }}
            className={`px-3 py-1 text-xs rounded font-medium uppercase tracking-wide transition-colors ${tab === t ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-800'}`}>
            {t}
          </button>
        ))}
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
                  <div className="text-xs font-semibold text-gray-700">{rfq.rfq_id}</div>
                  <div className="text-[11px] text-gray-400 mt-0.5">
                    {rfq.total_items} items · {rfq.total_suppliers} supplier{rfq.total_suppliers !== 1 ? 's' : ''}
                    {rfq.spec_summary?.estimated_total != null && (
                      <span> · est. {rfq.project.currency} {Number(rfq.spec_summary.estimated_total).toLocaleString()}</span>
                    )}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Btn small variant="secondary" onClick={() => navigator.clipboard.writeText(JSON.stringify(rfq, null, 2))}>Copy JSON</Btn>
                  <Btn small variant="secondary" onClick={downloadRfq}>Download</Btn>
                  <Btn small onClick={() => setShowSendModal(true)}>Send to Suppliers</Btn>
                </div>
              </div>

              {/* Warnings */}
              {rfq.spec_summary?.warnings?.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded p-3 space-y-1">
                  <p className="text-[11px] font-medium text-amber-700">BOM warnings</p>
                  {rfq.spec_summary.warnings.map((w, i) => (
                    <p key={i} className="text-[11px] text-amber-600">· {w}</p>
                  ))}
                </div>
              )}

              {/* Supplier groups */}
              <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
                {rfq.supplier_groups.map(group => (
                  <div key={group.supplier_name} className="border border-gray-100 rounded-lg overflow-hidden">
                    <div className="bg-gray-50 px-4 py-2 flex items-center justify-between">
                      <span className="text-xs font-semibold text-gray-700">{group.supplier_name}</span>
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
                          <th className="px-3 py-1.5"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {group.items.map(item => (
                          <tr key={item.line_id} className="border-t border-gray-50">
                            <td className="px-4 py-2 text-gray-800">{item.description}</td>
                            <td className="px-3 py-2 text-right text-gray-600 font-mono">{item.quantity}</td>
                            <td className="px-2 py-2 text-gray-400">{item.unit}</td>
                            <td className="px-3 py-2 text-right text-gray-600">
                              {item.estimated_line_cost != null
                                ? `${item.currency} ${Number(item.estimated_line_cost).toLocaleString()}`
                                : <span className="text-gray-300">—</span>}
                            </td>
                            <td className="px-3 py-2">
                              {item.required_evidence?.length > 0 && (
                                <span className="text-[10px] text-amber-500 font-medium">
                                  ⚠ {item.required_evidence.join(', ')}
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>

              {/* Responses panel */}
              <RfqResponsesPanel
                quoteId={quote.id}
                responses={rfqResponses}
                loading={responsesLoading}
                onLoad={loadResponses}
                onDelete={async (reqId) => {
                  await apiFetch(`/quotes/${quote.id}/rfq/requests/${reqId}`, { method: 'DELETE' })
                  loadResponses()
                }}
              />
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
    </Modal>
  )
}

// ── Send RFQ Modal ─────────────────────────────────────────────────────────────

const APP_URL = import.meta.env.VITE_APP_URL || window.location.origin

function SendRfqModal({ rfq, quoteId, onClose, onSent }) {
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
      const result = await apiFetch(`/quotes/${quoteId}/rfq/send`, {
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
  const [quotes, setQuotes] = useState([])
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('all')
  const [showNew, setShowNew] = useState(false)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    Promise.all([
      apiFetch('/quotes'),
      apiFetch('/clients'),
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
