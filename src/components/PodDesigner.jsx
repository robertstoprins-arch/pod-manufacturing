import { useState, useCallback, useEffect } from 'react'
import { apiFetch } from '../api/client'
import BuildUpLayerPreview from './BuildUpLayerPreview'
import CostSummary from './CostSummary'
import FinishSelector from './FinishSelector'

// ── Constants ─────────────────────────────────────────────────────────────────

const ROOF_TYPES = [
  { value: 'duo_pitch', label: 'Duo Pitch' },
  { value: 'mono_pitch', label: 'Mono Pitch' },
  { value: 'flat', label: 'Flat' },
]
const WALL_FACES = ['N', 'S', 'E', 'W']
const OPENING_TYPES = [
  { value: 'window',       label: 'Window' },
  { value: 'door',         label: 'External Door' },
  { value: 'french_door',  label: 'French / Patio Door' },
  { value: 'vent',         label: 'Vent / Louvre' },
]

const DEFAULT_SKYLIGHT = {
  id: 'SKY-01',
  type: 'skylight',
  selected: false,
  width_mm: 600,
  height_mm: 900,
  x_offset_mm: '',
  y_offset_mm: '',
  status: 'for_review',
}

const MIN_ROOF_CLEARANCE_MM = 400

function validateSkylight(sky, geom) {
  const roofW = (geom.width_m || 0) * 1000
  const roofL = (geom.length_m || 0) * 1000
  const w = sky.width_mm || 0
  const h = sky.height_mm || 0
  const x = sky.x_offset_mm !== '' && sky.x_offset_mm != null ? Number(sky.x_offset_mm) : null
  const y = sky.y_offset_mm !== '' && sky.y_offset_mm != null ? Number(sky.y_offset_mm) : null
  if (x === null || y === null) return null  // position optional — no error
  const errors = []
  if (x < MIN_ROOF_CLEARANCE_MM) errors.push(`offset from W edge must be ≥ 400mm (got ${x}mm)`)
  if (y < MIN_ROOF_CLEARANCE_MM) errors.push(`offset from N edge must be ≥ 400mm (got ${y}mm)`)
  if (x + w > roofW - MIN_ROOF_CLEARANCE_MM) errors.push(`right edge too close to E roof edge`)
  if (y + h > roofL - MIN_ROOF_CLEARANCE_MM) errors.push(`bottom edge too close to S roof edge`)
  return errors.length ? errors.join('; ') : null
}
const OPENING_SHAPES = [
  { value: 'rectangular', label: 'Rectangular' },
  { value: 'circular',    label: 'Circular' },
]
const DRAWING_TABS = [
  { key: 'floor_plan',       label: 'Floor Plan' },
  { key: 'wall_N',           label: 'Wall N' },
  { key: 'wall_S',           label: 'Wall S' },
  { key: 'wall_E',           label: 'Wall E' },
  { key: 'wall_W',           label: 'Wall W' },
  { key: 'manufacture_plan', label: 'Mfr Plan' },
]

const ELEMENT_LABELS = {
  ExternalWall: 'External Wall',
  Floor: 'Floor',
  Roof: 'Roof',
}

const DEFAULT_FORM = {
  width_m: 3.0,
  length_m: 6.0,
  wall_height_m: 2.7,
  roof_type: 'duo_pitch',
  roof_pitch_deg: 15,
  openings: [],
  roof_openings: [],
}

const DEFAULT_OPENING = {
  wall: 'S',
  type: 'window',
  shape: 'rectangular',
  width_m: 1.2,
  height_m: 1.1,
  sill_height_m: 0.9,
  x_offset_m: '',
}

const DEFAULT_ASSIGNMENTS = { ExternalWall: null, Floor: null, Roof: null }

// ── Small UI components ───────────────────────────────────────────────────────

function Field({ label, children, className = '' }) {
  return (
    <div className={className}>
      <label className="block text-xs text-gray-500 mb-1">{label}</label>
      {children}
    </div>
  )
}

function NumberInput({ value, onChange, step = 0.1, min = 0.1 }) {
  return (
    <input
      type="number"
      value={value}
      step={step}
      min={min}
      onChange={e => onChange(parseFloat(e.target.value) || 0)}
      className="w-full bg-white border border-gray-300 rounded px-3 py-2 text-sm text-gray-900 focus:outline-none focus:border-gray-600 transition-colors"
    />
  )
}

function Select({ value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="w-full bg-white border border-gray-300 rounded px-3 py-2 text-sm text-gray-900 focus:outline-none focus:border-gray-600 transition-colors"
    >
      {options.map(o => (
        <option key={o.value ?? o} value={o.value ?? o}>
          {o.label ?? o}
        </option>
      ))}
    </select>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function PodDesigner() {
  // Geometry + drawings
  const [form, setForm]           = useState(DEFAULT_FORM)
  const [drawings, setDrawings]   = useState(null)
  const [activeTab, setActiveTab] = useState('floor_plan')
  const [loading, setLoading]     = useState(false)
  const [drawError, setDrawError] = useState(null)

  // Pod spec persistence
  const [specId, setSpecId]           = useState(null)
  const [specName, setSpecName]       = useState('New Pod Spec')
  const [podSpecs, setPodSpecs]       = useState([])
  const [assignments, setAssignments] = useState(DEFAULT_ASSIGNMENTS)
  const [buildUps, setBuildUps]       = useState([])
  const [saving, setSaving]           = useState(false)
  const [saveError, setSaveError]     = useState(null)

  // Delete pod spec
  const [deleteTarget, setDeleteTarget]   = useState(null)  // { id, name }
  const [deleting, setDeleting]           = useState(false)
  const [deleteError, setDeleteError]     = useState(null)
  const deleteConfirm = deleteTarget !== null

  // BOM
  const [bom, setBom]             = useState(null)
  const [bomLoading, setBomLoading] = useState(false)
  const [showBom, setShowBom]         = useState(false)
  const [showCost, setShowCost]       = useState(false)
  const [showFinishes, setShowFinishes] = useState(false)
  const [finishSelections, setFinishSelections] = useState(null)

  // PDF generation
  const [pdfLoading, setPdfLoading]           = useState(false)
  const [pdfError,   setPdfError]             = useState(null)
  const [clientPdfLoading, setClientPdfLoading] = useState(false)
  const [clientPdfError,   setClientPdfError]   = useState(null)

  // Manufacture plan metadata
  const [mfrMeta, setMfrMeta] = useState({
    project_name: '',
    client_project_id: '',
    drawn_by: '',
    checked_by: '',
    revision: 'P1',
    drawing_number: '',
    status: 'Preliminary',
    issue_date: new Date().toISOString().slice(0, 10),
    scale_str: '1:50',
    disclaimer: 'This drawing is indicative only. All dimensions to be verified on site.',
  })
  const [mfrPlanLoading, setMfrPlanLoading] = useState(false)
  const [mfrPlanError,   setMfrPlanError]   = useState(null)

  // Package selections for Cost Summary
  const [packages, setPackages] = useState({
    roof_finish:  true,                        // bool   — EPDM always on by default
    heating:      'electric_radiators_base',  // radio
    ventilation:  ['trickle_vents_allowance'],// multi  — array of codes
    cctv_data:    [],                         // multi
    pv_ready:     false,                      // bool
    finishes:     null,                       // radio
    furniture:    {},                         // { [code]: qty }
    groundworks:  null,                       // radio
  })

  // ── On mount ────────────────────────────────────────────────────────────────
  useEffect(() => {
    apiFetch('/build-ups').then(setBuildUps).catch(console.error)
    apiFetch('/pod-specs').then(setPodSpecs).catch(console.error)
  }, [])

  // ── Form helpers ────────────────────────────────────────────────────────────
  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const addOpening = () =>
    setForm(f => ({ ...f, openings: [...f.openings, { ...DEFAULT_OPENING }] }))

  const removeOpening = i =>
    setForm(f => ({ ...f, openings: f.openings.filter((_, idx) => idx !== i) }))

  const OPENING_TYPE_DEFAULTS = {
    window:      { height_m: 1.1, sill_height_m: 0.9 },
    door:        { height_m: 2.1, sill_height_m: 0.0 },
    french_door: { height_m: 2.1, sill_height_m: 0.0 },
    vent:        { height_m: 0.3, sill_height_m: 2.1 },
  }

  const setOpening = (i, key, val) =>
    setForm(f => ({
      ...f,
      openings: f.openings.map((o, idx) => {
        if (idx !== i) return o
        const update = { ...o, [key]: val }
        // When type changes, apply sensible default height + sill
        if (key === 'type' && OPENING_TYPE_DEFAULTS[val]) {
          Object.assign(update, OPENING_TYPE_DEFAULTS[val])
        }
        return update
      }),
    }))

  // Skylight helpers — single optional skylight (SKY-01)
  const skylight = form.roof_openings?.[0] ?? null
  const skylightSelected = skylight?.selected === true

  const toggleSkylight = () => {
    if (skylightSelected) {
      setForm(f => ({ ...f, roof_openings: [] }))
    } else {
      setForm(f => ({ ...f, roof_openings: [{ ...DEFAULT_SKYLIGHT, selected: true }] }))
    }
  }

  const setSkylight = (key, val) =>
    setForm(f => ({
      ...f,
      roof_openings: [{ ...(f.roof_openings[0] || DEFAULT_SKYLIGHT), [key]: val }],
    }))

  const skylightError = skylightSelected ? validateSkylight(skylight, form) : null

  // ── Generate drawings ────────────────────────────────────────────────────────
  const generate = useCallback(async () => {
    setLoading(true)
    setDrawError(null)
    try {
      const wallBu  = buildUps.find(b => b.id === assignments.ExternalWall)
      const floorBu = buildUps.find(b => b.id === assignments.Floor)
      const roofBu  = buildUps.find(b => b.id === assignments.Roof)
      const payload = {
        ...form,
        openings: form.openings.map(({ x_offset_m, ...o }) => ({
          ...o,
          height_m: o.shape === 'circular' ? o.width_m : o.height_m,
          x_offset_m: x_offset_m === '' || x_offset_m == null ? null : parseFloat(x_offset_m),
        })),
        wall_thick_m: wallBu?.total_thickness_mm > 0 ? wallBu.total_thickness_mm / 1000 : 0.30,
        pod_name: specName || '',
        roof_openings: (form.roof_openings || []).filter(r => r.selected).map(({ selected, ...r }) => r),
        wall_u_value:  wallBu?.u_value  > 0 ? wallBu.u_value  : null,
        floor_u_value: floorBu?.u_value > 0 ? floorBu.u_value : null,
        roof_u_value:  roofBu?.u_value  > 0 ? roofBu.u_value  : null,
      }
      const result = await apiFetch('/drawings/all', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setDrawings(result)
      setShowBom(false)
    } catch (e) {
      setDrawError(e.message)
    } finally {
      setLoading(false)
    }
  }, [form])

  const downloadSvg = (svgString, key) => {
    const blob = new Blob([svgString], { type: 'image/svg+xml' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = `${key}.svg`
    a.click()
    URL.revokeObjectURL(url)
  }

  // ── Pod spec: new / load / save ──────────────────────────────────────────────
  const newSpec = () => {
    setSpecId(null)
    setSpecName('New Pod Spec')
    setForm(DEFAULT_FORM)
    setAssignments(DEFAULT_ASSIGNMENTS)
    setDrawings(null)
    setBom(null)
    setShowBom(false)
    setSaveError(null)
  }

  const loadSpec = async (spec) => {
    setSpecId(spec.id)
    setSpecName(spec.name)
    setForm(spec.geometry)
    setAssignments({
      ExternalWall: spec.wall_build_up_id ?? null,
      Floor:        spec.floor_build_up_id ?? null,
      Roof:         spec.roof_build_up_id ?? null,
    })
    setFinishSelections(spec.selected_finishes ?? null)
    setBom(null)
    setShowBom(false)
    setShowFinishes(false)
    setSaveError(null)
    setDrawings(null)
  }

  const saveSpec = async () => {
    setSaving(true)
    setSaveError(null)
    try {
      const payload = {
        name: specName,
        geometry: form,
        wall_build_up_id:  assignments.ExternalWall,
        floor_build_up_id: assignments.Floor,
        roof_build_up_id:  assignments.Roof,
        status: 'draft',
      }
      let saved
      if (specId) {
        saved = await apiFetch(`/pod-specs/${specId}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
        })
      } else {
        saved = await apiFetch('/pod-specs', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        setSpecId(saved.id)
      }
      const list = await apiFetch('/pod-specs')
      setPodSpecs(list)
    } catch (e) {
      setSaveError(e.message)
    } finally {
      setSaving(false)
    }
  }

  // ── Delete pod spec ──────────────────────────────────────────────────────────
  const deleteSpec = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    setDeleteError(null)
    try {
      await apiFetch(`/pod-specs/${deleteTarget.id}`, { method: 'DELETE' })
      const list = await apiFetch('/pod-specs')
      setPodSpecs(list)
      // If we just deleted the currently loaded spec, reset to blank
      if (specId === deleteTarget.id) {
        setSpecId(null)
        setSpecName('New Pod Spec')
        setForm(DEFAULT_FORM)
        setAssignments(DEFAULT_ASSIGNMENTS)
        setBom(null)
        setShowBom(false)
        setShowCost(false)
        setDrawings(null)
      }
      setDeleteTarget(null)
    } catch (e) {
      setDeleteError(e.message)
    } finally {
      setDeleting(false)
    }
  }

  // ── BOM ──────────────────────────────────────────────────────────────────────
  const generateBom = async () => {
    if (!specId) return
    setBomLoading(true)
    try {
      const data = await apiFetch(`/pod-specs/${specId}/bom`)
      setBom(data)
      setShowBom(true)
    } catch (e) {
      console.error('BOM error', e)
    } finally {
      setBomLoading(false)
    }
  }

  // ── PDF Review Pack ──────────────────────────────────────────────────────────
  const generatePdf = async () => {
    if (!specId) return
    setPdfLoading(true)
    setPdfError(null)
    try {
      const payload = {
        project_name: form.name || 'Pod',
        revision: 'A',
        packages,
        pkg_overrides: {},
      }
      const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
      const res = await fetch(`${API_BASE}/pod-specs/${specId}/generate-review-pack`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const err = await res.text()
        throw new Error(err || `HTTP ${res.status}`)
      }
      const blob = await res.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `review-pack-${(form.name || 'pod').toLowerCase().replace(/\s+/g, '-')}-revA.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setPdfError(e.message)
    } finally {
      setPdfLoading(false)
    }
  }

  const generateClientQuote = async () => {
    if (!specId) return
    setClientPdfLoading(true)
    setClientPdfError(null)
    try {
      const payload = {
        project_name: form.name || 'Pod',
        revision: 'A',
        packages,
        pkg_overrides: {},
        customer_name: '',
      }
      const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
      const res = await fetch(`${API_BASE}/pod-specs/${specId}/generate-client-quote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const err = await res.text()
        throw new Error(err || `HTTP ${res.status}`)
      }
      const blob = await res.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `pod-client-quote-${(form.name || 'pod').toLowerCase().replace(/\s+/g, '-')}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setClientPdfError(e.message)
    } finally {
      setClientPdfLoading(false)
    }
  }

  // ── Manufacture plan ─────────────────────────────────────────────────────────
  const generateManufacturePlan = async () => {
    setMfrPlanLoading(true)
    setMfrPlanError(null)
    try {
      const wallBu = buildUps.find(b => b.id === assignments.ExternalWall)
      const payload = {
        ...form,
        openings: form.openings.map(({ x_offset_m, ...o }) => ({
          ...o,
          height_m: o.shape === 'circular' ? o.width_m : o.height_m,
          x_offset_m: x_offset_m === '' || x_offset_m == null ? null : parseFloat(x_offset_m),
        })),
        wall_thick_m: wallBu?.total_thickness_mm > 0 ? wallBu.total_thickness_mm / 1000 : 0.25,
        pod_name: specName || '',
        roof_openings: (form.roof_openings || []).filter(r => r.selected).map(({ selected, ...r }) => r),
        ...mfrMeta,
      }
      const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
      const res = await fetch(`${API_BASE}/drawings/manufacture-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const errText = await res.text()
        let detail = errText
        try { detail = JSON.parse(errText)?.detail ?? errText } catch (_) {}
        throw new Error(detail || `HTTP ${res.status}`)
      }
      // Backend returns JSON {svg, drawing_number, ...}
      // Fallback: if response is raw SVG (content-type image/svg+xml), read as text
      const ct = res.headers.get('content-type') || ''
      let svgText
      if (ct.includes('application/json')) {
        const data = await res.json()
        svgText = data.svg
      } else {
        // Defensive: raw SVG response
        svgText = await res.text()
      }
      setDrawings(prev => ({ ...(prev || {}), manufacture_plan: svgText }))
      setActiveTab('manufacture_plan')
    } catch (e) {
      setMfrPlanError(e.message)
    } finally {
      setMfrPlanLoading(false)
    }
  }

  // ── Filtered build-up options per element type ───────────────────────────────
  const buOptions = (elementType) =>
    buildUps.filter(bu => bu.element_type === elementType)

  const buUValue = (id) => {
    const bu = buildUps.find(b => b.id === id)
    return bu?.u_value > 0 ? `${bu.u_value.toFixed(3)} W/m²K` : null
  }

  const buThickness = (id) => {
    const bu = buildUps.find(b => b.id === id)
    return bu?.total_thickness_mm > 0 ? `${Math.round(bu.total_thickness_mm)} mm` : null
  }

  const buPreviewLayers = (id) => {
    const bu = buildUps.find(b => b.id === id)
    if (!bu?.layers) return []
    return bu.layers
      .filter(l => Number(l.thickness_mm) > 0)
      .map(l => ({ name: l.material_name, thickness_mm: Number(l.thickness_mm), role: l.role }))
  }

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div className="flex h-full overflow-hidden">

      {/* ── Left panel ───────────────────────────────────────────────── */}
      <div className="w-80 shrink-0 bg-white border-r border-gray-200 flex flex-col overflow-y-auto">

        {/* Spec header */}
        <div className="px-5 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-3">
            <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Pod Designer</div>
            <button
              onClick={newSpec}
              className="text-xs text-gray-600 hover:text-gray-900 border border-gray-300 hover:border-gray-500 rounded px-2 py-1 transition-colors"
            >
              New
            </button>
          </div>

          {/* Name */}
          <input
            value={specName}
            onChange={e => setSpecName(e.target.value)}
            placeholder="Pod spec name"
            className="w-full bg-white border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-gray-600 mb-2"
          />

          {/* Saved specs list */}
          {podSpecs.length > 0 && (
            <div className="space-y-0.5 mt-1">
              <div className="text-[11px] font-medium text-gray-400 uppercase tracking-wider mb-1.5">Saved specs</div>
              {podSpecs.slice(0, 5).map(s => (
                <div
                  key={s.id}
                  className={`group flex items-center gap-1 rounded transition-colors ${
                    specId === s.id
                      ? 'bg-gray-100 border border-gray-300'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <button
                    onClick={() => loadSpec(s)}
                    className="flex-1 text-left text-xs px-2 py-1.5 min-w-0"
                  >
                    <div className={`font-medium truncate ${specId === s.id ? 'text-gray-900' : 'text-gray-500 group-hover:text-gray-900'}`}>{s.name}</div>
                    <div className="text-gray-400 tabular-nums">
                      {s.geometry?.width_m}m × {s.geometry?.length_m}m
                    </div>
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setDeleteTarget({ id: s.id, name: s.name }); setDeleteError(null) }}
                    title="Delete spec"
                    className="shrink-0 mr-1 p-1 text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all rounded"
                  >
                    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5">
                      <path d="M3 4h10M6 4V2.5a.5.5 0 01.5-.5h3a.5.5 0 01.5.5V4M5 4l.5 9h5l.5-9" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Geometry form */}
        <div className="flex-1 px-5 py-5 space-y-5">
          <div>
            <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Geometry</div>
            <div className="space-y-3">
              <Field label="Width — E/W (m)">
                <NumberInput value={form.width_m} onChange={v => set('width_m', v)} />
              </Field>
              <Field label="Length — N/S (m)">
                <NumberInput value={form.length_m} onChange={v => set('length_m', v)} />
              </Field>
              <Field label="Wall height / eaves (m)">
                <NumberInput value={form.wall_height_m} onChange={v => set('wall_height_m', v)} />
              </Field>
            </div>
          </div>

          {/* Roof */}
          <div>
            <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Roof</div>
            <div className="space-y-3">
              <Field label="Roof type">
                <Select value={form.roof_type} onChange={v => set('roof_type', v)} options={ROOF_TYPES} />
              </Field>
              {form.roof_type !== 'flat' && (
                <Field label="Pitch (°)">
                  <NumberInput value={form.roof_pitch_deg} onChange={v => set('roof_pitch_deg', v)} step={1} min={1} />
                </Field>
              )}
            </div>
          </div>

          {/* Openings */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Openings</div>
              <button
                onClick={addOpening}
                className="text-xs text-gray-600 hover:text-gray-900 font-medium transition-colors"
              >
                + Add
              </button>
            </div>
            {form.openings.length === 0 && (
              <p className="text-xs text-gray-400 italic">No openings — solid walls</p>
            )}
            <div className="space-y-3">
              {form.openings.map((o, i) => (
                <div key={i} className="bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-700">Opening {i + 1}</span>
                    <button
                      onClick={() => removeOpening(i)}
                      className="text-xs text-gray-400 hover:text-red-500 transition-colors"
                    >Remove</button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <Field label="Wall">
                      <Select value={o.wall} onChange={v => setOpening(i, 'wall', v)}
                        options={WALL_FACES.map(w => ({ value: w, label: w }))} />
                    </Field>
                    <Field label="Type">
                      <Select value={o.type} onChange={v => setOpening(i, 'type', v)}
                        options={OPENING_TYPES} />
                    </Field>
                    <Field label="Shape" className="col-span-2">
                      <Select value={o.shape} onChange={v => setOpening(i, 'shape', v)} options={OPENING_SHAPES} />
                    </Field>
                    {o.shape === 'circular' ? (
                      <Field label="Diameter (m)" className="col-span-2">
                        <NumberInput value={o.width_m} onChange={v => setOpening(i, 'width_m', v)} />
                      </Field>
                    ) : (
                      <>
                        <Field label="Width (m)">
                          <NumberInput value={o.width_m} onChange={v => setOpening(i, 'width_m', v)} />
                        </Field>
                        <Field label="Height (m)">
                          <NumberInput value={o.height_m} onChange={v => setOpening(i, 'height_m', v)} />
                        </Field>
                      </>
                    )}
                    <Field label={o.shape === 'circular' ? 'Bottom of opening (m)' : 'Sill height (m)'}>
                      <NumberInput value={o.sill_height_m} onChange={v => setOpening(i, 'sill_height_m', v)} step={0.1} min={0} />
                    </Field>
                    <Field label="Offset from left (m)">
                      <input
                        type="number"
                        value={o.x_offset_m}
                        step={0.1}
                        min={0}
                        placeholder="auto"
                        onChange={e => setOpening(i, 'x_offset_m', e.target.value)}
                        className="w-full bg-white border border-gray-300 rounded px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-gray-600 transition-colors"
                      />
                    </Field>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Roof Openings / Skylight */}
          <div>
            <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Roof Opening</div>
            <div className="flex items-center gap-2 mb-3">
              <button
                onClick={toggleSkylight}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${
                  skylightSelected ? 'bg-gray-900' : 'bg-gray-300'
                }`}
              >
                <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                  skylightSelected ? 'translate-x-4' : 'translate-x-1'
                }`} />
              </button>
              <span className="text-xs text-gray-700 font-medium">Add skylight / roof opening</span>
            </div>

            {skylightSelected && skylight && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-700">SKY-01</span>
                  <span className="text-[10px] text-gray-400 bg-gray-100 rounded px-1.5 py-0.5">for review</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Width (mm)">
                    <NumberInput value={skylight.width_mm} onChange={v => setSkylight('width_mm', v)} step={50} min={300} />
                  </Field>
                  <Field label="Height (mm)">
                    <NumberInput value={skylight.height_mm} onChange={v => setSkylight('height_mm', v)} step={50} min={300} />
                  </Field>
                  <Field label="X offset from W edge (mm)" className="col-span-2">
                    <input
                      type="number"
                      value={skylight.x_offset_mm}
                      step={50}
                      min={400}
                      placeholder="optional"
                      onChange={e => setSkylight('x_offset_mm', e.target.value)}
                      className="w-full bg-white border border-gray-300 rounded px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-gray-600 transition-colors"
                    />
                  </Field>
                  <Field label="Y offset from N edge (mm)" className="col-span-2">
                    <input
                      type="number"
                      value={skylight.y_offset_mm}
                      step={50}
                      min={400}
                      placeholder="optional"
                      onChange={e => setSkylight('y_offset_mm', e.target.value)}
                      className="w-full bg-white border border-gray-300 rounded px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-gray-600 transition-colors"
                    />
                  </Field>
                </div>

                {skylightError ? (
                  <div className="text-[11px] text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1.5">
                    ⚠ Skylight must be at least 400mm from external roof edges. Exact position to be confirmed after drawing review.
                    <div className="mt-0.5 text-red-500">{skylightError}</div>
                  </div>
                ) : (
                  <div className="text-[10px] text-gray-400 leading-relaxed">
                    Minimum 400mm clearance from external roof edges required. Position is preliminary — to be confirmed after drawing review by client. Internal wall / structure coordination to be confirmed during drawing review.
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Thermal Performance — compact previews for assigned build-ups */}
          {Object.entries(assignments).some(([, id]) => id !== null) && (
            <div>
              <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Thermal Performance</div>
              <div className="space-y-3">
                {['ExternalWall', 'Floor', 'Roof'].map(et => {
                  const id = assignments[et]
                  if (!id) return null
                  const bu = buildUps.find(b => b.id === id)
                  if (!bu) return null
                  const previewLayers = buPreviewLayers(id)
                  return (
                    <div key={et} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                      <div className="flex items-baseline justify-between mb-1.5">
                        <span className="text-xs font-semibold text-gray-700 truncate max-w-[140px]"
                          title={bu.name}>{ELEMENT_LABELS[et]}</span>
                        <div className="text-right shrink-0 ml-2">
                          {bu.u_value > 0 && (
                            <span className="text-xs text-gray-900 font-semibold tabular-nums">{bu.u_value.toFixed(3)}</span>
                          )}
                          {bu.u_value > 0 && bu.total_thickness_mm > 0 && (
                            <span className="text-gray-300 text-xs mx-1">·</span>
                          )}
                          {bu.total_thickness_mm > 0 && (
                            <span className="text-xs text-gray-500 tabular-nums">{Math.round(bu.total_thickness_mm)} mm</span>
                          )}
                        </div>
                      </div>
                      {previewLayers.length > 0 && (
                        <BuildUpLayerPreview layers={previewLayers} compact />
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Build-up assignment */}
          <div>
            <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Build-Up Spec</div>
            <div className="space-y-3">
              {['ExternalWall', 'Floor', 'Roof'].map(et => {
                const options = buOptions(et)
                const selected = assignments[et]
                const uv = selected ? buUValue(selected) : null
                const th = selected ? buThickness(selected) : null
                return (
                  <div key={et}>
                    <label className="block text-xs text-gray-500 mb-1">{ELEMENT_LABELS[et]}</label>
                    <select
                      value={selected ?? ''}
                      onChange={e => setAssignments(a => ({ ...a, [et]: parseInt(e.target.value) || null }))}
                      className="w-full bg-white border border-gray-300 rounded px-3 py-2 text-sm text-gray-900 focus:outline-none focus:border-gray-600 transition-colors"
                    >
                      <option value="">— unassigned —</option>
                      {options.map(bu => (
                        <option key={bu.id} value={bu.id}>{bu.name}</option>
                      ))}
                    </select>
                    {(uv || th) && (
                      <div className="text-xs text-gray-400 mt-0.5 pl-1 tabular-nums">
                        {uv && <span>{uv}</span>}
                        {uv && th && <span className="text-gray-300 mx-1">·</span>}
                        {th && <span>{th}</span>}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Action bar */}
        <div className="px-5 py-4 border-t border-gray-200 bg-gray-50 space-y-2">
          {(drawError || saveError) && (
            <p className="text-xs text-red-600">{drawError || saveError}</p>
          )}
          <button
            onClick={generate}
            disabled={loading}
            className="w-full bg-gray-900 hover:bg-gray-700 disabled:bg-gray-200 disabled:text-gray-400 text-white font-medium text-sm rounded py-2.5 transition-colors"
          >
            {loading ? 'Generating…' : 'Generate Drawings'}
          </button>
          <button
            onClick={saveSpec}
            disabled={saving}
            className="w-full bg-white border border-gray-300 hover:border-gray-500 disabled:opacity-50 text-gray-700 font-medium text-sm rounded py-2.5 transition-colors"
          >
            {saving ? 'Saving…' : specId ? 'Save Changes' : 'Save Spec'}
          </button>
          {specId && (
            <button
              type="button"
              onClick={generateBom}
              disabled={bomLoading}
              className="w-full text-xs text-gray-600 hover:text-gray-900 border border-gray-300 hover:border-gray-500 rounded py-2 transition-colors disabled:opacity-50"
            >
              {bomLoading ? 'Calculating…' : 'Generate BOM'}
            </button>
          )}
          {specId && (
            <div className="flex flex-col gap-1.5">
              <button
                type="button"
                onClick={generatePdf}
                disabled={pdfLoading}
                className="w-full text-xs font-medium text-white bg-gray-800 hover:bg-gray-900 disabled:bg-gray-400 rounded py-2 transition-colors"
              >
                {pdfLoading ? 'Generating…' : 'Generate Internal Technical Pack'}
              </button>
              <button
                type="button"
                onClick={generateClientQuote}
                disabled={clientPdfLoading}
                className="w-full text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 rounded py-2 transition-colors"
              >
                {clientPdfLoading ? 'Generating…' : 'Generate Client Quote PDF'}
              </button>
            </div>
          )}
          {pdfError && (
            <div className="text-[10px] text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1.5">
              Internal pack error: {pdfError}
            </div>
          )}
          {clientPdfError && (
            <div className="text-[10px] text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1.5">
              Client quote error: {clientPdfError}
            </div>
          )}

          {/* Manufacture Plan */}
          <div className="pt-2 border-t border-gray-100">
            <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Manufacture Plan</div>
            <div className="space-y-1.5">
              {[
                ['project_name',     'Project Name'],
                ['client_project_id','Client / Project ID'],
                ['drawing_number',   'Drawing No.'],
                ['drawn_by',         'Drawn By'],
                ['checked_by',       'Checked By'],
                ['revision',         'Revision'],
                ['status',           'Status'],
                ['issue_date',       'Issue Date'],
                ['scale_str',        'Scale'],
              ].map(([key, label]) => (
                <div key={key}>
                  <label className="block text-[10px] text-gray-400 mb-0.5">{label}</label>
                  <input
                    value={mfrMeta[key]}
                    onChange={e => setMfrMeta(m => ({ ...m, [key]: e.target.value }))}
                    className="w-full bg-white border border-gray-200 rounded px-2 py-1 text-xs text-gray-800 focus:outline-none focus:border-gray-500"
                  />
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={generateManufacturePlan}
              disabled={mfrPlanLoading}
              className="w-full mt-2 text-xs font-medium text-white bg-red-700 hover:bg-red-800 disabled:bg-red-300 rounded py-2 transition-colors"
            >
              {mfrPlanLoading ? 'Generating…' : 'Generate Manufacture Plan'}
            </button>
            {mfrPlanError && (
              <div className="text-[10px] text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1.5 mt-1">
                {mfrPlanError}
              </div>
            )}
          </div>

          {/* Compact cost card */}
          {bom && (() => {
            const fmt = n => `€${Math.round(n).toLocaleString('en')}`
            const matTotal = bom.total_cost ?? 0
            const pkgCount = [
              packages.roof_finish, packages.heating, packages.finishes, packages.groundworks,
              ...packages.ventilation, ...packages.cctv_data,
              ...(packages.pv_ready ? ['pv_ready'] : []),
              ...Object.keys(packages.furniture).filter(k => (packages.furniture[k] ?? 0) > 0),
            ].filter(Boolean).length
            return (
              <div className="mt-2 bg-gray-50 border border-gray-200 rounded-lg p-3 text-xs">
                <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Estimated Cost</div>
                <div className="flex justify-between mb-1">
                  <span className="text-gray-500">Materials</span>
                  <span className="font-medium text-gray-800 tabular-nums">{fmt(matTotal)}</span>
                </div>
                <div className="flex justify-between mb-1">
                  <span className="text-gray-500">Packages ({pkgCount} selected)</span>
                  <span className="text-gray-400 tabular-nums">see summary →</span>
                </div>
                <button type="button"
                  onClick={() => { setShowCost(true); setShowBom(false) }}
                  className="mt-2 w-full text-center text-[10px] text-gray-500 hover:text-gray-900 underline transition-colors"
                >
                  View Cost Summary
                </button>
              </div>
            )
          })()}
        </div>
      </div>

      {/* ── Right panel: drawings + BOM ───────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden bg-gray-50">
        {!drawings && !showBom && !showCost && !showFinishes ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
            <div className="w-12 h-12 mb-5 mx-auto">
              <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-full h-full text-gray-200">
                <rect x="6" y="6" width="36" height="36" rx="3" />
                <path d="M15 24h18M24 15v18" strokeLinecap="round" />
              </svg>
            </div>
            <h2 className="text-gray-900 font-semibold mb-2">No drawings yet</h2>
            <p className="text-gray-500 text-sm max-w-xs">
              Set dimensions, assign build-ups, then click{' '}
              <span className="text-gray-900 font-medium">Generate Drawings</span>.
              Save first to unlock the BOM.
            </p>
          </div>
        ) : (
          <>
            {/* Tab bar */}
            <div className="flex items-center border-b border-gray-200 bg-white px-4 shrink-0 overflow-x-auto">
              {drawings && DRAWING_TABS.filter(tab => drawings[tab.key]).map(tab => (
                <button
                  key={tab.key}
                  onClick={() => { setActiveTab(tab.key); setShowBom(false); setShowCost(false); setShowFinishes(false) }}
                  className={`px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                    !showBom && !showCost && !showFinishes && activeTab === tab.key
                      ? 'border-gray-900 text-gray-900'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
              {/* Finishes tab — always visible once spec is saved */}
              {specId && (
                <button
                  onClick={() => { setShowFinishes(true); setShowBom(false); setShowCost(false) }}
                  className={`px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                    showFinishes
                      ? 'border-blue-600 text-blue-700'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Finishes
                  {finishSelections?.items?.length > 0 && (
                    <span className="ml-1.5 text-[10px] bg-blue-100 text-blue-600 rounded-full px-1.5 py-0.5 font-medium">
                      {finishSelections.items.filter(i => i.included !== false).length}
                    </span>
                  )}
                </button>
              )}
              {bom && (
                <button
                  onClick={() => { setShowBom(false); setShowCost(true); setShowFinishes(false) }}
                  className={`px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                    showCost
                      ? 'border-gray-900 text-gray-900'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Cost Summary
                </button>
              )}
              {bom && (
                <button
                  onClick={() => { setShowBom(true); setShowCost(false); setShowFinishes(false) }}
                  className={`px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                    showBom
                      ? 'border-gray-900 text-gray-900'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  BOM
                </button>
              )}
              {drawings && !showBom && !showFinishes && (
                <button
                  onClick={() => downloadSvg(drawings[activeTab], activeTab)}
                  className="ml-auto shrink-0 text-xs text-gray-500 hover:text-gray-900 border border-gray-200 hover:border-gray-400 rounded px-3 py-1.5 transition-colors"
                >
                  Download SVG
                </button>
              )}
            </div>

            {/* Finishes tab */}
            {showFinishes && (
              <FinishSelector
                specId={specId}
                selections={finishSelections}
                onSelections={setFinishSelections}
              />
            )}

            {/* Cost Summary tab */}
            {showCost && (
              <CostSummary
                bom={bom}
                packages={packages}
                onPackages={setPackages}
                specId={specId}
                finishSelections={finishSelections}
              />
            )}

            {/* SVG viewer */}
            {drawings && !showBom && !showCost && !showFinishes && (
              <div className="flex-1 overflow-auto p-6">
                {drawings[activeTab] ? (
                  <div
                    className="bg-white rounded-lg shadow-sm border border-gray-200 mx-auto w-full [&>svg]:w-full [&>svg]:h-auto [&>svg]:display-block"
                    style={{ maxWidth: '960px' }}
                    dangerouslySetInnerHTML={{ __html: drawings[activeTab] }}
                  />
                ) : (
                  <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
                    No drawing for this tab yet
                  </div>
                )}
              </div>
            )}

            {/* BOM table */}
            {showBom && bom && (
              <div className="flex-1 overflow-auto p-6">
                {/* Element area summary + grand total */}
                <div className="flex gap-3 mb-6 flex-wrap">
                  {Object.entries(bom.areas).map(([et, area]) => (
                    area > 0 && (
                      <div key={et} className="bg-white border border-gray-200 rounded-lg px-4 py-3 text-center min-w-[88px]">
                        <div className="text-[11px] font-medium text-gray-400 uppercase tracking-wider mb-1">{ELEMENT_LABELS[et]}</div>
                        <div className="text-2xl font-semibold text-gray-900 tabular-nums">{area.toFixed(1)}</div>
                        <div className="text-xs text-gray-400">m²</div>
                      </div>
                    )
                  ))}
                  {bom.total_cost != null && (
                    <div className="bg-gray-900 border border-gray-700 rounded-lg px-5 py-3 text-center min-w-[120px] ml-auto">
                      <div className="text-[11px] font-medium text-gray-400 uppercase tracking-wider mb-1">Material cost</div>
                      <div className="text-2xl font-semibold text-white tabular-nums">
                        {bom.currency ?? '€'} {bom.total_cost.toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </div>
                      <div className="text-xs text-gray-500">priced lines only</div>
                    </div>
                  )}
                </div>

                {/* Material lines */}
                {['ExternalWall', 'Floor', 'Roof'].map(et => {
                  const lines = bom.lines.filter(l => l.element_type === et)
                  if (lines.length === 0) return null
                  return (
                    <div key={et} className="mb-8">
                      <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">
                        {ELEMENT_LABELS[et]} — {lines[0].build_up_name}
                      </div>
                      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs border-collapse">
                            <thead>
                              <tr className="border-b border-gray-200 bg-gray-50">
                                <th className="text-left py-2.5 px-3 font-medium text-gray-400 w-8">#</th>
                                <th className="text-left py-2.5 px-3 font-medium text-gray-400">Material</th>
                                <th className="text-left py-2.5 px-3 font-medium text-gray-400">Role</th>
                                <th className="text-left py-2.5 px-3 font-medium text-gray-400">Method</th>
                                <th className="text-right py-2.5 px-3 font-medium text-gray-400">mm</th>
                                <th className="text-right py-2.5 px-3 font-medium text-gray-400">Raw qty</th>
                                <th className="text-right py-2.5 px-3 font-medium text-gray-400">Waste</th>
                                <th className="text-right py-2.5 px-3 font-medium text-gray-400">Order qty</th>
                                <th className="text-left py-2.5 px-3 font-medium text-gray-400">Unit</th>
                                <th className="text-right py-2.5 px-3 font-medium text-gray-400">Price/unit</th>
                                <th className="text-right py-2.5 px-3 font-medium text-gray-400">Line cost</th>
                                <th className="text-left py-2.5 px-3 font-medium text-gray-400">Ref</th>
                              </tr>
                            </thead>
                            <tbody>
                              {lines.map((l, i) => (
                                <tr key={i} className={`border-b border-gray-100 last:border-b-0 ${l.unit === 'lm' ? 'bg-amber-50/40' : ''}`}>
                                  <td className="py-2 px-3 text-gray-400 tabular-nums">{l.position_order}</td>
                                  <td className="py-2 px-3 text-gray-900 font-medium">{l.material_name}</td>
                                  <td className="py-2 px-3 text-gray-500">{l.role || '—'}</td>
                                  <td className="py-2 px-3 text-gray-400">{l.method || '—'}</td>
                                  <td className="py-2 px-3 text-right text-gray-600 tabular-nums">{l.thickness_mm}</td>
                                  <td className="py-2 px-3 text-right text-gray-700 tabular-nums">{(l.raw_quantity ?? l.area_m2).toFixed(2)}</td>
                                  <td className="py-2 px-3 text-right text-gray-400 tabular-nums">{l.waste_factor ? `×${l.waste_factor.toFixed(2)}` : '—'}</td>
                                  <td className="py-2 px-3 text-right text-gray-900 font-semibold tabular-nums">{(l.order_quantity ?? l.area_m2).toFixed(2)}</td>
                                  <td className="py-2 px-3">
                                    {l.unit === 'lm'
                                      ? <span className="text-amber-700 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5">lm</span>
                                      : <span className="text-gray-500">{l.unit || 'm²'}</span>
                                    }
                                  </td>
                                  <td className="py-2 px-3 text-right tabular-nums text-gray-600">
                                    {l.price_per_unit != null
                                      ? `${l.currency ?? '€'} ${l.price_per_unit.toFixed(2)}`
                                      : <span className="text-gray-300">—</span>
                                    }
                                  </td>
                                  <td className="py-2 px-3 text-right tabular-nums font-semibold text-gray-900">
                                    {l.line_cost != null
                                      ? `${l.currency ?? '€'} ${l.line_cost.toFixed(2)}`
                                      : <span className="text-gray-300 font-normal">—</span>
                                    }
                                  </td>
                                  <td className="py-2 px-3 text-gray-400 font-mono text-[11px]">{l.supplier_ref}</td>
                                </tr>
                              ))}
                            </tbody>
                            {/* Subtotal row for this element group */}
                            {(() => {
                              const priced = lines.filter(l => l.line_cost != null)
                              if (priced.length === 0) return null
                              const subtotal = priced.reduce((s, l) => s + l.line_cost, 0)
                              const cur = priced[0].currency ?? '€'
                              return (
                                <tfoot>
                                  <tr className="border-t border-gray-200 bg-gray-50">
                                    <td colSpan={10} className="py-2.5 px-3 text-right text-xs font-medium text-gray-500">
                                      {ELEMENT_LABELS[et]} subtotal
                                    </td>
                                    <td className="py-2.5 px-3 text-right text-xs font-semibold text-gray-900 tabular-nums">
                                      {cur} {subtotal.toFixed(2)}
                                    </td>
                                    <td />
                                  </tr>
                                </tfoot>
                              )
                            })()}
                          </table>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </>
        )}
      </div>

      {/* ── Delete pod spec confirmation modal ───────────────────────────── */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 p-6">
            <div className="text-sm font-semibold text-gray-900 mb-2">Delete pod spec?</div>
            <div className="text-sm text-gray-600 mb-4">
              <span className="font-medium text-gray-900">{deleteTarget.name}</span> will be permanently deleted. This cannot be undone.
            </div>
            {deleteError && (
              <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2 mb-4">
                {deleteError}
              </div>
            )}
            <div className="flex gap-3">
              <button
                onClick={() => { setDeleteTarget(null); setDeleteError(null) }}
                className="flex-1 bg-white border border-gray-300 hover:border-gray-500 text-gray-700 font-medium text-sm rounded py-2 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={deleteSpec}
                disabled={deleting}
                className="flex-1 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-medium text-sm rounded py-2 transition-colors"
              >
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
