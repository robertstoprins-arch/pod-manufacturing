import { useState, useEffect, useCallback } from 'react'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const CATEGORIES = [
  'external_cladding', 'internal_paint', 'internal_timber_finish', 'flooring',
  'sanitaryware', 'toilet', 'vanity_unit', 'kitchenette', 'furniture_set',
  'lighting', 'heating_visible', 'ventilation_visible', 'cctv_data',
  'solar_battery', 'delivery_install', 'other',
]

const IMAGE_SOURCE_TYPES = [
  'none', 'placeholder', 'generated_placeholder', 'own_photo',
  'licensed_stock', 'supplier_reference', 'supplier_approved', 'needs_review',
]

const IMAGE_APPROVAL_STATUSES = [
  'missing', 'internal_reference_only', 'needs_approval',
  'approved_for_customer_pdf', 'own_photo', 'licensed_stock', 'generated_placeholder',
]

const QUANTITY_RULES = [
  'each', 'per_m2_floor_area', 'per_m2_wall_area', 'per_m2_roof_area',
  'per_lm_perimeter', 'manual', 'package_fixed',
]

const CUSTOMER_SAFE_STATUSES = new Set([
  'approved_for_customer_pdf', 'own_photo', 'licensed_stock', 'generated_placeholder',
])

const APPROVAL_BADGE = {
  missing:                  { label: 'Missing',          bg: 'bg-red-900/50',    text: 'text-red-300' },
  internal_reference_only:  { label: 'Internal ref',     bg: 'bg-gray-700',      text: 'text-gray-400' },
  needs_approval:           { label: 'Needs approval',   bg: 'bg-amber-900/50',  text: 'text-amber-300' },
  approved_for_customer_pdf:{ label: 'Approved PDF',     bg: 'bg-green-900/50',  text: 'text-green-300' },
  own_photo:                { label: 'Own photo',        bg: 'bg-green-900/50',  text: 'text-green-300' },
  licensed_stock:           { label: 'Licensed stock',   bg: 'bg-green-900/50',  text: 'text-green-300' },
  generated_placeholder:    { label: 'Placeholder',      bg: 'bg-blue-900/50',   text: 'text-blue-300' },
}

function badge(status) {
  const b = APPROVAL_BADGE[status] ?? { label: status, bg: 'bg-gray-700', text: 'text-gray-400' }
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${b.bg} ${b.text}`}>
      {b.label}
    </span>
  )
}

function fmt(cat) {
  return cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

const EMPTY_ITEM = {
  code: '', category: 'external_cladding', name: '', customer_name: '', customer_description: '',
  internal_description: '', supplier_name: '', manufacturer: '', supplier_url: '',
  specification_url: '', datasheet_url: '', image_url: '', image_alt_text: '',
  image_source_type: 'none', image_approval_status: 'missing',
  unit: '', unit_cost: '', currency: 'EUR', price_type: 'allowance',
  default_quantity: 1.0, quantity_rule: 'each',
  included_by_default: false, customer_visible: true, internal_only: false,
  specification_url_public: false,
  suitable_pod_types: '', package_tags: '', lead_time_note: '', notes: '', is_active: true,
}

function itemToForm(item) {
  return {
    ...item,
    unit_cost: item.unit_cost ?? '',
    suitable_pod_types: item.suitable_pod_types ? item.suitable_pod_types.join(', ') : '',
    package_tags: item.package_tags ? item.package_tags.join(', ') : '',
  }
}

function formToPayload(form) {
  return {
    ...form,
    unit_cost: form.unit_cost === '' ? null : parseFloat(form.unit_cost),
    default_quantity: parseFloat(form.default_quantity) || 1.0,
    suitable_pod_types: form.suitable_pod_types
      ? form.suitable_pod_types.split(',').map(s => s.trim()).filter(Boolean)
      : null,
    package_tags: form.package_tags
      ? form.package_tags.split(',').map(s => s.trim()).filter(Boolean)
      : null,
  }
}

// â”€â”€ Customer card preview â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function CustomerCardPreview({ item, onClose }) {
  const safeImage = CUSTOMER_SAFE_STATUSES.has(item.image_approval_status) ? item.image_url : null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70" onClick={onClose}>
      <div
        className="bg-[#1e1e1e] border border-[#333] rounded-lg w-72 overflow-hidden shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="h-40 bg-[#111] flex items-center justify-center">
          {safeImage
            ? <img src={safeImage} alt={item.image_alt_text || ''} className="object-cover w-full h-full" />
            : <span className="text-gray-600 text-xs">No approved image</span>
          }
        </div>
        <div className="p-4">
          <div className="text-xs text-gray-500 mb-1">{fmt(item.category)}</div>
          <div className="text-sm font-semibold text-white">{item.customer_name || item.name}</div>
          {item.customer_description && (
            <div className="text-xs text-gray-400 mt-1 line-clamp-3">{item.customer_description}</div>
          )}
          {item.unit_cost && (
            <div className="mt-2 text-xs text-gray-300">
              {item.currency} {item.unit_cost}
              {item.unit ? ` / ${item.unit}` : ''}
            </div>
          )}
          {item.lead_time_note && (
            <div className="mt-1 text-[10px] text-gray-500">{item.lead_time_note}</div>
          )}
        </div>
        <div className="px-4 pb-3 flex justify-end">
          <button onClick={onClose} className="text-xs text-gray-500 hover:text-gray-300">Close</button>
        </div>
      </div>
    </div>
  )
}

// â”€â”€ Edit / Create modal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function EditModal({ item, onClose, onSaved }) {
  const isNew = !item.id
  const [form, setForm] = useState(() => isNew ? { ...EMPTY_ITEM } : itemToForm(item))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const imageWarning = form.image_url && !CUSTOMER_SAFE_STATUSES.has(form.image_approval_status)

  async function save() {
    setSaving(true)
    setError(null)
    try {
      const payload = formToPayload(form)
      const method = isNew ? 'POST' : 'PUT'
      const url = isNew ? `${API}/finish-catalogue` : `${API}/finish-catalogue/${item.id}`
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const saved = await res.json()
      onSaved(saved, isNew)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const F = ({ label, children, span }) => (
    <div className={span ? 'col-span-2' : ''}>
      <label className="block text-[11px] text-gray-400 mb-1">{label}</label>
      {children}
    </div>
  )

  const inp = (k, type = 'text', extra = {}) => (
    <input
      type={type}
      value={form[k] ?? ''}
      onChange={e => set(k, type === 'number' ? e.target.value : e.target.value)}
      className="w-full bg-[#111] border border-[#333] rounded px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-blue-500"
      {...extra}
    />
  )

  const sel = (k, options) => (
    <select
      value={form[k] ?? ''}
      onChange={e => set(k, e.target.value)}
      className="w-full bg-[#111] border border-[#333] rounded px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-blue-500"
    >
      {options.map(o => (
        <option key={o} value={o}>{o}</option>
      ))}
    </select>
  )

  const chk = (k, label) => (
    <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
      <input
        type="checkbox"
        checked={!!form[k]}
        onChange={e => set(k, e.target.checked)}
        className="accent-blue-500"
      />
      {label}
    </label>
  )

  const ta = (k, rows = 2) => (
    <textarea
      value={form[k] ?? ''}
      onChange={e => set(k, e.target.value)}
      rows={rows}
      className="w-full bg-[#111] border border-[#333] rounded px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-blue-500 resize-none"
    />
  )

  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center bg-black/70 overflow-y-auto py-8">
      <div
        className="bg-[#1a1a1a] border border-[#333] rounded-lg w-full max-w-2xl mx-4 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#272727]">
          <div className="text-sm font-semibold text-white">
            {isNew ? 'New Catalogue Item' : `Edit â€” ${item.name}`}
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-200 text-lg leading-none">&times;</button>
        </div>

        <div className="p-5 space-y-5">
          {/* Identification */}
          <section>
            <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-3">Identification</div>
            <div className="grid grid-cols-2 gap-3">
              <F label="Code *"><div>{inp('code')}</div></F>
              <F label="Category *"><div>{sel('category', CATEGORIES)}</div></F>
              <F label="Internal name *" span><div>{inp('name')}</div></F>
              <F label="Customer name" span><div>{inp('customer_name')}</div></F>
            </div>
          </section>

          {/* Descriptions */}
          <section>
            <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-3">Descriptions</div>
            <div className="grid grid-cols-1 gap-3">
              <F label="Customer description">{ta('customer_description', 3)}</F>
              <F label="Internal description">{ta('internal_description', 2)}</F>
              <F label="Notes">{ta('notes', 2)}</F>
            </div>
          </section>

          {/* Supplier */}
          <section>
            <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-3">Supplier / Manufacturer</div>
            <div className="grid grid-cols-2 gap-3">
              <F label="Supplier name"><div>{inp('supplier_name')}</div></F>
              <F label="Manufacturer"><div>{inp('manufacturer')}</div></F>
              <F label="Supplier URL â€” internal only" span>
                <div className="relative">
                  {inp('supplier_url')}
                  <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] text-gray-600 bg-[#222] px-1.5 py-0.5 rounded pointer-events-none">internal</span>
                </div>
              </F>
              <F label="Specification / product URL" span><div>{inp('specification_url')}</div></F>
              <F label="Datasheet URL" span><div>{inp('datasheet_url')}</div></F>
              <div className="col-span-2">
                <label className="flex items-start gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!!form.specification_url_public}
                    onChange={e => set('specification_url_public', e.target.checked)}
                    className="mt-0.5 accent-blue-500"
                  />
                  <div>
                    <div className="text-xs text-gray-300 font-medium">Show specification link in client PDF</div>
                    <div className="text-[10px] text-gray-500 mt-0.5">
                      Only tick this if the specification URL points to a public product page or datasheet you have permission to share. Supplier URLs are never shown in client PDFs regardless of this setting.
                    </div>
                  </div>
                </label>
              </div>
            </div>
          </section>

          {/* Image */}
          <section>
            <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-3">Image</div>
            {/* Supplier reference image warning */}
            {form.image_url && (form.image_source_type === 'supplier_reference' || form.image_source_type === 'supplier_approved') && (
              <div className="mb-3 flex items-start gap-2 bg-red-900/30 border border-red-700/50 rounded px-3 py-2">
                <svg className="w-4 h-4 text-red-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 16 16" stroke="currentColor" strokeWidth="1.5">
                  <path d="M8 2L14 13H2L8 2z" strokeLinejoin="round" />
                  <path d="M8 6.5v3M8 11h.01" strokeLinecap="round" />
                </svg>
                <span className="text-xs text-red-300">
                  <strong>Supplier image â€” not approved for customer use.</strong> Images copied from supplier websites must not be shown in customer PDFs or marketing material. Set approval status to <em>needs_approval</em> or replace with own photo, licensed stock, or AI-generated placeholder.
                </span>
              </div>
            )}
            {/* AI-modified supplier image warning */}
            {form.image_source_type === 'needs_review' && (
              <div className="mb-3 flex items-start gap-2 bg-amber-900/30 border border-amber-600/50 rounded px-3 py-2">
                <svg className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 16 16" stroke="currentColor" strokeWidth="1.5">
                  <path d="M8 2L14 13H2L8 2z" strokeLinejoin="round" />
                  <path d="M8 6.5v3M8 11h.01" strokeLinecap="round" />
                </svg>
                <span className="text-xs text-amber-300">
                  Image needs review before use. If this is a supplier image modified with AI, it is still derived from the original and cannot be marked as own_photo without legal permission from the supplier.
                </span>
              </div>
            )}
            {/* Generic approval warning */}
            {imageWarning && form.image_source_type !== 'supplier_reference' && form.image_source_type !== 'supplier_approved' && form.image_source_type !== 'needs_review' && (
              <div className="mb-3 flex items-start gap-2 bg-amber-900/30 border border-amber-700/50 rounded px-3 py-2">
                <svg className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 16 16" stroke="currentColor" strokeWidth="1.5">
                  <path d="M8 2L14 13H2L8 2z" strokeLinejoin="round" />
                  <path d="M8 6.5v3M8 11h.01" strokeLinecap="round" />
                </svg>
                <span className="text-xs text-amber-300">
                  Image is stored as <strong>{form.image_source_type}</strong>. It will not appear in customer PDF until approval status is updated.
                </span>
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <F label="Image URL" span><div>{inp('image_url')}</div></F>
              <F label="Alt text" span><div>{inp('image_alt_text')}</div></F>
              <F label="Image source type"><div>{sel('image_source_type', IMAGE_SOURCE_TYPES)}</div></F>
              <F label="Image approval status"><div>{sel('image_approval_status', IMAGE_APPROVAL_STATUSES)}</div></F>
            </div>
            <div className="mt-2 grid grid-cols-1 gap-1 text-[10px] text-gray-600">
              <div><span className="text-green-500">âœ“ Approved for PDF:</span> own_photo Â· licensed_stock Â· generated_placeholder Â· approved_for_customer_pdf</div>
              <div><span className="text-red-400">âœ— Not shown to customers:</span> supplier_reference Â· supplier_approved (unless legal permission) Â· needs_review Â· missing Â· internal_reference_only</div>
            </div>
          </section>

          {/* Pricing */}
          <section>
            <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-3">Pricing</div>
            <div className="grid grid-cols-3 gap-3">
              <F label="Unit cost"><div>{inp('unit_cost', 'number')}</div></F>
              <F label="Currency"><div>{inp('currency')}</div></F>
              <F label="Price type"><div>{inp('price_type')}</div></F>
              <F label="Unit"><div>{inp('unit')}</div></F>
              <F label="Default quantity"><div>{inp('default_quantity', 'number')}</div></F>
              <F label="Quantity rule"><div>{sel('quantity_rule', QUANTITY_RULES)}</div></F>
            </div>
          </section>

          {/* Tags */}
          <section>
            <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-3">Tags &amp; Classification</div>
            <div className="grid grid-cols-2 gap-3">
              <F label="Suitable pod types (comma-separated)" span>
                <div>{inp('suitable_pod_types')}</div>
              </F>
              <F label="Package tags (comma-separated)" span>
                <div>{inp('package_tags')}</div>
              </F>
              <F label="Lead time note" span><div>{inp('lead_time_note')}</div></F>
            </div>
          </section>

          {/* Flags */}
          <section>
            <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-3">Flags</div>
            <div className="flex flex-wrap gap-5">
              {chk('included_by_default', 'Included by default')}
              {chk('customer_visible', 'Customer visible')}
              {chk('internal_only', 'Internal only')}
              {chk('is_active', 'Active')}
            </div>
          </section>

          {error && (
            <div className="text-xs text-red-400 bg-red-900/20 border border-red-700/40 rounded px-3 py-2">{error}</div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-[#272727]">
          <button onClick={onClose} className="px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 transition-colors">
            Cancel
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="px-4 py-1.5 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded font-medium transition-colors disabled:opacity-50"
          >
            {saving ? 'Savingâ€¦' : isNew ? 'Create item' : 'Save changes'}
          </button>
        </div>
      </div>
    </div>
  )
}

// â”€â”€ Research / Draft panel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const EMPTY_DRAFT = {
  name: '', category: 'external_cladding', supplier_name: '', manufacturer: '',
  supplier_url: '', specification_url: '', image_url: '', unit_cost: '',
  currency: 'EUR', unit: '', quantity_rule: 'each', notes: '',
  market: '', research_notes: '',
}

function ResearchPanel({ onApproved }) {
  const [form, setForm] = useState({ ...EMPTY_DRAFT })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [drafts, setDrafts] = useState([])
  const [loadingDrafts, setLoadingDrafts] = useState(true)
  const [approving, setApproving] = useState(null)
  const [editDraft, setEditDraft] = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const loadDrafts = useCallback(async () => {
    setLoadingDrafts(true)
    try {
      const res = await fetch(`${API}/finish-catalogue?is_active=false&customer_visible=false`)
      const data = await res.json()
      // Show only items that look like drafts (code starts with draft_ or internal_only)
      setDrafts(data.filter(i => i.internal_only || i.code.startsWith('draft_')))
    } finally {
      setLoadingDrafts(false)
    }
  }, [])

  useEffect(() => { loadDrafts() }, [loadDrafts])

  async function submitDraft(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const payload = {
        ...form,
        unit_cost: form.unit_cost === '' ? null : parseFloat(form.unit_cost),
      }
      const res = await fetch(`${API}/finish-catalogue/draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const saved = await res.json()
      setSuccess(`Draft created: ${saved.code}`)
      setForm({ ...EMPTY_DRAFT })
      setDrafts(prev => [saved, ...prev])
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function approveDraft(item) {
    setApproving(item.id)
    try {
      const res = await fetch(`${API}/finish-catalogue/${item.id}/approve`, { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const updated = await res.json()
      setDrafts(prev => prev.filter(d => d.id !== item.id))
      onApproved(updated)
    } finally {
      setApproving(null)
    }
  }

  const inp = (k, type = 'text', placeholder = '') => (
    <input
      type={type}
      value={form[k] ?? ''}
      onChange={e => set(k, e.target.value)}
      placeholder={placeholder}
      className="w-full bg-[#111] border border-[#333] rounded px-2.5 py-1.5 text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-blue-500"
    />
  )

  const F = ({ label, children, span }) => (
    <div className={span ? 'col-span-2' : ''}>
      <label className="block text-[11px] text-gray-400 mb-1">{label}</label>
      {children}
    </div>
  )

  return (
    <div className="flex-1 overflow-auto px-6 py-5 space-y-8">
      {/* Quick capture form */}
      <section>
        <div className="text-sm font-semibold text-white mb-1">Quick capture</div>
        <div className="text-xs text-gray-500 mb-4">
          Save a research candidate as a draft. It will not appear in customer-facing views until reviewed and approved.
        </div>
        <form onSubmit={submitDraft} className="bg-[#161616] border border-[#272727] rounded-lg p-4">
          <div className="grid grid-cols-2 gap-3">
            <F label="Name *" span>{inp('name', 'text', 'e.g. Thermory Sauna Cladding 21Ã—120')}</F>
            <F label="Category *">
              <select
                value={form.category}
                onChange={e => set('category', e.target.value)}
                className="w-full bg-[#111] border border-[#333] rounded px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-blue-500"
              >
                {CATEGORIES.map(c => <option key={c} value={c}>{fmt(c)}</option>)}
              </select>
            </F>
            <F label="Market">{inp('market', 'text', 'e.g. Sweden, Finland, Baltic')}</F>
            <F label="Unit cost">{inp('unit_cost', 'number', '0.00')}</F>
            <F label="Currency">
              <select
                value={form.currency}
                onChange={e => set('currency', e.target.value)}
                className="w-full bg-[#111] border border-[#333] rounded px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-blue-500"
              >
                {['EUR','SEK','NOK','DKK','GBP','USD'].map(c => <option key={c}>{c}</option>)}
              </select>
            </F>
            <F label="Unit">{inp('unit', 'text', 'e.g. m2, lm, piece')}</F>
            <F label="Supplier name">{inp('supplier_name')}</F>
            <F label="Manufacturer">{inp('manufacturer')}</F>
            <F label="Supplier URL" span>{inp('supplier_url', 'text', 'https://')}</F>
            <F label="Specification URL" span>{inp('specification_url', 'text', 'https://')}</F>
            <F label="Image URL" span>{inp('image_url', 'text', 'https://')}</F>
            <F label="Research notes" span>
              <textarea
                value={form.research_notes}
                onChange={e => set('research_notes', e.target.value)}
                rows={2}
                placeholder="Context, source, why this was foundâ€¦"
                className="w-full bg-[#111] border border-[#333] rounded px-2.5 py-1.5 text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-blue-500 resize-none"
              />
            </F>
          </div>
          {error && (
            <div className="mt-3 text-xs text-red-400 bg-red-900/20 border border-red-700/40 rounded px-3 py-2">{error}</div>
          )}
          {success && (
            <div className="mt-3 text-xs text-green-400 bg-green-900/20 border border-green-700/40 rounded px-3 py-2">{success}</div>
          )}
          <div className="mt-3 flex justify-end">
            <button
              type="submit"
              disabled={saving || !form.name}
              className="px-4 py-1.5 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded font-medium transition-colors disabled:opacity-50"
            >
              {saving ? 'Savingâ€¦' : 'Save draft'}
            </button>
          </div>
        </form>
      </section>

      {/* Draft queue */}
      <section>
        <div className="text-sm font-semibold text-white mb-1">
          Draft queue
          {drafts.length > 0 && (
            <span className="ml-2 inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-500/20 text-amber-300 text-[10px] font-bold">
              {drafts.length}
            </span>
          )}
        </div>
        <div className="text-xs text-gray-500 mb-4">
          Review each candidate before approving. Approval makes the item active and customer-visible. Images are reviewed separately.
        </div>

        {loadingDrafts ? (
          <div className="text-xs text-gray-600 py-4">Loading draftsâ€¦</div>
        ) : drafts.length === 0 ? (
          <div className="text-xs text-gray-600 py-4 bg-[#161616] border border-[#272727] rounded-lg text-center">
            No drafts in queue
          </div>
        ) : (
          <div className="space-y-2">
            {drafts.map(item => (
              <div
                key={item.id}
                className="bg-[#161616] border border-[#272727] rounded-lg px-4 py-3 flex items-start gap-4"
              >
                {/* Thumbnail */}
                <div className="w-12 h-12 rounded bg-[#222] border border-[#333] shrink-0 overflow-hidden flex items-center justify-center">
                  {item.image_url
                    ? <img src={item.image_url} alt="" className="object-cover w-full h-full" />
                    : <span className="text-gray-700 text-[9px]">No img</span>
                  }
                </div>

                {/* Details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-gray-100">{item.name}</span>
                    <span className="text-[10px] text-gray-600 font-mono">{item.code}</span>
                    <span className="text-[10px] bg-[#222] text-gray-400 px-1.5 py-0.5 rounded">{fmt(item.category)}</span>
                    {badge(item.image_approval_status)}
                  </div>
                  <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] text-gray-500">
                    {item.supplier_name && <span>Supplier: {item.supplier_name}</span>}
                    {item.unit_cost != null && (
                      <span>Price: {item.currency} {item.unit_cost}{item.unit ? ` / ${item.unit}` : ''}</span>
                    )}
                    {item.supplier_url && (
                      <a href={item.supplier_url} target="_blank" rel="noreferrer" className="text-blue-500 hover:text-blue-400">
                        Supplier link â†—
                      </a>
                    )}
                    {item.specification_url && (
                      <a href={item.specification_url} target="_blank" rel="noreferrer" className="text-blue-500 hover:text-blue-400">
                        Spec â†—
                      </a>
                    )}
                  </div>
                  {item.internal_description && (
                    <div className="mt-1 text-[11px] text-gray-600 line-clamp-2">{item.internal_description}</div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => setEditDraft(item)}
                    className="px-3 py-1 text-xs bg-[#222] hover:bg-[#2a2a2a] text-gray-300 rounded border border-[#333] transition-colors"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => approveDraft(item)}
                    disabled={approving === item.id}
                    className="px-3 py-1 text-xs bg-green-700 hover:bg-green-600 text-white rounded font-medium transition-colors disabled:opacity-50"
                  >
                    {approving === item.id ? 'â€¦' : 'Approve'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Edit draft modal reuses EditModal */}
      {editDraft !== null && (
        <EditModal
          item={editDraft}
          onClose={() => setEditDraft(null)}
          onSaved={(saved) => {
            setDrafts(prev => prev.map(d => d.id === saved.id ? saved : d))
            setEditDraft(null)
          }}
        />
      )}
    </div>
  )
}

// â”€â”€ Main page â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export default function FinishCatalogue() {
  const [mainTab, setMainTab] = useState('catalogue')  // 'catalogue' | 'research'
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterCat, setFilterCat] = useState('')
  const [filterVisible, setFilterVisible] = useState('')
  const [filterApproval, setFilterApproval] = useState('')
  const [search, setSearch] = useState('')
  const [editItem, setEditItem] = useState(null)   // null = closed, EMPTY_ITEM = new, item = edit
  const [preview, setPreview] = useState(null)
  const [deactivating, setDeactivating] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ is_active: '' })
      params.delete('is_active')
      if (filterCat) params.set('category', filterCat)
      if (filterVisible !== '') params.set('customer_visible', filterVisible)
      if (search) params.set('search', search)
      params.set('is_active', 'true')   // admin shows active by default; we'll also fetch inactive

      // Fetch both active and inactive for admin view
      const [activeRes, inactiveRes] = await Promise.all([
        fetch(`${API}/finish-catalogue?is_active=true${filterCat ? `&category=${filterCat}` : ''}${filterVisible !== '' ? `&customer_visible=${filterVisible}` : ''}${search ? `&search=${encodeURIComponent(search)}` : ''}`),
        fetch(`${API}/finish-catalogue?is_active=false${filterCat ? `&category=${filterCat}` : ''}${filterVisible !== '' ? `&customer_visible=${filterVisible}` : ''}${search ? `&search=${encodeURIComponent(search)}` : ''}`),
      ])
      const [active, inactive] = await Promise.all([activeRes.json(), inactiveRes.json()])
      let all = [...active, ...inactive]
      if (filterApproval) all = all.filter(i => i.image_approval_status === filterApproval)
      setItems(all)
    } finally {
      setLoading(false)
    }
  }, [filterCat, filterVisible, filterApproval, search])

  useEffect(() => { load() }, [load])

  async function deactivate(item) {
    setDeactivating(item.id)
    try {
      await fetch(`${API}/finish-catalogue/${item.id}`, { method: 'DELETE' })
      setItems(prev => prev.map(i => i.id === item.id ? { ...i, is_active: false } : i))
    } finally {
      setDeactivating(null)
    }
  }

  async function duplicate(item) {
    const form = itemToForm(item)
    const newCode = form.code + '_copy'
    setEditItem({ ...form, id: undefined, code: newCode, name: form.name + ' (copy)' })
  }

  function onSaved(saved, isNew) {
    if (isNew) {
      setItems(prev => [saved, ...prev])
    } else {
      setItems(prev => prev.map(i => i.id === saved.id ? saved : i))
    }
    setEditItem(null)
  }

  function onDraftApproved(item) {
    setItems(prev => [item, ...prev])
    setMainTab('catalogue')
  }

  const hasImageWarning = item =>
    item.image_url && !CUSTOMER_SAFE_STATUSES.has(item.image_approval_status)

  return (
    <div className="flex h-full bg-[#111] text-gray-200">
      {/* â”€â”€ Sidebar filters â”€â”€ */}
      <aside className="w-52 shrink-0 bg-[#161616] border-r border-[#272727] p-4 space-y-5">
        <div>
          <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-2">Search</div>
          <input
            type="search"
            placeholder="Name, supplier, codeâ€¦"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-[#111] border border-[#333] rounded px-2.5 py-1.5 text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div>
          <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-2">Category</div>
          <select
            value={filterCat}
            onChange={e => setFilterCat(e.target.value)}
            className="w-full bg-[#111] border border-[#333] rounded px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-blue-500"
          >
            <option value="">All categories</option>
            {CATEGORIES.map(c => <option key={c} value={c}>{fmt(c)}</option>)}
          </select>
        </div>

        <div>
          <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-2">Customer visible</div>
          <select
            value={filterVisible}
            onChange={e => setFilterVisible(e.target.value)}
            className="w-full bg-[#111] border border-[#333] rounded px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-blue-500"
          >
            <option value="">All</option>
            <option value="true">Visible</option>
            <option value="false">Hidden</option>
          </select>
        </div>

        <div>
          <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-2">Image status</div>
          <select
            value={filterApproval}
            onChange={e => setFilterApproval(e.target.value)}
            className="w-full bg-[#111] border border-[#333] rounded px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-blue-500"
          >
            <option value="">All statuses</option>
            {IMAGE_APPROVAL_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        <div className="pt-2">
          <button
            onClick={() => setEditItem({ ...EMPTY_ITEM })}
            className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded transition-colors"
          >
            + New item
          </button>
        </div>

        <div className="pt-1 text-[10px] text-gray-600">
          {items.length} item{items.length !== 1 ? 's' : ''}
        </div>
      </aside>

      {/* â”€â”€ Main area â”€â”€ */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header + tab bar */}
        <div className="px-6 py-4 border-b border-[#272727]">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-base font-semibold text-white">Finish Catalogue</div>
              <div className="text-xs text-gray-500 mt-0.5">Internal admin â€” manage items, images, pricing and supplier links</div>
            </div>
          </div>
          <div className="flex gap-1">
            {[
              { id: 'catalogue', label: `Catalogue (${items.length})` },
              { id: 'research', label: 'Research / Drafts' },
            ].map(t => (
              <button
                key={t.id}
                onClick={() => setMainTab(t.id)}
                className={`px-3 py-1.5 text-xs rounded font-medium transition-colors ${
                  mainTab === t.id
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {mainTab === 'research' ? (
          <ResearchPanel onApproved={onDraftApproved} />
        ) : (
        <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-gray-600 text-sm">Loadingâ€¦</div>
        ) : items.length === 0 ? (
          <div className="flex items-center justify-center h-64 text-gray-600 text-sm">No items found</div>
        ) : (
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#272727] text-[10px] text-gray-500 uppercase tracking-wider">
                <th className="text-left px-4 py-3 w-10"></th>
                <th className="text-left px-3 py-3">Name / Code</th>
                <th className="text-left px-3 py-3">Category</th>
                <th className="text-left px-3 py-3">Supplier</th>
                <th className="text-right px-3 py-3">Unit cost</th>
                <th className="text-center px-3 py-3">Visible</th>
                <th className="text-left px-3 py-3">Image status</th>
                <th className="text-center px-3 py-3">Active</th>
                <th className="px-3 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => (
                <tr
                  key={item.id}
                  className={`border-b border-[#1e1e1e] hover:bg-white/[0.02] transition-colors ${!item.is_active ? 'opacity-40' : ''}`}
                >
                  {/* Thumbnail */}
                  <td className="px-4 py-2">
                    <div className="w-9 h-9 rounded bg-[#222] overflow-hidden flex items-center justify-center border border-[#333]">
                      {CUSTOMER_SAFE_STATUSES.has(item.image_approval_status) && item.image_url
                        ? <img src={item.image_url} alt="" className="object-cover w-full h-full" />
                        : <span className="text-gray-700 text-[8px] text-center leading-tight px-1">
                            {item.image_url ? 'âš ' : 'â€“'}
                          </span>
                      }
                    </div>
                  </td>

                  {/* Name */}
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-1.5">
                      <span className="font-medium text-gray-100">{item.customer_name || item.name}</span>
                      {hasImageWarning(item) && (
                        <span title="Image not approved for customer use" className="text-amber-400 text-[10px]">âš </span>
                      )}
                    </div>
                    <div className="text-[10px] text-gray-600 mt-0.5 font-mono">{item.code}</div>
                  </td>

                  <td className="px-3 py-2 text-gray-400">{fmt(item.category)}</td>

                  <td className="px-3 py-2 text-gray-400 max-w-[140px]">
                    <div className="truncate">{item.supplier_name || 'â€”'}</div>
                  </td>

                  <td className="px-3 py-2 text-right text-gray-300">
                    {item.unit_cost != null
                      ? `${item.currency} ${item.unit_cost}${item.unit ? ` / ${item.unit}` : ''}`
                      : <span className="text-gray-600">â€”</span>
                    }
                  </td>

                  <td className="px-3 py-2 text-center">
                    {item.customer_visible
                      ? <span className="text-green-400">âœ“</span>
                      : <span className="text-gray-600">â€“</span>
                    }
                  </td>

                  <td className="px-3 py-2">{badge(item.image_approval_status)}</td>

                  <td className="px-3 py-2 text-center">
                    {item.is_active
                      ? <span className="text-green-400">âœ“</span>
                      : <span className="text-red-400">âœ—</span>
                    }
                  </td>

                  {/* Actions */}
                  <td className="px-3 py-2">
                    <div className="flex items-center justify-end gap-1">
                      <ActionBtn title="Edit" onClick={() => setEditItem(item)}>
                        <path d="M11 2l3 3-8.5 8.5L2 14l.5-3.5L11 2z" strokeLinejoin="round" />
                      </ActionBtn>
                      <ActionBtn title="Duplicate" onClick={() => duplicate(item)}>
                        <rect x="5" y="5" width="8" height="8" rx="1" />
                        <path d="M3 11V3h8" strokeLinecap="round" strokeLinejoin="round" />
                      </ActionBtn>
                      {item.supplier_url && (
                        <ActionBtn title="Supplier link" onClick={() => window.open(item.supplier_url, '_blank')}>
                          <path d="M6.5 3H3v10h10V9.5M10 2h4v4M14 2L7 9" strokeLinecap="round" strokeLinejoin="round" />
                        </ActionBtn>
                      )}
                      {item.specification_url && (
                        <ActionBtn title="Specification" onClick={() => window.open(item.specification_url, '_blank')}>
                          <path d="M9 2H4a1 1 0 00-1 1v10a1 1 0 001 1h8a1 1 0 001-1V6M9 2v4h4M9 2l4 4" strokeLinecap="round" strokeLinejoin="round" />
                        </ActionBtn>
                      )}
                      <ActionBtn title="Customer preview" onClick={() => setPreview(item)}>
                        <circle cx="8" cy="8" r="3" />
                        <path d="M1.5 8s2.5-5 6.5-5 6.5 5 6.5 5-2.5 5-6.5 5-6.5-5-6.5-5z" />
                      </ActionBtn>
                      {item.is_active && (
                        <ActionBtn
                          title="Deactivate"
                          danger
                          disabled={deactivating === item.id}
                          onClick={() => deactivate(item)}
                        >
                          <circle cx="8" cy="8" r="5.5" />
                          <path d="M5.5 5.5l5 5M10.5 5.5l-5 5" strokeLinecap="round" />
                        </ActionBtn>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        </div>
        )}
      </div>

      {/* â”€â”€ Modals â”€â”€ */}
      {editItem !== null && (
        <EditModal
          item={editItem}
          onClose={() => setEditItem(null)}
          onSaved={onSaved}
        />
      )}
      {preview && (
        <CustomerCardPreview item={preview} onClose={() => setPreview(null)} />
      )}
    </div>
  )
}

function ActionBtn({ title, onClick, children, danger, disabled }) {
  return (
    <button
      title={title}
      onClick={onClick}
      disabled={disabled}
      className={`p-1.5 rounded transition-colors disabled:opacity-30 ${
        danger
          ? 'text-gray-600 hover:text-red-400 hover:bg-red-900/20'
          : 'text-gray-600 hover:text-gray-300 hover:bg-white/5'
      }`}
    >
      <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.4">
        {children}
      </svg>
    </button>
  )
}

