import { useState, useEffect } from 'react'
import { apiFetch } from '../api/client'

// ── Evidence badge ─────────────────────────────────────────────────────────────

const EVIDENCE_CFG = {
  verified: { dot: 'bg-green-500', cls: 'bg-green-50 text-green-700 border-green-200',  label: 'Verified' },
  partial:  { dot: 'bg-amber-400', cls: 'bg-amber-50 text-amber-700 border-amber-200',  label: 'Partial'  },
  missing:  { dot: 'bg-gray-300',  cls: 'bg-gray-100 text-gray-500 border-gray-200',    label: 'Missing'  },
}

function EvidenceBadge({ status }) {
  const cfg = EVIDENCE_CFG[status] ?? EVIDENCE_CFG.missing
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border font-medium ${cfg.cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  )
}

function LinkCell({ url, label }) {
  if (!url) return <span className="text-[11px] text-gray-300">—</span>
  return (
    <a href={url} target="_blank" rel="noreferrer"
      className="text-[11px] text-blue-500 hover:text-blue-700 hover:underline">
      {label} ↗
    </a>
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

function Field({ label, value, onChange, placeholder = '', type = 'text', hint }) {
  return (
    <div>
      <label className="block text-[11px] font-medium text-gray-500 mb-1">{label}</label>
      <input type={type} value={value} placeholder={placeholder}
        onChange={e => onChange(e.target.value)}
        className="w-full bg-white border border-gray-200 rounded px-2.5 py-1.5 text-sm text-gray-900 focus:outline-none focus:border-gray-500 transition-colors" />
      {hint && <p className="text-[10px] text-gray-400 mt-0.5">{hint}</p>}
    </div>
  )
}

// ── Add material modal ─────────────────────────────────────────────────────────

const EMPTY_FORM = {
  name: '', manufacturer: '', supplier_name: '', supplier_ref: '',
  spec_ref: '', lambda_W_mK: '', density_kg_m3: '', fire_euroclass: '',
  supplier_url: '', datasheet_url: '', dop_url: '',
  unit: 'm2', currency: 'EUR',
  material_class: 'manufactured',
}

function AddMaterialModal({ onClose, onAdded }) {
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const save = async () => {
    if (!form.name.trim()) { setError('Name is required.'); return }
    setSaving(true); setError(null)
    try {
      const payload = {
        name:           form.name.trim(),
        manufacturer:   form.manufacturer   || null,
        supplier_name:  form.supplier_name  || null,
        supplier_ref:   form.supplier_ref   || null,
        spec_ref:       form.spec_ref       || null,
        lambda_W_mK:    form.lambda_W_mK    ? parseFloat(form.lambda_W_mK)    : null,
        density_kg_m3:  form.density_kg_m3  ? parseFloat(form.density_kg_m3)  : null,
        fire_euroclass: form.fire_euroclass || null,
        supplier_url:   form.supplier_url   || null,
        datasheet_url:  form.datasheet_url  || null,
        dop_url:        form.dop_url        || null,
        unit:           form.unit || 'm2',
        currency:       form.currency || 'EUR',
        properties: { material_class: form.material_class },
      }
      const created = await apiFetch('/materials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      onAdded(created)
    } catch (e) { setError(e.message) }
    finally { setSaving(false) }
  }

  return (
    <Modal
      title="Add Material"
      subtitle="New entry in the material library"
      onClose={onClose}
      footer={
        <>
          <button type="button" onClick={onClose}
            className="px-3 py-1.5 text-xs text-gray-600 border border-gray-200 rounded hover:border-gray-400 transition-colors">
            Cancel
          </button>
          <button type="button" onClick={save} disabled={saving}
            className="px-4 py-1.5 text-xs bg-gray-900 text-white rounded hover:bg-gray-700 transition-colors disabled:opacity-40">
            {saving ? 'Saving…' : 'Add material'}
          </button>
        </>
      }
    >
      <Field label="Material name *" value={form.name} onChange={v => set('name', v)} placeholder="e.g. Rockwool Flexibatts 100mm" />

      <div className="grid grid-cols-2 gap-3">
        <Field label="Manufacturer"   value={form.manufacturer}  onChange={v => set('manufacturer', v)}  placeholder="e.g. Rockwool" />
        <Field label="Supplier name"  value={form.supplier_name} onChange={v => set('supplier_name', v)} placeholder="e.g. prof.lv" />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Supplier ref"   value={form.supplier_ref}  onChange={v => set('supplier_ref', v)}  placeholder="e.g. RW-FLEX-100" />
        <Field label="Spec / standard" value={form.spec_ref}     onChange={v => set('spec_ref', v)}      placeholder="e.g. EN 13162" />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <Field label="λ W/mK"          value={form.lambda_W_mK}   onChange={v => set('lambda_W_mK', v)}   type="number" placeholder="0.034" />
        <Field label="Density kg/m³"   value={form.density_kg_m3} onChange={v => set('density_kg_m3', v)} type="number" placeholder="40" />
        <Field label="Fire Euroclass"  value={form.fire_euroclass} onChange={v => set('fire_euroclass', v)} placeholder="A1 / B …" />
      </div>

      <Field label="Supplier URL"   value={form.supplier_url}  onChange={v => set('supplier_url', v)}  placeholder="https://…" />
      <Field label="Datasheet URL"  value={form.datasheet_url} onChange={v => set('datasheet_url', v)} placeholder="https://…" />
      <Field label="DoP / Certificate URL" value={form.dop_url} onChange={v => set('dop_url', v)}      placeholder="https://… (optional)" />

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-[11px] font-medium text-gray-500 mb-1">Default unit</label>
          <select value={form.unit} onChange={e => set('unit', e.target.value)}
            className="w-full bg-white border border-gray-200 rounded px-2.5 py-1.5 text-sm text-gray-900 focus:outline-none focus:border-gray-500">
            {['m2','lm','m3','pcs','kg'].map(u => <option key={u}>{u}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-[11px] font-medium text-gray-500 mb-1">Category</label>
          <select value={form.material_class} onChange={e => set('material_class', e.target.value)}
            className="w-full bg-white border border-gray-200 rounded px-2.5 py-1.5 text-sm text-gray-900 focus:outline-none focus:border-gray-500">
            <option value="manufactured">Manufactured product</option>
            <option value="building">Building / site material</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>
      )}
    </Modal>
  )
}

// ── Edit evidence modal ────────────────────────────────────────────────────────

function EvidenceModal({ mat, onClose, onSaved }) {
  const [form, setForm] = useState({
    manufacturer:     mat.manufacturer     ?? '',
    supplier_name:    mat.supplier_name    ?? '',
    supplier_url:     mat.supplier_url     ?? '',
    datasheet_url:    mat.datasheet_url    ?? '',
    dop_url:          mat.dop_url          ?? '',
    fire_euroclass:   mat.fire_euroclass   ?? '',
    density_kg_m3:    mat.density_kg_m3    ?? '',
    price_source_url: mat.price_source_url ?? '',
    price_checked_at: mat.price_checked_at ?? '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError]   = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const save = async () => {
    setSaving(true); setError(null)
    try {
      const payload = { ...form }
      if (payload.density_kg_m3 !== '') payload.density_kg_m3 = parseFloat(payload.density_kg_m3)
      else delete payload.density_kg_m3
      const updated = await apiFetch(`/materials/${mat.id}/evidence`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      onSaved(updated)
    } catch (e) { setError(e.message) }
    finally { setSaving(false) }
  }

  return (
    <Modal
      title={mat.name}
      subtitle={mat.spec_ref || 'Edit evidence & supplier links'}
      onClose={onClose}
      footer={
        <>
          <button type="button" onClick={onClose}
            className="px-3 py-1.5 text-xs text-gray-600 border border-gray-200 rounded hover:border-gray-400 transition-colors">
            Cancel
          </button>
          <button type="button" onClick={save} disabled={saving}
            className="px-4 py-1.5 text-xs bg-gray-900 text-white rounded hover:bg-gray-700 transition-colors disabled:opacity-40">
            {saving ? 'Saving…' : 'Save changes'}
          </button>
        </>
      }
    >
      <Field label="Manufacturer"        value={form.manufacturer}     onChange={v => set('manufacturer', v)} />
      <Field label="Supplier name"       value={form.supplier_name}    onChange={v => set('supplier_name', v)} />
      <Field label="Supplier URL"        value={form.supplier_url}     onChange={v => set('supplier_url', v)}     placeholder="https://…" />
      <Field label="Data sheet URL"      value={form.datasheet_url}    onChange={v => set('datasheet_url', v)}    placeholder="https://…" />
      <Field label="DoP / Certificate"   value={form.dop_url}          onChange={v => set('dop_url', v)}          placeholder="https://… (optional)" />
      <Field label="Fire Euroclass"      value={form.fire_euroclass}   onChange={v => set('fire_euroclass', v)}   placeholder="A1 / A2 / B / C …" />
      <div className="grid grid-cols-2 gap-3">
        <Field label="Density (kg/m³)"   value={form.density_kg_m3}    onChange={v => set('density_kg_m3', v)}    type="number" />
        <Field label="Price checked date" value={form.price_checked_at} onChange={v => set('price_checked_at', v)} type="date" />
      </div>
      <Field label="Price source URL"    value={form.price_source_url} onChange={v => set('price_source_url', v)} placeholder="https://…" />
      {error && (
        <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>
      )}
    </Modal>
  )
}

// ── Delete confirmation ────────────────────────────────────────────────────────

function DeleteConfirm({ mat, onClose, onDeleted }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const confirm = async () => {
    setBusy(true); setError(null)
    try {
      await apiFetch(`/materials/${mat.id}`, { method: 'DELETE' })
      onDeleted(mat.id)
    } catch (e) { setError(e.message); setBusy(false) }
  }

  return (
    <Modal
      title="Remove material"
      onClose={onClose}
      footer={
        <>
          <button type="button" onClick={onClose}
            className="px-3 py-1.5 text-xs text-gray-600 border border-gray-200 rounded hover:border-gray-400 transition-colors">
            Cancel
          </button>
          <button type="button" onClick={confirm} disabled={busy}
            className="px-4 py-1.5 text-xs bg-red-600 text-white rounded hover:bg-red-700 transition-colors disabled:opacity-40">
            {busy ? 'Removing…' : 'Remove'}
          </button>
        </>
      }
    >
      <p className="text-sm text-gray-700">
        Remove <span className="font-semibold">{mat.name}</span> from the library?
      </p>
      <p className="text-xs text-gray-400">
        This cannot be undone. Materials used in a build-up cannot be removed — remove them from all build-ups first.
      </p>
      {error && (
        <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>
      )}
    </Modal>
  )
}

// ── Grouping ───────────────────────────────────────────────────────────────────

function groupMaterials(materials) {
  const manufactured = materials.filter(m => (m.properties?.material_class ?? 'manufactured') !== 'building')
  const building     = materials.filter(m => m.properties?.material_class === 'building')
  return [
    { id: 'manufactured', label: 'Manufactured Products',      note: 'CE marked — datasheet & DoP required',                items: manufactured },
    { id: 'building',     label: 'Building & Site Materials',   note: 'Specify by grade / standard — no manufacturer datasheet', items: building },
  ].filter(g => g.items.length > 0)
}

function SectionHeader({ label, count, note }) {
  return (
    <tr>
      <td colSpan={9} className="pt-6 pb-2 px-4">
        <div className="flex items-baseline gap-3 border-b border-gray-200 pb-2">
          <span className="text-[11px] font-semibold text-gray-700 uppercase tracking-widest">{label}</span>
          <span className="text-[10px] text-gray-400">{count} item{count !== 1 ? 's' : ''}</span>
          {note && <span className="text-[10px] text-gray-400 italic ml-auto">{note}</span>}
        </div>
      </td>
    </tr>
  )
}

// ── Material row ───────────────────────────────────────────────────────────────

function MaterialRow({ m, onEdit, onDelete }) {
  const notes      = m.properties?.notes
  const isBuilding = m.properties?.material_class === 'building'

  return (
    <tr className={`border-b border-gray-100 hover:bg-gray-50/60 transition-colors ${isBuilding ? 'bg-stone-50/40' : ''}`}>
      <td className="py-3 px-4 min-w-[220px]">
        <div className="font-medium text-gray-900 text-[12px] leading-snug">{m.name}</div>
        {m.spec_ref && <div className="text-[10px] text-gray-500 font-mono mt-0.5">{m.spec_ref}</div>}
        {m.supplier_name && (
          <div className={`text-[10px] mt-0.5 ${isBuilding ? 'text-blue-600' : 'text-gray-400'}`}>{m.supplier_name}</div>
        )}
        {notes && (
          <div className="mt-1.5 text-[10px] text-gray-500 italic leading-relaxed border-l-2 border-amber-300 pl-2 bg-amber-50/50 py-0.5 rounded-r">
            {notes}
          </div>
        )}
      </td>
      <td className="py-3 px-3 text-[11px] text-gray-600 align-top">
        {m.manufacturer ?? <span className="text-gray-300">—</span>}
      </td>
      <td className="py-3 px-3 text-right text-[11px] tabular-nums text-gray-700 align-top">
        {m.lambda_W_mK != null ? m.lambda_W_mK.toFixed(3) : <span className="text-gray-300">—</span>}
      </td>
      <td className="py-3 px-3 align-top">
        {m.fire_euroclass
          ? <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 rounded border border-gray-200 font-mono">{m.fire_euroclass}</span>
          : <span className="text-gray-300 text-[11px]">—</span>}
      </td>
      <td className="py-3 px-3 align-top">
        {isBuilding && !m.supplier_url
          ? <span className="text-[10px] text-blue-500 italic">Local merchants</span>
          : <LinkCell url={m.supplier_url} label="Supplier" />}
      </td>
      <td className="py-3 px-3 align-top">
        {isBuilding && !m.datasheet_url
          ? <span className="text-[10px] text-gray-400 italic">Grade spec</span>
          : <LinkCell url={m.datasheet_url} label="Datasheet" />}
      </td>
      <td className="py-3 px-3 align-top">
        {m.dop_url
          ? <a href={m.dop_url} target="_blank" rel="noreferrer" className="text-[11px] text-blue-500 hover:text-blue-700 hover:underline">DoP ↗</a>
          : <span className="text-[11px] text-gray-300">—</span>}
      </td>
      <td className="py-3 px-3 align-top"><EvidenceBadge status={m.evidence_status} /></td>
      <td className="py-3 px-3 align-top">
        <div className="flex items-center gap-1">
          <button type="button" onClick={() => onEdit(m)}
            className="text-[10px] px-2 py-1 border border-gray-200 rounded text-gray-500 hover:border-gray-400 hover:text-gray-800 transition-colors">
            Edit
          </button>
          <button type="button" onClick={() => onDelete(m)}
            className="text-[10px] px-2 py-1 border border-red-100 rounded text-red-400 hover:border-red-300 hover:text-red-600 transition-colors">
            ✕
          </button>
        </div>
      </td>
    </tr>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function MaterialLibraryPage() {
  const [materials,   setMaterials]   = useState([])
  const [editTarget,  setEditTarget]  = useState(null)
  const [deleteTarget,setDeleteTarget]= useState(null)
  const [showAdd,     setShowAdd]     = useState(false)
  const [filter,      setFilter]      = useState('')

  useEffect(() => {
    apiFetch('/materials').then(setMaterials).catch(console.error)
  }, [])

  const visible = materials.filter(m => !m.properties?.hide_from_library)

  const filtered = visible.filter(m =>
    !filter ||
    m.name.toLowerCase().includes(filter.toLowerCase()) ||
    (m.manufacturer ?? '').toLowerCase().includes(filter.toLowerCase()) ||
    (m.spec_ref ?? '').toLowerCase().includes(filter.toLowerCase())
  )

  const summary = {
    verified: visible.filter(m => m.evidence_status === 'verified').length,
    partial:  visible.filter(m => m.evidence_status === 'partial').length,
    missing:  visible.filter(m => m.evidence_status === 'missing').length,
  }

  const groups = groupMaterials(filtered)

  const handleSaved   = updated => setMaterials(ms => ms.map(m => m.id === updated.id ? updated : m))
  const handleAdded   = created => { setMaterials(ms => [...ms, created]); setShowAdd(false) }
  const handleDeleted = id      => setMaterials(ms => ms.filter(m => m.id !== id))

  return (
    <div className="flex flex-col h-full overflow-hidden bg-gray-50">

      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-5 shrink-0">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-[15px] font-semibold text-gray-900">Material Library</h1>
            <p className="text-[11px] text-gray-400 mt-0.5">
              Supplier links, datasheets &amp; compliance evidence for all build-up materials
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex gap-2 text-[11px]">
              <span className="inline-flex items-center gap-1.5 bg-green-50 text-green-700 border border-green-200 rounded-full px-2.5 py-1">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500" />{summary.verified} verified
              </span>
              <span className="inline-flex items-center gap-1.5 bg-amber-50 text-amber-700 border border-amber-200 rounded-full px-2.5 py-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />{summary.partial} partial
              </span>
              <span className="inline-flex items-center gap-1.5 bg-gray-100 text-gray-500 border border-gray-200 rounded-full px-2.5 py-1">
                <span className="w-1.5 h-1.5 rounded-full bg-gray-300" />{summary.missing} missing
              </span>
            </div>
            <button type="button" onClick={() => setShowAdd(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 text-white text-xs rounded-lg hover:bg-gray-700 transition-colors">
              <span className="text-base leading-none">+</span> Add material
            </button>
          </div>
        </div>
        <input
          type="search" value={filter} onChange={e => setFilter(e.target.value)}
          placeholder="Filter by name, manufacturer, or spec…"
          className="w-80 bg-gray-50 border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-gray-500 focus:bg-white transition-colors"
        />
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs border-collapse">
          <thead className="sticky top-0 bg-white border-b border-gray-200 z-10 shadow-sm">
            <tr>
              <th className="text-left py-2.5 px-4 font-medium text-gray-400 text-[10px] uppercase tracking-wide">Material / Specification</th>
              <th className="text-left py-2.5 px-3 font-medium text-gray-400 text-[10px] uppercase tracking-wide">Manufacturer / Source</th>
              <th className="text-right py-2.5 px-3 font-medium text-gray-400 text-[10px] uppercase tracking-wide">λ W/mK</th>
              <th className="text-left py-2.5 px-3 font-medium text-gray-400 text-[10px] uppercase tracking-wide">Fire</th>
              <th className="text-left py-2.5 px-3 font-medium text-gray-400 text-[10px] uppercase tracking-wide">Supplier</th>
              <th className="text-left py-2.5 px-3 font-medium text-gray-400 text-[10px] uppercase tracking-wide">Datasheet</th>
              <th className="text-left py-2.5 px-3 font-medium text-gray-400 text-[10px] uppercase tracking-wide">DoP</th>
              <th className="text-left py-2.5 px-3 font-medium text-gray-400 text-[10px] uppercase tracking-wide">Evidence</th>
              <th className="py-2.5 px-3 w-20" />
            </tr>
          </thead>
          <tbody>
            {groups.map(group => (
              <>
                <SectionHeader key={`hdr-${group.id}`} label={group.label} count={group.items.length} note={group.note} />
                {group.items.map(m => (
                  <MaterialRow key={m.id} m={m} onEdit={setEditTarget} onDelete={setDeleteTarget} />
                ))}
              </>
            ))}
          </tbody>
        </table>

        {filtered.length === 0 && (
          <div className="flex items-center justify-center h-32 text-sm text-gray-400">
            {filter ? 'No materials match that filter.' : 'No materials found.'}
          </div>
        )}
      </div>

      {showAdd && (
        <AddMaterialModal onClose={() => setShowAdd(false)} onAdded={handleAdded} />
      )}
      {editTarget && (
        <EvidenceModal mat={editTarget} onClose={() => setEditTarget(null)} onSaved={m => { handleSaved(m); setEditTarget(null) }} />
      )}
      {deleteTarget && (
        <DeleteConfirm mat={deleteTarget} onClose={() => setDeleteTarget(null)} onDeleted={id => { handleDeleted(id); setDeleteTarget(null) }} />
      )}
    </div>
  )
}
