import { useState, useEffect, useRef } from 'react'
import { apiFetch } from '../api/client'

// ── Categories ─────────────────────────────────────────────────────────────────

const CATEGORIES = [
  { value: 'insulation',          label: 'Insulation' },
  { value: 'structural_timber',   label: 'Structural Timber' },
  { value: 'board_sheet',         label: 'Board & Sheet' },
  { value: 'cladding',            label: 'Cladding' },
  { value: 'roofing',             label: 'Roofing' },
  { value: 'membrane_vcl',        label: 'Membrane / VCL' },
  { value: 'fixings_fasteners',   label: 'Fixings & Fasteners' },
  { value: 'glazing_windows',     label: 'Glazing & Windows' },
  { value: 'doors',               label: 'Doors' },
  { value: 'electrical',          label: 'Electrical' },
  { value: 'plumbing',            label: 'Plumbing' },
  { value: 'finishes_flooring',   label: 'Finishes & Flooring' },
  { value: 'furniture_fittings',  label: 'Furniture & Fittings' },
  { value: 'tools_plant',         label: 'Tools & Plant' },
  { value: 'other',               label: 'Other' },
]

function categoryLabel(value) {
  return CATEGORIES.find(c => c.value === value)?.label ?? value ?? '—'
}

// ── Shared UI ──────────────────────────────────────────────────────────────────

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

function SelectField({ label, value, onChange, options, placeholder = '— None —' }) {
  return (
    <div>
      <label className="block text-[11px] font-medium text-gray-500 mb-1">{label}</label>
      <select value={value ?? ''} onChange={e => onChange(e.target.value)}
        className="w-full bg-white border border-gray-200 rounded px-2.5 py-1.5 text-sm text-gray-900 focus:outline-none focus:border-gray-500">
        <option value="">{placeholder}</option>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  )
}

function Btn({ onClick, children, variant = 'primary', disabled = false, small = false }) {
  const base = `rounded font-medium transition-colors disabled:opacity-40 ${small ? 'px-2 py-1 text-xs' : 'px-3 py-1.5 text-sm'}`
  const variants = {
    primary:   'bg-gray-900 text-white hover:bg-gray-700',
    secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200',
    danger:    'bg-red-50 text-red-600 hover:bg-red-100',
    amber:     'bg-amber-50 text-amber-700 hover:bg-amber-100',
    success:   'bg-green-600 text-white hover:bg-green-700',
  }
  return <button type="button" className={`${base} ${variants[variant]}`} onClick={onClick} disabled={disabled}>{children}</button>
}

// ── Supplier form (add / edit) ─────────────────────────────────────────────────

const EMPTY = {
  name: '', contact_name: '', email: '', phone: '', website: '',
  address: '', category: '', lead_time_days: '', payment_terms: '',
  delivery_terms: '', currency: 'EUR', notes: '',
}

function SupplierFormModal({ initial, onClose, onSaved }) {
  const [form, setForm] = useState(initial ? {
    ...EMPTY,
    ...initial,
    lead_time_days: initial.lead_time_days ?? '',
  } : EMPTY)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')

  const set = k => v => setForm(f => ({ ...f, [k]: v }))
  const isEdit = !!initial?.id

  async function handleSave() {
    if (!form.name.trim()) { setErr('Name is required'); return }
    setSaving(true)
    setErr('')
    try {
      const body = {
        ...form,
        lead_time_days: form.lead_time_days !== '' ? parseInt(form.lead_time_days) : null,
        category: form.category || null,
      }
      const result = isEdit
        ? await apiFetch(`/suppliers/${initial.id}`, { method: 'PUT', body: JSON.stringify(body) })
        : await apiFetch('/suppliers', { method: 'POST', body: JSON.stringify(body) })
      onSaved(result, isEdit)
    } catch (e) {
      setErr(e.message ?? 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title={isEdit ? 'Edit Supplier' : 'Add Supplier'}
      subtitle={isEdit ? initial.name : undefined}
      onClose={onClose}
      footer={
        <>
          {err && <span className="text-xs text-red-500 mr-auto">{err}</span>}
          <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
          <Btn onClick={handleSave} disabled={saving}>{saving ? 'Saving…' : isEdit ? 'Save Changes' : 'Add Supplier'}</Btn>
        </>
      }
    >
      <Field label="Supplier Name *" value={form.name} onChange={set('name')} placeholder="e.g. Rockwool Ireland" />
      <div className="grid grid-cols-2 gap-3">
        <Field label="Contact Name" value={form.contact_name} onChange={set('contact_name')} placeholder="Sales rep" />
        <Field label="Email" value={form.email} onChange={set('email')} type="email" placeholder="sales@supplier.com" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Phone" value={form.phone} onChange={set('phone')} placeholder="+353 1 234 5678" />
        <Field label="Website" value={form.website} onChange={set('website')} placeholder="https://supplier.com" />
      </div>
      <SelectField label="Category" value={form.category} onChange={set('category')} options={CATEGORIES} />
      <div className="grid grid-cols-3 gap-3">
        <Field label="Lead Time (days)" value={form.lead_time_days} onChange={set('lead_time_days')} type="number" placeholder="5" />
        <Field label="Payment Terms" value={form.payment_terms} onChange={set('payment_terms')} placeholder="30 days" />
        <Field label="Currency" value={form.currency} onChange={set('currency')} placeholder="EUR" />
      </div>
      <Field label="Delivery Terms" value={form.delivery_terms} onChange={set('delivery_terms')} placeholder="Ex-works / DDP / etc." />
      <Field label="Address" value={form.address} onChange={set('address')} textarea placeholder="Full address" />
      <Field label="Notes" value={form.notes} onChange={set('notes')} textarea placeholder="Account number, special terms, etc." />
    </Modal>
  )
}

// ── Import modal ───────────────────────────────────────────────────────────────

const CSV_COLUMNS = ['name','contact_name','email','phone','website','address','category','lead_time_days','payment_terms','delivery_terms','currency','notes']

function parseCSV(text) {
  const lines = text.trim().split('\n').filter(l => l.trim())
  if (lines.length < 2) return { headers: [], rows: [] }
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''))
  const rows = lines.slice(1).map(line => {
    const vals = line.split(',').map(v => v.trim().replace(/^"|"$/g, ''))
    const obj = {}
    headers.forEach((h, i) => { obj[h] = vals[i] ?? '' })
    return obj
  })
  return { headers, rows }
}

function ImportModal({ onClose, onImported }) {
  const [step, setStep] = useState('upload') // upload | map | preview | result
  const [csvText, setCsvText] = useState('')
  const [parsed, setParsed] = useState(null)
  const [mapping, setMapping] = useState({})
  const [preview, setPreview] = useState([])
  const [result, setResult] = useState(null)
  const [importing, setImporting] = useState(false)
  const [err, setErr] = useState('')
  const fileRef = useRef()

  function handleFile(e) {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = ev => setCsvText(ev.target.result)
    reader.readAsText(file)
  }

  function handleParse() {
    setErr('')
    const { headers, rows } = parseCSV(csvText)
    if (!headers.length) { setErr('Could not parse CSV — check the format.'); return }
    setParsed({ headers, rows })
    // Auto-map: try to match header names to known fields
    const autoMap = {}
    CSV_COLUMNS.forEach(col => {
      const match = headers.find(h =>
        h.toLowerCase().replace(/[\s_-]/g, '') === col.toLowerCase().replace(/[\s_-]/g, '') ||
        h.toLowerCase().includes(col.toLowerCase().split('_')[0])
      )
      if (match) autoMap[col] = match
    })
    setMapping(autoMap)
    setStep('map')
  }

  function handlePreview() {
    if (!mapping.name) { setErr('You must map the "Name" column.'); return }
    setErr('')
    const rows = parsed.rows.map(row => {
      const obj = {}
      CSV_COLUMNS.forEach(col => {
        obj[col] = mapping[col] ? (row[mapping[col]] ?? '') : ''
      })
      return obj
    }).filter(r => r.name.trim())
    setPreview(rows)
    setStep('preview')
  }

  async function handleImport() {
    setImporting(true)
    setErr('')
    try {
      const body = preview.map(r => ({
        name: r.name,
        contact_name: r.contact_name || null,
        email: r.email || null,
        phone: r.phone || null,
        website: r.website || null,
        address: r.address || null,
        category: r.category || null,
        lead_time_days: r.lead_time_days ? parseInt(r.lead_time_days) : null,
        payment_terms: r.payment_terms || null,
        delivery_terms: r.delivery_terms || null,
        currency: r.currency || 'EUR',
        notes: r.notes || null,
        is_active: true,
      }))
      const res = await apiFetch('/suppliers/import', { method: 'POST', body: JSON.stringify(body) })
      setResult(res)
      setStep('result')
      onImported(res.suppliers)
    } catch (e) {
      setErr(e.message ?? 'Import failed')
    } finally {
      setImporting(false)
    }
  }

  return (
    <Modal title="Import Suppliers" subtitle="CSV file" onClose={onClose} footer={
      <>
        {err && <span className="text-xs text-red-500 mr-auto">{err}</span>}
        {step === 'upload' && <><Btn variant="secondary" onClick={onClose}>Cancel</Btn><Btn onClick={handleParse} disabled={!csvText.trim()}>Parse CSV</Btn></>}
        {step === 'map' && <><Btn variant="secondary" onClick={() => setStep('upload')}>Back</Btn><Btn onClick={handlePreview}>Preview</Btn></>}
        {step === 'preview' && <><Btn variant="secondary" onClick={() => setStep('map')}>Back</Btn><Btn onClick={handleImport} disabled={importing || !preview.length}>{importing ? 'Importing…' : `Import ${preview.length} suppliers`}</Btn></>}
        {step === 'result' && <Btn onClick={onClose}>Done</Btn>}
      </>
    }>
      {step === 'upload' && (
        <div className="space-y-3">
          <p className="text-xs text-gray-500">Upload a CSV file with your supplier list, or paste CSV text below. First row must be column headers.</p>
          <input ref={fileRef} type="file" accept=".csv,.txt" onChange={handleFile} className="text-xs text-gray-600" />
          <div>
            <label className="block text-[11px] font-medium text-gray-500 mb-1">Or paste CSV text</label>
            <textarea value={csvText} onChange={e => setCsvText(e.target.value)} rows={8}
              placeholder={'Name,Email,Phone,Category\nRockwool,sales@rockwool.com,+353 1 234,insulation'}
              className="w-full bg-white border border-gray-200 rounded px-2.5 py-1.5 text-xs font-mono text-gray-900 focus:outline-none focus:border-gray-500 resize-none" />
          </div>
        </div>
      )}

      {step === 'map' && parsed && (
        <div className="space-y-2">
          <p className="text-xs text-gray-500">Map your CSV columns to supplier fields. "Name" is required.</p>
          {CSV_COLUMNS.map(col => (
            <div key={col} className="flex items-center gap-3">
              <span className="text-[11px] font-medium text-gray-600 w-36 shrink-0 capitalize">{col.replace(/_/g, ' ')}</span>
              <select value={mapping[col] ?? ''} onChange={e => setMapping(m => ({ ...m, [col]: e.target.value || undefined }))}
                className="flex-1 bg-white border border-gray-200 rounded px-2 py-1 text-xs text-gray-900 focus:outline-none focus:border-gray-500">
                <option value="">— skip —</option>
                {parsed.headers.map(h => <option key={h} value={h}>{h}</option>)}
              </select>
            </div>
          ))}
        </div>
      )}

      {step === 'preview' && (
        <div className="space-y-2">
          <p className="text-xs text-gray-500">{preview.length} suppliers ready to import. Duplicates (same name or email) will be skipped.</p>
          <div className="max-h-64 overflow-y-auto border border-gray-100 rounded">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="text-left px-3 py-2 text-gray-500 font-medium">Name</th>
                  <th className="text-left px-3 py-2 text-gray-500 font-medium">Email</th>
                  <th className="text-left px-3 py-2 text-gray-500 font-medium">Category</th>
                </tr>
              </thead>
              <tbody>
                {preview.map((r, i) => (
                  <tr key={i} className="border-t border-gray-50">
                    <td className="px-3 py-1.5 text-gray-800">{r.name}</td>
                    <td className="px-3 py-1.5 text-gray-500">{r.email || '—'}</td>
                    <td className="px-3 py-1.5 text-gray-500">{categoryLabel(r.category)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {step === 'result' && result && (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-green-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-green-600">{result.created}</div>
              <div className="text-[11px] text-green-600 mt-0.5">Created</div>
            </div>
            <div className="bg-amber-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-amber-600">{result.skipped_duplicates}</div>
              <div className="text-[11px] text-amber-600 mt-0.5">Skipped (duplicates)</div>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-red-500">{result.errors.length}</div>
              <div className="text-[11px] text-red-500 mt-0.5">Errors</div>
            </div>
          </div>
          {result.errors.length > 0 && (
            <div className="bg-gray-50 rounded p-3 space-y-1">
              {result.errors.map((e, i) => <p key={i} className="text-xs text-red-500">{e}</p>)}
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}

// ── Supplier detail modal ──────────────────────────────────────────────────────

function SupplierDetailModal({ supplier, onClose, onEdit, onArchive, onReactivate }) {
  return (
    <Modal title={supplier.name} subtitle={categoryLabel(supplier.category)} onClose={onClose} footer={
      <div className="flex gap-2 w-full">
        {supplier.is_active
          ? <Btn variant="amber" onClick={() => onArchive(supplier)}>Archive</Btn>
          : <Btn variant="success" onClick={() => onReactivate(supplier)}>Reactivate</Btn>
        }
        <div className="ml-auto flex gap-2">
          <Btn variant="secondary" onClick={onClose}>Close</Btn>
          <Btn onClick={() => onEdit(supplier)}>Edit</Btn>
        </div>
      </div>
    }>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
        <InfoRow label="Status">{supplier.is_active ? <span className="text-green-600 font-medium">Active</span> : <span className="text-gray-400">Archived</span>}</InfoRow>
        <InfoRow label="Category">{categoryLabel(supplier.category)}</InfoRow>
        <InfoRow label="Contact">{supplier.contact_name ?? '—'}</InfoRow>
        <InfoRow label="Email">{supplier.email ? <a href={`mailto:${supplier.email}`} className="text-blue-500 hover:underline">{supplier.email}</a> : '—'}</InfoRow>
        <InfoRow label="Phone">{supplier.phone ?? '—'}</InfoRow>
        <InfoRow label="Website">{supplier.website ? <a href={supplier.website} target="_blank" rel="noreferrer" className="text-blue-500 hover:underline">Visit ↗</a> : '—'}</InfoRow>
        <InfoRow label="Lead Time">{supplier.lead_time_days != null ? `${supplier.lead_time_days} days` : '—'}</InfoRow>
        <InfoRow label="Currency">{supplier.currency}</InfoRow>
        <InfoRow label="Payment Terms">{supplier.payment_terms ?? '—'}</InfoRow>
        <InfoRow label="Delivery Terms">{supplier.delivery_terms ?? '—'}</InfoRow>
      </div>
      {supplier.address && <div className="mt-2 bg-gray-50 rounded p-3 text-xs text-gray-600 whitespace-pre-wrap">{supplier.address}</div>}
      {supplier.notes && <div className="mt-2 bg-gray-50 rounded p-3 text-xs text-gray-600 whitespace-pre-wrap">{supplier.notes}</div>}
    </Modal>
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

// ── Main page ──────────────────────────────────────────────────────────────────

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showArchived, setShowArchived] = useState(false)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [editing, setEditing] = useState(null)
  const [viewing, setViewing] = useState(null)

  function load(includeArchived) {
    setLoading(true)
    apiFetch(`/suppliers?include_archived=${includeArchived}`)
      .then(setSuppliers)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(showArchived) }, [showArchived])

  function handleSaved(s, isEdit) {
    if (isEdit) {
      setSuppliers(prev => prev.map(x => x.id === s.id ? s : x))
      setViewing(s)
    } else {
      setSuppliers(prev => [...prev, s])
    }
    setEditing(null)
    setShowAdd(false)
  }

  function handleImported(newSuppliers) {
    setSuppliers(prev => [...prev, ...newSuppliers])
    setShowImport(false)
  }

  async function handleArchive(s) {
    const updated = await apiFetch(`/suppliers/${s.id}/archive`, { method: 'PATCH' })
    setSuppliers(prev => showArchived ? prev.map(x => x.id === s.id ? updated : x) : prev.filter(x => x.id !== s.id))
    setViewing(null)
  }

  async function handleReactivate(s) {
    const updated = await apiFetch(`/suppliers/${s.id}/reactivate`, { method: 'PATCH' })
    setSuppliers(prev => prev.map(x => x.id === s.id ? updated : x))
    setViewing(updated)
  }

  const filtered = suppliers.filter(s => {
    const matchSearch = !search ||
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      (s.contact_name ?? '').toLowerCase().includes(search.toLowerCase()) ||
      (s.email ?? '').toLowerCase().includes(search.toLowerCase())
    const matchCat = !categoryFilter || s.category === categoryFilter
    return matchSearch && matchCat
  })

  const activeCount = suppliers.filter(s => s.is_active).length
  const archivedCount = suppliers.filter(s => !s.is_active).length

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Suppliers</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {activeCount} active{archivedCount > 0 ? `, ${archivedCount} archived` : ''}
          </p>
        </div>
        <div className="flex gap-2">
          <Btn variant="secondary" onClick={() => setShowImport(true)}>Import CSV</Btn>
          <Btn onClick={() => setShowAdd(true)}>+ Add Supplier</Btn>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-5">
        <input
          type="text" value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search by name, contact, email…"
          className="flex-1 max-w-xs bg-white border border-gray-200 rounded px-3 py-1.5 text-sm text-gray-900 focus:outline-none focus:border-gray-500"
        />
        <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}
          className="bg-white border border-gray-200 rounded px-2.5 py-1.5 text-sm text-gray-700 focus:outline-none focus:border-gray-500">
          <option value="">All categories</option>
          {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
        <button onClick={() => setShowArchived(v => !v)}
          className={`px-3 py-1.5 rounded text-xs font-medium transition-colors border ${showArchived ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-500 border-gray-200 hover:text-gray-800'}`}>
          {showArchived ? 'Showing archived' : 'Show archived'}
        </button>
      </div>

      {/* List */}
      {loading ? (
        <div className="flex items-center justify-center h-48 text-sm text-gray-400">Loading suppliers…</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-sm text-gray-400">
          {suppliers.length === 0 ? 'No suppliers yet. Add one or import from CSV.' : 'No suppliers match that filter.'}
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-100 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3 text-[11px] font-medium text-gray-500 uppercase tracking-wide">Supplier</th>
                <th className="text-left px-4 py-3 text-[11px] font-medium text-gray-500 uppercase tracking-wide">Category</th>
                <th className="text-left px-4 py-3 text-[11px] font-medium text-gray-500 uppercase tracking-wide">Contact</th>
                <th className="text-left px-4 py-3 text-[11px] font-medium text-gray-500 uppercase tracking-wide">Lead Time</th>
                <th className="text-left px-4 py-3 text-[11px] font-medium text-gray-500 uppercase tracking-wide">Terms</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(s => (
                <tr key={s.id} className={`border-t border-gray-50 hover:bg-gray-50 transition-colors ${!s.is_active ? 'opacity-50' : ''}`}>
                  <td className="px-4 py-3">
                    <button onClick={() => setViewing(s)} className="text-left">
                      <div className="font-medium text-gray-900">{s.name}</div>
                      {s.email && <div className="text-[11px] text-gray-400">{s.email}</div>}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">{categoryLabel(s.category)}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{s.contact_name ?? '—'}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{s.lead_time_days != null ? `${s.lead_time_days}d` : '—'}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{s.payment_terms ?? '—'}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Btn small variant="secondary" onClick={() => { setEditing(s); setViewing(null) }}>Edit</Btn>
                      {s.is_active
                        ? <Btn small variant="amber" onClick={() => handleArchive(s)}>Archive</Btn>
                        : <Btn small variant="success" onClick={() => handleReactivate(s)}>Reactivate</Btn>
                      }
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showAdd && <SupplierFormModal onClose={() => setShowAdd(false)} onSaved={handleSaved} />}
      {editing && <SupplierFormModal initial={editing} onClose={() => setEditing(null)} onSaved={handleSaved} />}
      {showImport && <ImportModal onClose={() => setShowImport(false)} onImported={handleImported} />}
      {viewing && !editing && (
        <SupplierDetailModal
          supplier={viewing}
          onClose={() => setViewing(null)}
          onEdit={s => { setEditing(s); setViewing(null) }}
          onArchive={handleArchive}
          onReactivate={handleReactivate}
        />
      )}
    </div>
  )
}
