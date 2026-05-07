import { useState, useEffect, useCallback, useRef } from 'react'
import { apiFetch } from '../api/client'
import BuildUpLayerPreview from '../components/BuildUpLayerPreview'

// ── Constants ─────────────────────────────────────────────────────────────────

const ELEMENT_TYPES = [
  { value: 'ExternalWall', label: 'External Wall' },
  { value: 'Floor',        label: 'Floor' },
  { value: 'Roof',         label: 'Roof' },
]

const ROLES = [
  { value: '',                label: '— unset —' },
  { value: 'internal_finish', label: 'Internal finish' },
  { value: 'service_void',    label: 'Service void' },
  { value: 'vcl',             label: 'VCL / airtight layer' },
  { value: 'airtight_layer',  label: 'Airtight layer' },
  { value: 'sheathing',       label: 'Sheathing / board' },
  { value: 'structure',       label: 'Structure' },
  { value: 'framing_zone',    label: 'Framing zone (stud/rafter + fill)' },
  { value: 'insulation',      label: 'Insulation' },
  { value: 'breather',        label: 'Breather membrane' },
  { value: 'cavity',          label: 'Ventilated cavity' },
  { value: 'cladding',        label: 'Cladding' },
  { value: 'external_finish', label: 'External finish' },
]

const FRAMING_PRESETS = [
  { label: 'None',              value: 0 },
  { label: 'Timber studs 15%',  value: 0.15 },
  { label: 'Timber studs 20%',  value: 0.20 },
  { label: 'Rafters 12%',       value: 0.12 },
  { label: 'Joists 15%',        value: 0.15 },
]

const INFILL_OPTIONS = [
  { value: 'pir',          label: 'PIR board (λ=0.023)',    lambda: 0.023, ref: 'GENERIC-PIR-FRAMING-140', name: 'PIR Infill' },
  { value: 'mineral_wool', label: 'Mineral wool (λ=0.034)', lambda: 0.034, ref: 'GENERIC-MW-FRAMING-140',  name: 'Mineral Wool Infill' },
]

const DEFAULT_LAYER = {
  material_id: '',
  thickness_mm: 100,
  position_order: 1,
  role: '',
  framing_fraction: 0,
  include_in_u_value: true,
  sd_value_m: null,
  infill_type: null,
  infill_lambda_W_mK: null,
  infill_name: null,
  infill_material_ref: null,
}

const TIER_ORDER = { standard: 0, enhanced: 1, light: 2 }

const ELEMENT_GROUPS = [
  { key: 'ExternalWall', label: 'Walls' },
  { key: 'Floor',        label: 'Floors' },
  { key: 'Roof',         label: 'Roofs' },
]

// ── Small UI components ───────────────────────────────────────────────────────

function Select({ value, onChange, options, className = '', disabled = false }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      disabled={disabled}
      className={`bg-white border border-gray-300 rounded px-2 py-1 text-xs text-gray-900 focus:outline-none focus:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
    >
      {options.map(o => (
        <option key={o.value ?? o} value={o.value ?? o}>
          {o.label ?? o}
        </option>
      ))}
    </select>
  )
}

function NumInput({ value, onChange, step = 1, min = 0, className = '' }) {
  return (
    <input
      type="number"
      value={value}
      step={step}
      min={min}
      onChange={e => onChange(parseFloat(e.target.value) || 0)}
      className={`bg-white border border-gray-300 rounded px-2 py-1 text-xs text-gray-900 focus:outline-none focus:border-gray-600 ${className}`}
    />
  )
}

function TierBadge({ tier }) {
  const cfg = {
    standard: { cls: 'bg-gray-100 text-gray-600 border border-gray-200',  label: 'Standard' },
    enhanced: { cls: 'bg-gray-800 text-gray-100',                          label: 'Enhanced' },
    light:    { cls: 'bg-gray-50 text-gray-400 border border-gray-200',    label: 'Light' },
  }
  const { cls, label } = cfg[tier] ?? { cls: 'bg-gray-50 text-gray-400 border border-gray-200', label: 'Draft' }
  return (
    <span className={`text-[11px] px-1.5 py-0.5 rounded font-medium ${cls}`}>{label}</span>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function BuildUpEditor() {
  const [materials, setMaterials] = useState([])
  const [buildUps, setBuildUps] = useState([])
  const [buildUpsLoading, setBuildUpsLoading] = useState(true)
  const [activeBuId, setActiveBuId] = useState(null)
  const [readOnly, setReadOnly] = useState(false)

  // Editor state
  const [name, setName] = useState('New Build-Up')
  const [elementType, setElementType] = useState('ExternalWall')
  const [layers, setLayers] = useState([])

  // Live validation result
  const [result, setResult] = useState(null)
  const [validating, setValidating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)

  // Material prices: { [materialId]: [priceRecord, ...] }
  const [matPrices, setMatPrices] = useState({})
  const [priceEditing, setPriceEditing] = useState(null) // materialId being edited

  // Delete confirmation
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState(null)

  const debounceRef = useRef(null)

  // ── Load materials + build-up list on mount ──────────────────────────────
  useEffect(() => {
    apiFetch('/materials').then(setMaterials).catch(console.error)
    apiFetch('/build-ups')
      .then(setBuildUps)
      .catch(console.error)
      .finally(() => setBuildUpsLoading(false))
  }, [])

  // ── Load prices for all materials currently in layers ───────────────────
  useEffect(() => {
    const ids = [...new Set(layers.map(l => l.material_id).filter(Boolean))]
    ids.forEach(id => {
      apiFetch(`/materials/${id}/prices`)
        .then(prices => setMatPrices(p => ({ ...p, [id]: prices })))
        .catch(() => {})
    })
  }, [layers])

  const loadPrices = (materialId) =>
    apiFetch(`/materials/${materialId}/prices`)
      .then(prices => setMatPrices(p => ({ ...p, [materialId]: prices })))
      .catch(() => {})

  // ── Material lookup helpers ──────────────────────────────────────────────
  const matById = Object.fromEntries(materials.map(m => [m.id, m]))

  // ── Debounced validate ───────────────────────────────────────────────────
  const validate = useCallback((currentLayers, currentElementType) => {
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      if (currentLayers.length === 0) { setResult(null); return }
      const valid = currentLayers.filter(l => l.material_id !== '')
      if (valid.length === 0) { setResult(null); return }
      setValidating(true)
      try {
        const r = await apiFetch('/build-ups/validate', {
          method: 'POST',
          body: JSON.stringify({
            element_type: currentElementType,
            layers: valid.map((l, i) => ({
              material_id: l.material_id,
              thickness_mm: l.thickness_mm,
              position_order: i + 1,
              role: l.role,
              framing_fraction: l.framing_fraction,
              include_in_u_value: l.include_in_u_value,
              sd_value_m: l.sd_value_m,
              ...(l.infill_lambda_W_mK  != null && { infill_lambda_W_mK: l.infill_lambda_W_mK }),
              ...(l.infill_type         != null && { infill_type: l.infill_type }),
              ...(l.infill_name         != null && { infill_name: l.infill_name }),
              ...(l.infill_material_ref != null && { infill_material_ref: l.infill_material_ref }),
            })),
          }),
        })
        setResult(r)
      } catch (e) {
        console.error('Validate error', e)
      } finally {
        setValidating(false)
      }
    }, 400)
  }, [])

  const handleLayerChange = (newLayers) => {
    setLayers(newLayers)
    validate(newLayers, elementType)
  }

  const handleElementTypeChange = (et) => {
    setElementType(et)
    validate(layers, et)
  }

  // ── Layer operations ─────────────────────────────────────────────────────
  const addLayer = () => {
    handleLayerChange([...layers, { ...DEFAULT_LAYER }])
  }

  const removeLayer = (i) => {
    handleLayerChange(layers.filter((_, idx) => idx !== i))
  }

  const setLayer = (i, key, val) => {
    handleLayerChange(layers.map((l, idx) => idx === i ? { ...l, [key]: val } : l))
  }

  const setLayerBatch = (i, updates) => {
    handleLayerChange(layers.map((l, idx) => idx === i ? { ...l, ...updates } : l))
  }

  const moveUp = (i) => {
    if (i === 0) return
    const next = [...layers]
    ;[next[i - 1], next[i]] = [next[i], next[i - 1]]
    handleLayerChange(next)
  }

  const moveDown = (i) => {
    if (i === layers.length - 1) return
    const next = [...layers]
    ;[next[i], next[i + 1]] = [next[i + 1], next[i]]
    handleLayerChange(next)
  }

  // ── Load existing build-up ───────────────────────────────────────────────
  const loadBuildUp = async (id) => {
    try {
      const bu = await apiFetch(`/build-ups/${id}`)
      setActiveBuId(bu.id)
      setName(bu.name)
      setElementType(bu.element_type || 'ExternalWall')
      setReadOnly(bu.status === 'approved')
      const loaded = bu.layers.map(l => ({
        material_id: l.material_id,
        thickness_mm: l.thickness_mm,
        role: l.role,
        framing_fraction: l.framing_fraction,
        include_in_u_value: l.include_in_u_value,
        sd_value_m: l.sd_value_m,
        position_order: l.position_order,
        infill_type: l.infill_type ?? null,
        infill_lambda_W_mK: l.infill_lambda_W_mK ?? null,
        infill_name: l.infill_name ?? null,
        infill_material_ref: l.infill_material_ref ?? null,
      }))
      handleLayerChange(loaded)
      setResult(null)
    } catch (e) {
      console.error(e)
    }
  }

  // ── New / Duplicate ──────────────────────────────────────────────────────
  const newBuildUp = () => {
    setActiveBuId(null)
    setName('New Build-Up')
    setElementType('ExternalWall')
    setLayers([])
    setResult(null)
    setSaveError(null)
    setReadOnly(false)
  }

  const duplicateBuildUp = () => {
    setActiveBuId(null)
    setName(`Copy of ${name}`)
    setReadOnly(false)
    setSaveError(null)
  }

  // ── Delete build-up ──────────────────────────────────────────────────────
  const deleteBuildUp = async () => {
    if (!activeBuId) return
    setDeleting(true)
    setDeleteError(null)
    try {
      await apiFetch(`/build-ups/${activeBuId}`, { method: 'DELETE' })
      const updated = await apiFetch('/build-ups')
      setBuildUps(updated)
      // Reset to blank new build-up
      setActiveBuId(null)
      setName('New Build-Up')
      setElementType('ExternalWall')
      setLayers([])
      setResult(null)
      setReadOnly(false)
      setDeleteConfirm(false)
    } catch (e) {
      setDeleteError(e.message)
    } finally {
      setDeleting(false)
    }
  }

  // ── Save ─────────────────────────────────────────────────────────────────
  const save = async () => {
    setSaving(true)
    setSaveError(null)
    try {
      const payload = {
        name,
        element_type: elementType,
        build_up_type: 'closed_panel',
        scope: 'library',
        status: 'draft',
        layers: layers
          .filter(l => l.material_id !== '')
          .map((l, i) => ({
            material_id: l.material_id,
            thickness_mm: l.thickness_mm,
            position_order: i + 1,
            role: l.role,
            framing_fraction: l.framing_fraction,
            include_in_u_value: l.include_in_u_value,
            sd_value_m: l.sd_value_m,
            ...(l.infill_lambda_W_mK  != null && { infill_lambda_W_mK: l.infill_lambda_W_mK }),
            ...(l.infill_type         != null && { infill_type: l.infill_type }),
            ...(l.infill_name         != null && { infill_name: l.infill_name }),
            ...(l.infill_material_ref != null && { infill_material_ref: l.infill_material_ref }),
          })),
      }

      let saved
      if (activeBuId) {
        saved = await apiFetch(`/build-ups/${activeBuId}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
        })
      } else {
        saved = await apiFetch('/build-ups', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        setActiveBuId(saved.id)
      }
      setResult(saved)
      const list = await apiFetch('/build-ups')
      setBuildUps(list)
    } catch (e) {
      setSaveError(e.message)
    } finally {
      setSaving(false)
    }
  }

  // ── Grouped + sorted template list ───────────────────────────────────────
  const sortedBuildUps = [...buildUps].sort((a, b) => {
    const ta = TIER_ORDER[a.build_up_type] ?? 99
    const tb = TIER_ORDER[b.build_up_type] ?? 99
    if (ta !== tb) return ta - tb
    return new Date(a.created_at ?? 0) - new Date(b.created_at ?? 0)
  })

  // ── Render ────────────────────────────────────────────────────────────────
  const hasErrors = result?.errors?.length > 0

  return (
    <div className="flex h-full overflow-hidden">

      {/* ── Left panel: settings + saved list ────────────────────────── */}
      <div className="w-64 shrink-0 bg-white border-r border-gray-200 flex flex-col overflow-y-auto">
        <div className="px-4 py-4 border-b border-gray-200">
          <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Build-Up Editor</div>

          {/* Name */}
          <div className="mb-3">
            <label className="block text-xs text-gray-500 mb-1">Name</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              disabled={readOnly}
              className="w-full bg-white border border-gray-300 rounded px-2 py-1.5 text-sm text-gray-900 focus:outline-none focus:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          {/* Element type */}
          <div className="mb-3">
            <label className="block text-xs text-gray-500 mb-1">Element type</label>
            <Select
              value={elementType}
              onChange={handleElementTypeChange}
              options={ELEMENT_TYPES}
              className="w-full"
              disabled={readOnly}
            />
          </div>

          <button
            onClick={newBuildUp}
            className="w-full text-xs text-gray-600 hover:text-gray-900 border border-gray-300 hover:border-gray-500 rounded px-2 py-1.5 transition-colors"
          >
            New build-up
          </button>
        </div>

        {/* Template list — grouped by element type */}
        <div className="flex-1 px-4 py-3 overflow-y-auto">
          <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Library</div>
          {buildUpsLoading ? (
            <p className="text-xs text-gray-400 italic">Loading…</p>
          ) : buildUps.length === 0 ? (
            <p className="text-xs text-gray-400 italic">No templates yet</p>
          ) : (
            <>
              {ELEMENT_GROUPS.map(group => {
                const items = sortedBuildUps.filter(bu => bu.element_type === group.key)
                if (items.length === 0) return null
                return (
                  <div key={group.key} className="mb-4">
                    <div className="text-[11px] font-medium text-gray-400 uppercase tracking-wider mb-1.5">{group.label}</div>
                    <div className="space-y-0.5">
                      {items.map(bu => (
                        <button
                          key={bu.id}
                          onClick={() => loadBuildUp(bu.id)}
                          className={`w-full text-left text-xs px-2 py-2 rounded transition-colors ${
                            activeBuId === bu.id
                              ? 'bg-gray-100 text-gray-900 border border-gray-300'
                              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                          }`}
                        >
                          <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                            <span className="font-medium truncate">{bu.name}</span>
                            {bu.status === 'approved' && (
                              <span className="text-[10px] text-gray-400 border border-gray-200 rounded px-1 shrink-0" title="Library template">lib</span>
                            )}
                          </div>
                          <div className="flex items-center gap-1.5 mt-1">
                            <TierBadge tier={bu.build_up_type} />
                            <span className="text-gray-400 tabular-nums">
                              {bu.u_value > 0 ? `${bu.u_value.toFixed(3)} W/m²K` : '—'}
                            </span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )
              })}
              {/* Ungrouped */}
              {(() => {
                const knownTypes = ELEMENT_GROUPS.map(g => g.key)
                const others = sortedBuildUps.filter(bu => !knownTypes.includes(bu.element_type))
                if (others.length === 0) return null
                return (
                  <div className="mb-4">
                    <div className="text-[11px] font-medium text-gray-400 uppercase tracking-wider mb-1.5">Other</div>
                    <div className="space-y-0.5">
                      {others.map(bu => (
                        <button
                          key={bu.id}
                          onClick={() => loadBuildUp(bu.id)}
                          className={`w-full text-left text-xs px-2 py-2 rounded transition-colors ${
                            activeBuId === bu.id
                              ? 'bg-gray-100 text-gray-900 border border-gray-300'
                              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                          }`}
                        >
                          <div className="font-medium truncate">{bu.name}</div>
                          <div className="flex items-center gap-1.5 mt-1">
                            <TierBadge tier={bu.build_up_type} />
                            <span className="text-gray-400">{bu.element_type}</span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )
              })()}
            </>
          )}
        </div>
      </div>

      {/* ── Centre: layer list ────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden border-r border-gray-200">
        <div className="px-5 py-3 border-b border-gray-200 bg-white flex items-center justify-between shrink-0">
          <div>
            <div className="text-sm font-semibold text-gray-900">Layers — Inside to Outside</div>
            <div className="text-xs text-gray-400">Position 1 = innermost warm layer</div>
          </div>
          {!readOnly && (
            <button
              onClick={addLayer}
              className="text-xs text-gray-600 hover:text-gray-900 font-medium border border-gray-300 hover:border-gray-500 rounded px-3 py-1.5 transition-colors"
            >
              + Add layer
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 bg-gray-50">
          {layers.length === 0 ? (
            <div className="text-center py-16 text-gray-400 text-sm">
              {readOnly ? 'Loading template…' : 'No layers yet. Click "+ Add layer" or select a template.'}
            </div>
          ) : (
            <div className="space-y-2">
              {layers.map((layer, i) => (
                <LayerRow
                  key={i}
                  index={i}
                  layer={layer}
                  total={layers.length}
                  materials={materials}
                  matById={matById}
                  readOnly={readOnly}
                  onSet={setLayer}
                  onSetBatch={setLayerBatch}
                  onMoveUp={moveUp}
                  onMoveDown={moveDown}
                  onRemove={removeLayer}
                />
              ))}
            </div>
          )}
        </div>

        {/* Save / duplicate bar */}
        <div className="px-5 py-3 border-t border-gray-200 bg-white shrink-0">
          {saveError && <p className="text-xs text-red-600 mb-2">{saveError}</p>}
          <div className="flex items-center gap-3">
            {readOnly ? (
              <>
                <button
                  onClick={duplicateBuildUp}
                  className="bg-gray-900 hover:bg-gray-700 text-white font-medium text-sm rounded px-5 py-2 transition-colors"
                >
                  Duplicate to edit
                </button>
                <span className="text-xs text-gray-400">Library template — read only</span>
              </>
            ) : (
              <>
                <button
                  onClick={save}
                  disabled={saving || layers.filter(l => l.material_id !== '').length === 0}
                  className="bg-gray-900 hover:bg-gray-700 disabled:bg-gray-200 disabled:text-gray-400 text-white font-medium text-sm rounded px-5 py-2 transition-colors"
                >
                  {saving ? 'Saving…' : activeBuId ? 'Save changes' : 'Save build-up'}
                </button>
                {hasErrors && (
                  <span className="text-xs text-red-600">
                    {result.errors.length} error{result.errors.length > 1 ? 's' : ''} — fix before saving
                  </span>
                )}
                {activeBuId && (
                  <button
                    onClick={() => { setDeleteConfirm(true); setDeleteError(null) }}
                    className="ml-auto text-xs text-gray-400 hover:text-red-600 transition-colors"
                  >
                    Delete
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── Delete confirmation modal ─────────────────────────────────── */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 p-6">
            <div className="text-sm font-semibold text-gray-900 mb-2">Delete build-up?</div>
            <div className="text-sm text-gray-600 mb-4">
              <span className="font-medium text-gray-900">{name}</span> will be permanently deleted. This cannot be undone.
            </div>
            {deleteError && (
              <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2 mb-4">
                {deleteError}
              </div>
            )}
            <div className="flex gap-3">
              <button
                onClick={() => { setDeleteConfirm(false); setDeleteError(null) }}
                className="flex-1 bg-white border border-gray-300 hover:border-gray-500 text-gray-700 font-medium text-sm rounded py-2 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={deleteBuildUp}
                disabled={deleting}
                className="flex-1 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-medium text-sm rounded py-2 transition-colors"
              >
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Right panel: live U-value result ─────────────────────────── */}
      <div className="w-80 shrink-0 bg-white border-l border-gray-200 overflow-y-auto">
        <div className="px-5 py-4 border-b border-gray-200">
          <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Thermal Performance</div>
        </div>

        {validating && (
          <div className="px-5 py-4 text-xs text-gray-400 animate-pulse">Calculating…</div>
        )}

        {!validating && result && (
          <div className="px-5 py-4 space-y-5">

            {/* U-value + thickness headline */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
              <div className="text-3xl font-semibold text-gray-900 tabular-nums">
                {result.u_value > 0 ? result.u_value.toFixed(3) : '—'}
              </div>
              <div className="text-xs text-gray-400 mt-1">W/m²K</div>
              <div className="text-xs text-gray-400 mt-0.5">
                R<sub>total</sub> = {result.r_total > 0 ? result.r_total.toFixed(3) : '—'} m²K/W
              </div>
              {result.total_thickness_mm > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-200">
                  <div className="text-xl font-semibold text-gray-700 tabular-nums">
                    {Math.round(result.total_thickness_mm)} mm
                  </div>
                  <div className="text-xs text-gray-400">total build-up thickness</div>
                </div>
              )}
            </div>

            {/* Live layer preview */}
            {(() => {
              const previewLayers = layers
                .filter(l => l.material_id !== '' && Number(l.thickness_mm) > 0)
                .map(l => ({ name: matById[l.material_id]?.name || 'Layer', thickness_mm: Number(l.thickness_mm), role: l.role }))
              return previewLayers.length > 0 ? (
                <div>
                  <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Build-up section</div>
                  <BuildUpLayerPreview layers={previewLayers} />
                </div>
              ) : null
            })()}

            {/* Target checks */}
            {result.targets?.length > 0 && (
              <div>
                <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Profile targets</div>
                <div className="space-y-1.5">
                  {result.targets.map(t => (
                    <div key={t.code} className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded px-3 py-2">
                      <div>
                        <div className="text-xs font-medium text-gray-700">{t.label || `${t.code} target`}</div>
                        <div className="text-xs text-gray-400">≤ {t.target_u_value} W/m²K</div>
                      </div>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded border ${
                        t.passes
                          ? 'bg-green-50 text-green-700 border-green-200'
                          : 'bg-red-50 text-red-700 border-red-200'
                      }`}>
                        {t.passes ? `Pass +${t.headroom.toFixed(3)}` : `Fail ${t.headroom.toFixed(3)}`}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Errors */}
            {result.errors?.length > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <div className="text-[11px] font-semibold text-red-700 uppercase tracking-wider mb-2">Errors</div>
                <ul className="space-y-1">
                  {result.errors.map((e, i) => (
                    <li key={i} className="text-xs text-red-600 flex gap-1.5">
                      <span className="shrink-0">✗</span>{e}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Warnings */}
            {result.warnings?.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                <div className="text-[11px] font-semibold text-amber-700 uppercase tracking-wider mb-2">Warnings</div>
                <ul className="space-y-1">
                  {result.warnings.map((w, i) => (
                    <li key={i} className="text-xs text-amber-700 flex gap-1.5">
                      <span className="shrink-0">△</span>{w}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Layer breakdown */}
            {result.layer_results?.length > 0 && (
              <div>
                <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Layer breakdown</div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-1.5 pr-2 font-medium text-gray-400">Layer</th>
                        <th className="text-right py-1.5 pr-2 font-medium text-gray-400">mm</th>
                        <th className="text-right py-1.5 pr-2 font-medium text-gray-400">λ_eff</th>
                        <th className="text-right py-1.5 font-medium text-gray-400">R</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.layer_results.map((lr, i) => (
                        <tr key={i} className="border-b border-gray-100">
                          <td className="py-1.5 pr-2 text-gray-700 truncate max-w-[100px]" title={lr.name}>{lr.name}</td>
                          <td className="py-1.5 pr-2 text-right text-gray-600 tabular-nums">{lr.thickness_mm}</td>
                          <td className="py-1.5 pr-2 text-right text-gray-600 tabular-nums">{lr.lambda_effective.toFixed(4)}</td>
                          <td className="py-1.5 text-right text-gray-700 font-medium tabular-nums">{lr.r_value.toFixed(3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Assumptions */}
            {result.assumptions?.length > 0 && (
              <div>
                <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Assumptions</div>
                <ul className="space-y-0.5">
                  {result.assumptions.map((a, i) => (
                    <li key={i} className="text-xs text-gray-400">{a}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {!validating && !result && (() => {
          const previewLayers = layers
            .filter(l => l.material_id !== '' && Number(l.thickness_mm) > 0)
            .map(l => ({ name: matById[l.material_id]?.name || 'Layer', thickness_mm: Number(l.thickness_mm), role: l.role }))
          const localTotal = previewLayers.reduce((s, l) => s + l.thickness_mm, 0)
          if (previewLayers.length === 0) {
            return (
              <div className="px-5 py-10 text-center text-gray-400 text-xs">
                Add layers to see the live U-value calculation.
              </div>
            )
          }
          return (
            <div className="px-5 py-4 space-y-4">
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
                <div className="text-xl font-semibold text-gray-700 tabular-nums">{Math.round(localTotal)} mm</div>
                <div className="text-xs text-gray-400">total thickness (calculating U-value…)</div>
              </div>
              <div>
                <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Build-up section</div>
                <BuildUpLayerPreview layers={previewLayers} />
              </div>
            </div>
          )
        })()}

        {/* ── Material Costs ──────────────────────────────────────── */}
        {layers.some(l => l.material_id) && (
          <div className="px-5 py-4 border-t border-gray-200">
            <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Material Costs</div>
            <div className="space-y-2">
              {[...new Set(layers.map(l => l.material_id).filter(Boolean))].map(matId => {
                const mat = matById[matId]
                if (!mat) return null
                const prices = matPrices[matId] || []
                const defPrice = prices.find(p => p.is_default) || prices[0]
                const isEditing = priceEditing === matId
                return (
                  <MaterialPriceRow
                    key={matId}
                    mat={mat}
                    defaultPrice={defPrice}
                    allPrices={prices}
                    isEditing={isEditing}
                    onEdit={() => setPriceEditing(isEditing ? null : matId)}
                    onSaved={() => { loadPrices(matId); setPriceEditing(null) }}
                    onDeleted={(pid) => {
                      apiFetch(`/material-prices/${pid}`, { method: 'DELETE' })
                        .then(() => loadPrices(matId))
                        .catch(() => {})
                    }}
                    onSetDefault={(pid) => {
                      apiFetch(`/material-prices/${pid}/set-default`, { method: 'POST' })
                        .then(() => loadPrices(matId))
                        .catch(() => {})
                    }}
                  />
                )
              })}
            </div>
          </div>
        )}

        {/* ── Material Evidence ────────────────────────────────────── */}
        {layers.some(l => l.material_id) && (() => {
          const layerMats = [...new Set(layers.map(l => l.material_id).filter(Boolean))].map(id => matById[id]).filter(Boolean)
          const counts = { verified: 0, partial: 0, missing: 0 }
          layerMats.forEach(m => { counts[m.evidence_status] = (counts[m.evidence_status] || 0) + 1 })
          return (
            <div className="px-5 py-4 border-t border-gray-200">
              <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Material Evidence</div>
              <div className="flex gap-3 text-xs">
                {counts.verified > 0 && <span className="text-green-700 bg-green-50 border border-green-200 rounded px-2 py-0.5">✓ {counts.verified} verified</span>}
                {counts.partial  > 0 && <span className="text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-0.5">~ {counts.partial} partial</span>}
                {counts.missing  > 0 && <span className="text-amber-600 bg-amber-50 border border-amber-100 rounded px-2 py-0.5">⚠ {counts.missing} missing</span>}
              </div>
            </div>
          )
        })()}
      </div>
    </div>
  )
}

// ── Layer row component ───────────────────────────────────────────────────────

function LayerRow({ index, layer, total, materials, matById, readOnly, onSet, onSetBatch, onMoveUp, onMoveDown, onRemove }) {
  const mat = layer.material_id ? matById[layer.material_id] : null

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3 hover:border-gray-300 transition-colors">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs text-gray-400 w-5 shrink-0 text-center tabular-nums">{index + 1}</span>

        {/* Material */}
        <select
          value={layer.material_id}
          onChange={e => onSet(index, 'material_id', parseInt(e.target.value) || '')}
          disabled={readOnly}
          className="flex-1 bg-white border border-gray-300 rounded px-2 py-1 text-xs text-gray-900 focus:outline-none focus:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <option value="">— select material —</option>
          {materials.map(m => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>

        {!readOnly && (
          <>
            <button
              onClick={() => onMoveUp(index)}
              disabled={index === 0}
              className="text-gray-400 hover:text-gray-700 disabled:opacity-20 text-xs px-1"
              title="Move up (warmer)"
            >↑</button>
            <button
              onClick={() => onMoveDown(index)}
              disabled={index === total - 1}
              className="text-gray-400 hover:text-gray-700 disabled:opacity-20 text-xs px-1"
              title="Move down (colder)"
            >↓</button>
            <button
              onClick={() => onRemove(index)}
              className="text-gray-300 hover:text-red-500 text-xs px-1 transition-colors"
            >✕</button>
          </>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 ml-7">
        {/* Thickness */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">Thickness (mm)</label>
          <NumInput
            value={layer.thickness_mm}
            onChange={v => onSet(index, 'thickness_mm', v)}
            step={1}
            className={`w-full ${readOnly ? 'opacity-50 cursor-not-allowed' : ''}`}
          />
        </div>

        {/* Role */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">Role</label>
          <Select
            value={layer.role}
            onChange={v => onSet(index, 'role', v)}
            options={ROLES}
            className="w-full"
            disabled={readOnly}
          />
        </div>

        {/* Framing fraction */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">Framing fraction</label>
          <Select
            value={FRAMING_PRESETS.find(p => Math.abs(p.value - layer.framing_fraction) < 0.001)?.value ?? 0}
            onChange={v => onSet(index, 'framing_fraction', parseFloat(v))}
            options={FRAMING_PRESETS}
            className="w-full"
            disabled={readOnly}
          />
        </div>

        {/* Include in U-value */}
        <div className="flex items-end pb-1">
          <label className={`flex items-center gap-2 text-xs text-gray-500 ${readOnly ? 'cursor-not-allowed' : 'cursor-pointer'}`}>
            <input
              type="checkbox"
              checked={layer.include_in_u_value}
              onChange={e => onSet(index, 'include_in_u_value', e.target.checked)}
              disabled={readOnly}
              className="accent-gray-700"
            />
            Include in U-value
          </label>
        </div>
      </div>

      {/* Infill type — only for framing_zone */}
      {layer.role === 'framing_zone' && (
        <div className="ml-7 mt-2 grid grid-cols-2 gap-2">
          <div className="col-span-2">
            <label className="block text-xs text-gray-400 mb-1">Infill insulation</label>
            <Select
              value={layer.infill_type || ''}
              onChange={v => {
                const opt = INFILL_OPTIONS.find(o => o.value === v)
                onSetBatch(index, {
                  infill_type:         v || null,
                  infill_lambda_W_mK:  opt ? opt.lambda : null,
                  infill_name:         opt ? opt.name   : null,
                  infill_material_ref: opt ? opt.ref    : null,
                })
              }}
              options={[{ value: '', label: '— auto from material —' }, ...INFILL_OPTIONS]}
              className="w-full"
              disabled={readOnly}
            />
          </div>
          {layer.infill_lambda_W_mK != null && (
            <div className="col-span-2 text-xs text-gray-500">
              λ_infill = {layer.infill_lambda_W_mK} W/mK — overrides material lambda for U-value
            </div>
          )}
        </div>
      )}

      {/* Lambda hint */}
      {mat && (
        <div className="ml-7 mt-1.5 flex items-center gap-2 flex-wrap">
          <span className="text-xs text-gray-400">λ = {mat.lambda_W_mK} W/mK</span>
          {mat.supplier_url
            ? <a href={mat.supplier_url} target="_blank" rel="noreferrer"
                className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 hover:bg-blue-100 border border-blue-100 transition-colors">Supplier</a>
            : <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-600 border border-amber-100">No supplier</span>
          }
          {mat.datasheet_url
            ? <a href={mat.datasheet_url} target="_blank" rel="noreferrer"
                className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 hover:bg-blue-100 border border-blue-100 transition-colors">Data sheet</a>
            : <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-600 border border-amber-100">No data sheet</span>
          }
          {mat.dop_url
            ? <a href={mat.dop_url} target="_blank" rel="noreferrer"
                className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 hover:bg-blue-100 border border-blue-100 transition-colors">DoP</a>
            : null
          }
        </div>
      )}
    </div>
  )
}

// ── Material price row ────────────────────────────────────────────────────────

const PRICE_TYPES = [
  { value: 'retail_lv',           label: 'Retail LV' },
  { value: 'trade_lv',            label: 'Trade LV' },
  { value: 'manufacturer_direct', label: 'Manufacturer direct' },
  { value: 'import_benchmark',    label: 'Import benchmark' },
  { value: 'manual_override',     label: 'Manual override' },
]

function MaterialPriceRow({ mat, defaultPrice, allPrices, isEditing, onEdit, onSaved, onDeleted, onSetDefault }) {
  const [form, setForm] = useState({
    price_type: 'retail_lv',
    price_per_unit: '',
    unit: mat.unit || 'm2',
    currency: 'EUR',
    notes: '',
    is_default: true,
  })
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState(null)

  const submit = async () => {
    if (!form.price_per_unit || isNaN(Number(form.price_per_unit))) {
      setErr('Enter a valid price'); return
    }
    setSaving(true); setErr(null)
    try {
      await apiFetch(`/materials/${mat.id}/prices`, {
        method: 'POST',
        body: JSON.stringify({ ...form, price_per_unit: Number(form.price_per_unit) }),
      })
      onSaved()
    } catch (e) {
      setErr(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Header row */}
      <button
        onClick={onEdit}
        className="w-full flex items-center justify-between px-3 py-2 bg-white hover:bg-gray-50 transition-colors text-left"
      >
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium text-gray-800 truncate">{mat.name}</div>
          <div className="text-[11px] text-gray-400 mt-0.5">
            {defaultPrice
              ? <span className="text-green-700">{defaultPrice.currency} {defaultPrice.price_per_unit.toFixed(2)} / {defaultPrice.unit}</span>
              : <span className="text-amber-600">No price set</span>
            }
          </div>
        </div>
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"
          className={`w-3.5 h-3.5 shrink-0 ml-2 text-gray-400 transition-transform ${isEditing ? 'rotate-180' : ''}`}>
          <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {/* Expanded: existing prices + add form */}
      {isEditing && (
        <div className="border-t border-gray-100 bg-gray-50 px-3 py-3 space-y-3">
          {/* Existing prices */}
          {allPrices.length > 0 && (
            <div className="space-y-1">
              {allPrices.map(p => (
                <div key={p.id} className="flex items-center gap-2 text-xs">
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${p.is_default ? 'bg-green-500' : 'bg-gray-300'}`} />
                  <span className="text-gray-700 font-medium tabular-nums">{p.currency} {p.price_per_unit.toFixed(2)}/{p.unit}</span>
                  <span className="text-gray-400">{PRICE_TYPES.find(t => t.value === p.price_type)?.label || p.price_type}</span>
                  <div className="ml-auto flex gap-1">
                    {!p.is_default && (
                      <button
                        onClick={() => onSetDefault(p.id)}
                        className="text-[10px] text-gray-500 hover:text-green-700 border border-gray-200 hover:border-green-300 rounded px-1.5 py-0.5 transition-colors"
                      >set default</button>
                    )}
                    <button
                      onClick={() => onDeleted(p.id)}
                      className="text-[10px] text-gray-400 hover:text-red-600 border border-gray-200 hover:border-red-300 rounded px-1.5 py-0.5 transition-colors"
                    >del</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Add new price form */}
          <div className="space-y-2 pt-2 border-t border-gray-200">
            <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Add price</div>
            <div className="flex gap-1.5">
              <input
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={form.price_per_unit}
                onChange={e => setForm(f => ({ ...f, price_per_unit: e.target.value }))}
                className="w-20 bg-white border border-gray-300 rounded px-2 py-1 text-xs text-gray-900 focus:outline-none focus:border-gray-600 tabular-nums"
              />
              <select
                value={form.currency}
                onChange={e => setForm(f => ({ ...f, currency: e.target.value }))}
                className="w-16 bg-white border border-gray-300 rounded px-1 py-1 text-xs text-gray-900 focus:outline-none focus:border-gray-600"
              >
                <option>EUR</option>
                <option>USD</option>
                <option>GBP</option>
              </select>
              <select
                value={form.unit}
                onChange={e => setForm(f => ({ ...f, unit: e.target.value }))}
                className="w-14 bg-white border border-gray-300 rounded px-1 py-1 text-xs text-gray-900 focus:outline-none focus:border-gray-600"
              >
                <option value="m2">m²</option>
                <option value="lm">lm</option>
                <option value="m3">m³</option>
                <option value="pcs">pcs</option>
              </select>
            </div>
            <select
              value={form.price_type}
              onChange={e => setForm(f => ({ ...f, price_type: e.target.value }))}
              className="w-full bg-white border border-gray-300 rounded px-2 py-1 text-xs text-gray-900 focus:outline-none focus:border-gray-600"
            >
              {PRICE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            <input
              type="text"
              placeholder="Notes (optional)"
              value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              className="w-full bg-white border border-gray-300 rounded px-2 py-1 text-xs text-gray-900 focus:outline-none focus:border-gray-600"
            />
            <label className="flex items-center gap-2 text-xs text-gray-600">
              <input
                type="checkbox"
                checked={form.is_default}
                onChange={e => setForm(f => ({ ...f, is_default: e.target.checked }))}
                className="rounded"
              />
              Set as default price
            </label>
            {err && <div className="text-xs text-red-600">{err}</div>}
            <button
              onClick={submit}
              disabled={saving}
              className="w-full bg-gray-900 hover:bg-gray-700 disabled:opacity-50 text-white text-xs font-medium rounded px-3 py-1.5 transition-colors"
            >
              {saving ? 'Saving…' : 'Add price'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
