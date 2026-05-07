import { useState, useEffect } from 'react'
import { apiFetch } from '../api/client'

// ── Package group definitions ─────────────────────────────────────────────────
// type: 'radio' = one choice at a time | 'multi' = checkboxes | 'qty' = with quantity

export const PACKAGE_GROUPS = [
  {
    id: 'roof_finish', label: 'Roof Finish', type: 'bool', phase: 'base_envelope',
    options: [
      { code: 'roof_epdm_standard', name: 'EPDM Roof Finish', low: 700, target: 700, high: 700, notes: 'EPDM membrane, adhesive, trims and outlet allowance.' },
    ],
  },
  {
    id: 'heating', label: 'Heating', type: 'radio', phase: 'services_comfort',
    options: [
      { code: 'electric_radiators_base',  name: 'Electric Radiators — Base',      low: 250,  target: 400,  high: 600,  notes: 'Slim wall-mounted electric radiators. Final electrical design by qualified installer.' },
      { code: 'electric_radiators_smart', name: 'Smart Electric Radiators',        low: 700,  target: 1000, high: 1400, notes: 'Smart controls / WiFi radiator allowance.' },
      { code: 'air_to_air_heat_pump',     name: 'Air-to-Air Heat Pump Upgrade',   low: 1500, target: 2200, high: 3000, notes: 'Heating and cooling upgrade. Installation by qualified installer.' },
    ],
  },
  {
    id: 'ventilation', label: 'Ventilation', type: 'multi', phase: 'services_comfort',
    options: [
      { code: 'trickle_vents_allowance', name: 'Trickle Vents',              low: 80,   target: 140,  high: 200,  notes: 'Background ventilation allowance via window trickle vents.' },
      { code: 'bathroom_extract',        name: 'Bathroom Extract Fan',       low: 120,  target: 200,  high: 300,  notes: 'Required where bathroom / shower room is selected.' },
      { code: 'kitchen_extract',         name: 'Kitchen Extract Provision',  low: 200,  target: 380,  high: 600,  notes: 'Cooker hood or wall extract provision.' },
      { code: 'mvhr_premium',            name: 'MVHR Premium Option',        low: 1500, target: 2200, high: 3000, notes: 'Premium option only, not base specification.' },
    ],
  },
  {
    id: 'cctv_data', label: 'CCTV / Data', type: 'multi', phase: 'optional_addons',
    options: [
      { code: 'cctv_cat6_prewire',        name: 'CAT6 Prewire',              low: 350, target: 600,  high: 800,  notes: 'CAT6 home-runs to external camera positions and data/comms location.' },
      { code: 'basic_4_camera_ip',        name: 'Basic 4-Camera IP Package', low: 800, target: 1400, high: 2000, notes: 'Basic IP cameras, PoE/NVR allowance. Brand to be confirmed.' },
    ],
  },
  {
    id: 'pv_ready', label: 'PV-Ready Provision', type: 'bool', phase: 'optional_addons',
    options: [
      { code: 'pv_ready_roof', name: 'PV-Ready Roof Provision', low: 250, target: 400, high: 600, notes: 'Spare conduit, marked fixing/ballast zones. PV installation not included.' },
    ],
  },
  {
    id: 'finishes', label: 'Interior Finishes', type: 'radio', phase: 'interior_finish',
    options: [
      { code: 'budget_finishes',   name: 'Budget Internal Finishes',   low: 2500, target: 3200, high: 4000, notes: 'Basic flooring, paint, skirting/trim allowance.' },
      { code: 'standard_finishes', name: 'Standard Internal Finishes', low: 4500, target: 5800, high: 7000, notes: 'Improved flooring, decorating, trims and internal finish allowance.' },
    ],
  },
  {
    id: 'furniture', label: 'Furniture / Client Discretion', type: 'qty', phase: 'optional_addons',
    options: [
      { code: 'kitchenette',    name: 'Kitchenette Allowance',        low: 600, target: 600,  high: 600,  notes: 'Client discretion allowance.' },
      { code: 'single_bed',    name: 'Single Bed (frame + mattress)', low: 270, target: 270,  high: 270,  notes: 'Client discretion allowance.' },
      { code: 'double_bed',    name: 'Double Bed (frame + mattress)', low: 370, target: 370,  high: 370,  notes: 'Client discretion allowance.' },
      { code: 'office_desk',   name: 'Office Desk + Chair',           low: 370, target: 370,  high: 370,  notes: 'Client discretion allowance.' },
      { code: 'vanity_unit',   name: 'Vanity Unit Allowance',         low: 150, target: 150,  high: 150,  notes: 'Budget vanity allowance. Client-selected sanitaryware may cost more.' },
    ],
  },
  {
    id: 'groundworks', label: 'Concrete / Groundworks', type: 'radio', phase: 'groundworks_slab',
    options: [
      { code: 'concrete_material_only',   name: 'Concrete Material Only',           low: null, target: null, high: null, notes: 'From BOM concrete total. Groundworks, labour, formwork excluded.' },
      { code: 'basic_groundworks_pkg',    name: 'Basic Groundworks Package',         low: 2000, target: 3500, high: 5000, notes: 'High-level provisional allowance only.' },
    ],
  },
]

// All option objects keyed by code for O(1) lookup
export const PKG_BY_CODE = Object.fromEntries(
  PACKAGE_GROUPS.flatMap(g => g.options.map(o => [o.code, { ...o, groupId: g.id, phase: g.phase }]))
)

// ── Helpers to compute active codes from packages state ───────────────────────

export function activeCodes(packages) {
  const codes = []
  for (const g of PACKAGE_GROUPS) {
    if (g.type === 'radio')  { if (packages[g.id]) codes.push(packages[g.id]) }
    if (g.type === 'multi')  { codes.push(...(packages[g.id] || [])) }
    if (g.type === 'bool')   { if (packages[g.id]) codes.push(g.options[0].code) }
    if (g.type === 'qty')    {
      const fm = packages[g.id] || {}
      g.options.forEach(o => { if ((fm[o.code] ?? 0) > 0) codes.push(o.code) })
    }
  }
  return codes
}

// ── Phase mapping: BOM role → cost phase ─────────────────────────────────────

const ROLE_PHASE = {
  internal_finish: 'base_envelope', sheathing: 'base_envelope',
  insulation: 'base_envelope',      framing_zone: 'base_envelope',
  framing_zone_timber: 'base_envelope', framing_zone_pir: 'base_envelope',
  structure: 'groundworks_slab',    cladding: 'base_envelope',
  external_finish: 'base_envelope', vcl: 'base_envelope',
  breather: 'base_envelope',        airtight_layer: 'base_envelope',
  service_void: 'base_envelope',    cavity: 'base_envelope',
  opening: 'base_envelope',
}

function linePhase(line) { return ROLE_PHASE[line.role] || 'base_envelope' }

// ── Quantity resolver for provisional allowances ──────────────────────────────

function resolveQty(pa, bom, qtyOverrides) {
  if (qtyOverrides[pa.id] !== undefined) return qtyOverrides[pa.id]
  const oc = bom.opening_counts || {}
  const areas = bom.areas || {}
  switch (pa.quantity_source) {
    case 'opening_count_window':    return oc.window    || 0
    case 'opening_count_door':      return oc.door      || 0
    case 'opening_count_rooflight': return oc.rooflight || oc.rooflights || 0
    case 'floor_area':              return areas.Floor  || 0
    case 'wall_ceiling_area':       return (areas.ExternalWall || 0) + (areas.Roof || 0)
    default:                        return pa.default_quantity || 0
  }
}

// ── Format helpers ────────────────────────────────────────────────────────────

const fmt  = n => n == null ? '—' : `€${Math.round(n).toLocaleString('en')}`
const fmtD = n => `€${n.toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

// ── ProvisionalRow — single editable allowance line ──────────────────────────

function ProvisionalRow({ pa, bom, included, quantity, rate, onToggle, onQtyChange, onRateChange }) {
  const cost = included ? rate * quantity : 0
  const isAutoQty = pa.quantity_source !== 'manual'
  return (
    <tr className={`border-b border-gray-100 last:border-b-0 ${!included ? 'opacity-50' : ''}`}>
      <td className="py-1.5 px-3">
        <input type="checkbox" checked={included} onChange={onToggle} className="rounded" />
      </td>
      <td className="py-1.5 px-3 text-gray-800 text-xs">
        {pa.name}
        {pa.is_client_discretion && (
          <span className="ml-1.5 text-[10px] text-gray-400 bg-gray-100 rounded px-1 py-0.5">client discretion</span>
        )}
      </td>
      <td className="py-1.5 px-3 text-right">
        <input type="number" min="0" step={pa.unit === 'm2' || pa.unit === 'lm' ? '0.1' : '1'}
          value={quantity} onChange={e => onQtyChange(parseFloat(e.target.value) || 0)}
          disabled={isAutoQty && quantity > 0}
          title={isAutoQty ? `Auto from ${pa.quantity_source}` : 'Manual quantity'}
          className={`w-16 text-right text-xs tabular-nums border rounded px-1.5 py-0.5 focus:outline-none focus:border-gray-600 ${
            isAutoQty && quantity > 0 ? 'bg-gray-50 border-gray-200 text-gray-500 cursor-not-allowed' : 'bg-white border-gray-300 text-gray-900'
          }`}
        />
        <span className="ml-1 text-[10px] text-gray-400">{pa.unit}</span>
      </td>
      <td className="py-1.5 px-3 text-right">
        <span className="text-[10px] text-gray-400 mr-0.5">€</span>
        <input type="number" min="0" step="0.5" value={rate}
          onChange={e => onRateChange(parseFloat(e.target.value) || 0)}
          className="w-16 text-right text-xs tabular-nums border border-gray-300 rounded px-1.5 py-0.5 bg-white text-gray-900 focus:outline-none focus:border-gray-600"
        />
        <span className="ml-1 text-[10px] text-gray-400">/{pa.unit}</span>
      </td>
      <td className="py-1.5 px-3 text-right text-xs font-medium tabular-nums text-gray-900">
        {included && cost > 0 ? fmtD(cost) : <span className="text-gray-300">—</span>}
      </td>
    </tr>
  )
}

// ── Main export ───────────────────────────────────────────────────────────────

// ── Finish cost group section ─────────────────────────────────────────────────

function FinishCostGroup({ groupName, lines }) {
  const [open, setOpen] = useState(true)
  const total = lines.filter(l => l.line_cost != null && l.included !== false)
    .reduce((s, l) => s + l.line_cost, 0)

  const fmtD = n => `€${n.toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  const fmt  = n => n == null ? '—' : `€${Math.round(n).toLocaleString('en')}`

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden mb-3">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full px-3 py-2 flex items-center justify-between border-b border-gray-100 text-left"
      >
        <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">{groupName}</span>
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-gray-900 tabular-nums">{fmt(total)}</span>
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"
            className={`w-3.5 h-3.5 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}>
            <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </button>
      {open && (
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="text-left py-2 px-3 font-medium text-gray-400">Item</th>
              <th className="text-left py-2 px-3 font-medium text-gray-400">Source</th>
              <th className="text-right py-2 px-3 font-medium text-gray-400">Qty</th>
              <th className="text-left py-2 px-3 font-medium text-gray-400">Unit</th>
              <th className="text-right py-2 px-3 font-medium text-gray-400">Rate</th>
              <th className="text-right py-2 px-3 font-medium text-gray-400">Cost</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((l, i) => (
              <tr key={i} className={`border-b border-gray-100 last:border-b-0 ${l.included === false ? 'opacity-40' : ''}`}>
                <td className="py-1.5 px-3 text-gray-800">
                  <div>{l.name}</div>
                  {l.quantity_rule && l.quantity_rule !== 'each' && (
                    <div className="text-[10px] text-gray-400">{l.quantity_rule.replace(/_/g,' ')}</div>
                  )}
                </td>
                <td className="py-1.5 px-3 text-gray-400 text-[10px]">
                  {l.source === 'package'
                    ? <span className="text-blue-600 bg-blue-50 rounded px-1 py-0.5">{l.package_name || 'Package'}</span>
                    : <span className="text-gray-400">manual</span>
                  }
                </td>
                <td className="py-1.5 px-3 text-right tabular-nums text-gray-600">{l.quantity}</td>
                <td className="py-1.5 px-3 text-gray-500">{l.unit || '—'}</td>
                <td className="py-1.5 px-3 text-right tabular-nums text-gray-500">
                  {l.unit_cost != null ? fmtD(l.unit_cost) : <span className="text-amber-500">no price</span>}
                </td>
                <td className="py-1.5 px-3 text-right tabular-nums font-medium text-gray-900">
                  {l.line_cost != null ? fmtD(l.line_cost) : <span className="text-amber-500">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

// ── Main export ───────────────────────────────────────────────────────────────

export default function CostSummary({ bom, packages, onPackages, specId, finishSelections }) {
  const [allowances, setAllowances] = useState([])
  const [provError, setProvError]   = useState(null)
  const [included, setIncluded]     = useState({})
  const [qtyOverrides, setQtyOverrides]   = useState({})
  const [rateOverrides, setRateOverrides] = useState({})
  // Per-package cost overrides: { [code]: { low?, high? } }
  const [pkgOverrides, setPkgOverrides]   = useState({})
  const [detail, setDetail] = useState(
    Object.fromEntries([
      'base_envelope','interior_finish','services_comfort',
      'groundworks_slab','optional_addons','finishes_catalogue',
    ].map(p => [p, true]))
  )

  // ── Markup / selling price state ────────────────────────────────────────────
  const [settings, setSettings]           = useState(null)
  const [settingsOpen, setSettingsOpen]   = useState(false)
  const [settingsDraft, setSettingsDraft] = useState(null)
  const [settingsSaving, setSettingsSaving] = useState(false)

  useEffect(() => {
    apiFetch('/settings').then(s => setSettings(s)).catch(() => {})
  }, [])

  const computeSellingPrice = (cost, s) => {
    if (!s || !cost) return null
    const markupAmt   = Math.round(cost * s.default_markup_percent / 100 * 100) / 100
    const exVat       = Math.round((cost + markupAmt) * 100) / 100
    const vatAmt      = Math.round(exVat * s.vat_rate_percent / 100 * 100) / 100
    const incVat      = Math.round((exVat + vatAmt) * 100) / 100
    const rtn         = s.round_to_nearest > 0
      ? Math.ceil(incVat / s.round_to_nearest) * s.round_to_nearest
      : incVat
    return { markupAmt, exVat, vatAmt, incVat, rounded: rtn }
  }

  const openSettings = () => {
    setSettingsDraft(settings ? { ...settings } : null)
    setSettingsOpen(true)
  }
  const saveSettings = () => {
    if (!settingsDraft) return
    setSettingsSaving(true)
    apiFetch('/settings', { method: 'PUT', body: JSON.stringify(settingsDraft) })
      .then(s => { setSettings(s); setSettingsOpen(false) })
      .catch(() => {})
      .finally(() => setSettingsSaving(false))
  }

  useEffect(() => {
    apiFetch('/provisional-allowances')
      .then(data => {
        setAllowances(data)
        setIncluded(Object.fromEntries(data.map(a => [a.id, a.is_included_by_default])))
      })
      .catch(err => { console.error(err); setProvError('Could not load provisional allowances — is the backend running?') })
  }, [])

  // ── Finish catalogue costs ────────────────────────────────────────────────────
  const [finishLines, setFinishLines]   = useState([])
  const [finishTotal, setFinishTotal]   = useState(0)
  const [finishLoading, setFinishLoading] = useState(false)

  // Stable key: re-fetch only when specId changes or the selections content changes
  const finishSelectionsKey = specId
    ? `${specId}:${JSON.stringify(finishSelections ?? null)}`
    : null

  useEffect(() => {
    if (!specId) { setFinishLines([]); setFinishTotal(0); return }
    setFinishLoading(true)
    apiFetch(`/pod-specs/${specId}/finish-cost`)
      .then(data => {
        const lines = data.lines ?? []
        setFinishLines(lines)
        setFinishTotal(data.total ?? 0)
      })
      .catch(() => { setFinishLines([]); setFinishTotal(0) })
      .finally(() => setFinishLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [finishSelectionsKey])

  if (!bom) {
    return (
      <div className="flex-1 flex items-center justify-center text-sm text-gray-400 py-16">
        Generate the BOM first to see cost breakdown.
      </div>
    )
  }

  const bomLines = bom.lines || []

  // ── Package helpers ─────────────────────────────────────────────────────────

  const setRadio   = (gid, code) => onPackages(p => ({ ...p, [gid]: p[gid] === code ? null : code }))
  const toggleMulti = (gid, code) => onPackages(p => {
    const cur = p[gid] || []
    return { ...p, [gid]: cur.includes(code) ? cur.filter(c => c !== code) : [...cur, code] }
  })
  const toggleBool  = (gid) => onPackages(p => ({ ...p, [gid]: !p[gid] }))
  const setQtyFurn  = (code, qty) => onPackages(p => ({
    ...p, furniture: { ...p.furniture, [code]: Math.max(0, qty) }
  }))

  const isActive = (gid, code) => {
    const g = PACKAGE_GROUPS.find(x => x.id === gid)
    if (!g) return false
    if (g.type === 'radio') return packages[gid] === code
    if (g.type === 'multi') return (packages[gid] || []).includes(code)
    if (g.type === 'bool')  return !!packages[gid]
    if (g.type === 'qty')   return (packages.furniture?.[code] ?? 0) > 0
    return false
  }

  const pkgLow    = code => pkgOverrides[code]?.low  ?? PKG_BY_CODE[code]?.low
  const pkgHigh   = code => pkgOverrides[code]?.high ?? PKG_BY_CODE[code]?.high
  const pkgTarget = code => {
    const lo = pkgLow(code); const hi = pkgHigh(code)
    return (lo != null && hi != null) ? Math.round((lo + hi) / 2) : (lo ?? hi)
  }
  const setPkgOverride = (code, field, val) =>
    setPkgOverrides(o => ({ ...o, [code]: { ...o[code], [field]: val } }))

  // ── Phase totals ────────────────────────────────────────────────────────────

  const matPhaseTotal = phase =>
    bomLines.filter(l => linePhase(l) === phase && l.line_cost != null)
      .reduce((s, l) => s + l.line_cost, 0)

  const pkgPhaseTotal = phase => {
    let total = 0
    for (const g of PACKAGE_GROUPS) {
      if (g.phase !== phase) continue
      for (const o of g.options) {
        if (!isActive(g.id, o.code)) continue
        const qty = g.type === 'qty' ? (packages.furniture?.[o.code] ?? 1) : 1
        const t = pkgTarget(o.code)
        if (t != null) total += t * qty
      }
    }
    return total
  }

  const effRate = pa => rateOverrides[pa.id] ?? pa.default_unit_rate
  const effQty  = pa => resolveQty(pa, bom, qtyOverrides)
  const effIncl = pa => included[pa.id] ?? pa.is_included_by_default
  const effCost = pa => effIncl(pa) ? effRate(pa) * effQty(pa) : 0
  const toggleIncl  = id => setIncluded(s => ({ ...s, [id]: !s[id] }))
  const setQtyPA    = (id, v) => setQtyOverrides(s => ({ ...s, [id]: v }))
  const setRatePA   = (id, v) => setRateOverrides(s => ({ ...s, [id]: v }))

  const provPhaseTotal = phase =>
    allowances.filter(a => a.cost_phase === phase).reduce((s, a) => s + effCost(a), 0)

  const phaseTotal = phase => matPhaseTotal(phase) + pkgPhaseTotal(phase) + provPhaseTotal(phase)

  const PHASES = ['base_envelope', 'interior_finish', 'services_comfort', 'groundworks_slab', 'optional_addons']

  // Grand totals with low/high
  const pkgLowTotal  = PACKAGE_GROUPS.flatMap(g => g.options.filter(o => isActive(g.id, o.code)).map(o => {
    const qty = g.type === 'qty' ? (packages.furniture?.[o.code] ?? 1) : 1
    return (pkgLow(o.code) ?? pkgTarget(o.code) ?? 0) * qty
  })).reduce((s, v) => s + v, 0)
  const pkgHighTotal = PACKAGE_GROUPS.flatMap(g => g.options.filter(o => isActive(g.id, o.code)).map(o => {
    const qty = g.type === 'qty' ? (packages.furniture?.[o.code] ?? 1) : 1
    return (pkgHigh(o.code) ?? pkgTarget(o.code) ?? 0) * qty
  })).reduce((s, v) => s + v, 0)
  const matTotal  = (bom.total_cost ?? 0) + allowances.reduce((s, a) => s + effCost(a), 0)
  const grandLow  = Math.round(matTotal + pkgLowTotal  + (finishTotal ?? 0))
  const grandHigh = Math.round(matTotal + pkgHighTotal + (finishTotal ?? 0))

  const toggleDetail = p => setDetail(d => ({ ...d, [p]: !d[p] }))

  // ── Reusable section wrapper ────────────────────────────────────────────────
  const Section = ({ id, title, subtitle, children }) => (
    <div className="mb-8">
      <button type="button" onClick={() => toggleDetail(id)}
        className="w-full flex items-center justify-between mb-3 text-left group">
        <div>
          <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">{title}</div>
          {subtitle && <div className="text-xs text-gray-500 mt-0.5">{subtitle}</div>}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-gray-900 tabular-nums">{fmt(phaseTotal(id))}</span>
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"
            className={`w-3.5 h-3.5 text-gray-400 transition-transform ${detail[id] ? 'rotate-180' : ''}`}>
            <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </button>
      {detail[id] && <div className="space-y-3">{children}</div>}
    </div>
  )

  // ── BOM materials table ─────────────────────────────────────────────────────
  const MatTable = ({ phase }) => {
    const lines = bomLines.filter(l => linePhase(l) === phase)
    if (lines.length === 0) return null
    const unpriced = lines.filter(l => l.line_cost == null)
    return (
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="px-3 py-2 border-b border-gray-100 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
          Material schedule
        </div>
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="text-left py-2 px-3 font-medium text-gray-400">Material</th>
              <th className="text-right py-2 px-3 font-medium text-gray-400">Qty</th>
              <th className="text-left py-2 px-3 font-medium text-gray-400">Unit</th>
              <th className="text-right py-2 px-3 font-medium text-gray-400">Rate</th>
              <th className="text-right py-2 px-3 font-medium text-gray-400">Cost</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((l, i) => (
              <tr key={i} className={`border-b border-gray-100 last:border-b-0 ${l.unit === 'lm' ? 'bg-amber-50/30' : ''}`}>
                <td className="py-1.5 px-3 text-gray-800">{l.material_name}</td>
                <td className="py-1.5 px-3 text-right tabular-nums text-gray-600">{l.order_quantity.toFixed(2)}</td>
                <td className="py-1.5 px-3 text-gray-500">
                  {l.unit === 'lm'
                    ? <span className="text-amber-700 bg-amber-50 border border-amber-200 rounded px-1 text-[10px]">lm</span>
                    : l.unit}
                </td>
                <td className="py-1.5 px-3 text-right tabular-nums text-gray-500">
                  {l.price_per_unit != null ? fmtD(l.price_per_unit) : <span className="text-amber-500">no price</span>}
                </td>
                <td className="py-1.5 px-3 text-right tabular-nums font-medium text-gray-900">
                  {l.line_cost != null ? fmtD(l.line_cost) : <span className="text-amber-500">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {unpriced.length > 0 && (
          <div className="px-3 py-2 bg-amber-50 border-t border-amber-100 text-[10px] text-amber-700">
            {unpriced.length} material{unpriced.length > 1 ? 's' : ''} missing price: {unpriced.map(l => l.material_name.split(' — ')[0]).join(', ')}
          </div>
        )}
      </div>
    )
  }

  // ── Package group table for a phase ────────────────────────────────────────
  const PkgGroupSection = ({ group }) => {
    const g = group
    const isRadio = g.type === 'radio'
    const isQty   = g.type === 'qty'
    const isBool  = g.type === 'bool'

    return (
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="px-3 py-2 border-b border-gray-100 text-[10px] font-semibold text-gray-400 uppercase tracking-wider flex items-center justify-between">
          <span>{g.label}</span>
          {isRadio && <span className="font-normal normal-case text-gray-300">choose one</span>}
          {isQty   && <span className="font-normal normal-case text-gray-300">client discretion</span>}
        </div>
        <div className="divide-y divide-gray-100">
          {g.options.map(opt => {
            const active  = isActive(g.id, opt.code)
            const qty     = isQty ? (packages.furniture?.[opt.code] ?? 0) : 1
            const lo      = pkgLow(opt.code)
            const hi      = pkgHigh(opt.code)
            const lineCost = active ? (pkgTarget(opt.code) ?? 0) * qty : 0
            return (
              <div key={opt.code} className={`px-3 py-2.5 ${active ? 'bg-gray-50' : ''}`}>
                <div className="flex items-start gap-2.5">
                  {/* Toggle */}
                  {isRadio && (
                    <button type="button" onClick={() => setRadio(g.id, opt.code)}
                      className={`mt-0.5 w-4 h-4 rounded-full border-2 shrink-0 transition-colors ${active ? 'border-gray-900 bg-gray-900' : 'border-gray-300'}`}
                    />
                  )}
                  {(g.type === 'multi') && (
                    <input type="checkbox" checked={active}
                      onChange={() => toggleMulti(g.id, opt.code)}
                      className="mt-0.5 rounded shrink-0" />
                  )}
                  {isBool && (
                    <input type="checkbox" checked={active}
                      onChange={() => toggleBool(g.id)}
                      className="mt-0.5 rounded shrink-0" />
                  )}
                  {isQty && (
                    <input type="number" min="0" step="1" value={qty}
                      onChange={e => setQtyFurn(opt.code, parseInt(e.target.value) || 0)}
                      className="w-12 text-center text-xs border border-gray-300 rounded px-1 py-0.5 bg-white text-gray-900 shrink-0" />
                  )}

                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className={`text-xs font-medium ${active ? 'text-gray-900' : 'text-gray-500'}`}>{opt.name}</span>
                      <div className="shrink-0 text-right">
                        {active && lineCost > 0 && (
                          <span className="text-xs font-semibold text-gray-900 tabular-nums">{fmt(lineCost)}</span>
                        )}
                        {!active && lo != null && (
                          <span className="text-[10px] text-gray-300 tabular-nums">{fmt(lo)} – {fmt(hi)}</span>
                        )}
                      </div>
                    </div>
                    {active && lo != null && (
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-[10px] text-gray-400">Range:</span>
                        <div className="flex items-center gap-1">
                          <span className="text-[10px] text-gray-400">Low</span>
                          <input type="number" value={pkgOverrides[opt.code]?.low ?? lo} min="0"
                            onChange={e => setPkgOverride(opt.code, 'low', parseFloat(e.target.value) || 0)}
                            className="w-16 text-xs tabular-nums border border-gray-200 rounded px-1 py-0.5 bg-white text-gray-700" />
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-[10px] text-gray-400">High</span>
                          <input type="number" value={pkgOverrides[opt.code]?.high ?? hi} min="0"
                            onChange={e => setPkgOverride(opt.code, 'high', parseFloat(e.target.value) || 0)}
                            className="w-16 text-xs tabular-nums border border-gray-200 rounded px-1 py-0.5 bg-white text-gray-700" />
                        </div>
                      </div>
                    )}
                    {opt.notes && (
                      <div className="text-[10px] text-gray-400 mt-0.5 leading-relaxed">{opt.notes}</div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  // ── Provisional sums table ──────────────────────────────────────────────────
  const ProvTable = ({ phase }) => {
    const items = allowances.filter(a => a.cost_phase === phase)
    if (items.length === 0) return null
    return (
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="px-3 py-2 border-b border-gray-100 text-[10px] font-semibold text-gray-400 uppercase tracking-wider flex items-center justify-between">
          <span>Provisional sums</span>
          <span className="text-gray-300 font-normal normal-case">Tick to include · edit qty &amp; rate</span>
        </div>
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="py-2 px-3 w-8" />
              <th className="text-left py-2 px-3 font-medium text-gray-400">Item</th>
              <th className="text-right py-2 px-3 font-medium text-gray-400">Qty</th>
              <th className="text-right py-2 px-3 font-medium text-gray-400">Rate</th>
              <th className="text-right py-2 px-3 font-medium text-gray-400">Cost</th>
            </tr>
          </thead>
          <tbody>
            {items.map(pa => (
              <ProvisionalRow key={pa.id} pa={pa} bom={bom}
                included={effIncl(pa)} quantity={effQty(pa)} rate={effRate(pa)}
                onToggle={() => toggleIncl(pa.id)}
                onQtyChange={v => setQtyPA(pa.id, v)}
                onRateChange={v => setRatePA(pa.id, v)}
              />
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  // ── Phase subtotal bar ──────────────────────────────────────────────────────
  const PhaseSubtotal = ({ phase }) => {
    const mat  = matPhaseTotal(phase)
    const pkg  = pkgPhaseTotal(phase)
    const prov = provPhaseTotal(phase)
    const total = mat + pkg + prov
    if (total === 0) return null
    return (
      <div className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 mt-1">
        <div className="text-xs text-gray-400 space-x-2">
          {mat > 0  && <span>{fmtD(mat)} materials</span>}
          {pkg > 0  && <span>{fmt(pkg)} pkg</span>}
          {prov > 0 && <span>{fmt(prov)} prov. sums</span>}
        </div>
        <div className="text-base font-semibold text-gray-900 tabular-nums">{fmt(total)}</div>
      </div>
    )
  }

  // Groups by phase for rendering
  const groupsForPhase = phase => PACKAGE_GROUPS.filter(g => g.phase === phase)

  return (
    <div className="flex-1 overflow-auto p-6">

      {provError && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
          ⚠ {provError}
        </div>
      )}

      {/* Grand total banner */}
      <div className="bg-gray-900 rounded-xl px-6 py-5 mb-3 flex items-center justify-between">
        <div>
          <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">Total Estimate — Internal Cost</div>
          <div className="flex items-baseline gap-3">
            <div className="text-3xl font-semibold text-white tabular-nums">{fmt(grandLow)}</div>
            <div className="text-gray-500 text-sm">–</div>
            <div className="text-2xl font-semibold text-gray-300 tabular-nums">{fmt(grandHigh)}</div>
          </div>
          <div className="text-xs text-gray-500 mt-1">Low – High range based on selected packages</div>
        </div>
        <div className="text-right text-xs text-gray-500 max-w-[200px] leading-relaxed">
          Optional package costs are provisional allowances only. Final price depends on specification, installation and client choices.
        </div>
      </div>

      {/* Markup / selling price bar */}
      {(() => {
        const midCost = (grandLow + grandHigh) / 2
        const sp = computeSellingPrice(midCost, settings)
        return (
          <div className="bg-gray-800 rounded-xl px-6 py-4 mb-8 border border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Selling Price Calculation</div>
              <button type="button" onClick={openSettings} title="Edit markup settings"
                className="p-1.5 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-gray-700 transition-colors">
                <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                  <path fillRule="evenodd" d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.31 1.55a6.003 6.003 0 011.527.88l1.48-.56a1 1 0 011.21.433l1.18 2.044a1 1 0 01-.25 1.298l-1.24.93a6.07 6.07 0 010 1.762l1.24.93a1 1 0 01.25 1.298l-1.18 2.044a1 1 0 01-1.21.434l-1.48-.56a6.003 6.003 0 01-1.527.88l-.31 1.55A1 1 0 0111.18 19H8.82a1 1 0 01-.98-.804l-.31-1.55a6.003 6.003 0 01-1.527-.88l-1.48.56a1 1 0 01-1.21-.433L2.13 13.849a1 1 0 01.25-1.298l1.24-.93a6.07 6.07 0 010-1.762l-1.24-.93a1 1 0 01-.25-1.298L3.31 5.587a1 1 0 011.21-.434l1.48.56a6.003 6.003 0 011.527-.88l.31-1.55zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
            {settings && sp ? (
              <div className="grid grid-cols-2 gap-x-8 gap-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-400">Internal cost (mid)</span>
                  <span className="text-gray-200 tabular-nums font-medium">{fmt(Math.round(midCost))}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Markup ({settings.default_markup_percent}%)</span>
                  <span className="text-gray-200 tabular-nums font-medium">+ {fmt(Math.round(sp.markupAmt))}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Selling price ex VAT</span>
                  <span className="text-gray-200 tabular-nums font-medium">{fmt(Math.round(sp.exVat))}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">VAT ({settings.vat_rate_percent}%)</span>
                  <span className="text-gray-200 tabular-nums font-medium">+ {fmt(Math.round(sp.vatAmt))}</span>
                </div>
                <div className="flex justify-between border-t border-gray-600 pt-1.5 mt-0.5">
                  <span className="text-gray-300 font-semibold">Selling price inc VAT</span>
                  <span className="text-white tabular-nums font-semibold">{fmt(Math.round(sp.incVat))}</span>
                </div>
                {settings.round_to_nearest > 0 && (
                  <div className="flex justify-between border-t border-gray-600 pt-1.5 mt-0.5">
                    <span className="text-amber-400 font-semibold">Rounded (to €{settings.round_to_nearest})</span>
                    <span className="text-amber-400 tabular-nums font-bold text-sm">{fmt(sp.rounded)}</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-xs text-gray-500 italic">Loading settings…</div>
            )}
          </div>
        )
      })()}

      {/* Settings modal */}
      {settingsOpen && settingsDraft && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setSettingsOpen(false)}>
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-80" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm font-semibold text-gray-900">Pricing Settings</div>
              <button onClick={() => setSettingsOpen(false)} className="text-gray-400 hover:text-gray-600">
                <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
              </button>
            </div>
            <div className="space-y-4">
              <label className="block">
                <span className="text-xs font-medium text-gray-600">Markup %</span>
                <input type="number" min="0" max="500" step="0.5" value={settingsDraft.default_markup_percent}
                  onChange={e => setSettingsDraft(d => ({ ...d, default_markup_percent: parseFloat(e.target.value) || 0 }))}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-gray-500" />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-gray-600">VAT Rate %</span>
                <input type="number" min="0" max="100" step="0.5" value={settingsDraft.vat_rate_percent}
                  onChange={e => setSettingsDraft(d => ({ ...d, vat_rate_percent: parseFloat(e.target.value) || 0 }))}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-gray-500" />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-gray-600">Round to nearest (€)</span>
                <input type="number" min="0" step="50" value={settingsDraft.round_to_nearest}
                  onChange={e => setSettingsDraft(d => ({ ...d, round_to_nearest: parseInt(e.target.value) || 0 }))}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-gray-500" />
                <span className="text-[10px] text-gray-400">Set to 0 to disable rounding</span>
              </label>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setSettingsOpen(false)}
                className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
              <button onClick={saveSettings} disabled={settingsSaving}
                className="flex-1 bg-gray-900 text-white rounded-lg px-3 py-2 text-sm font-medium hover:bg-gray-700 disabled:opacity-50">
                {settingsSaving ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Phase 1: Base Envelope ────────────────────────────────── */}
      {Section({ id: 'base_envelope', title: 'Base Envelope / Weatherproof Shell',
        subtitle: 'Insulated shell, cladding, roof finish, openings', children: (<>
          {MatTable({ phase: 'base_envelope' })}
          {groupsForPhase('base_envelope').map(g => PkgGroupSection({ group: g }))}
          {ProvTable({ phase: 'base_envelope' })}
          {PhaseSubtotal({ phase: 'base_envelope' })}
        </>)
      })}

      {/* ── Phase 2: Interior Finishes ────────────────────────────── */}
      {Section({ id: 'interior_finish', title: 'Interior Finishes — Optional',
        subtitle: 'Flooring, paint, trims and internal finish packages', children: (<>
          {groupsForPhase('interior_finish').map(g => PkgGroupSection({ group: g }))}
          {ProvTable({ phase: 'interior_finish' })}
          <div className="text-[10px] text-gray-400 italic px-1">
            Furniture and sanitaryware are client discretion items and are not included in the base pod unless selected.
          </div>
          {PhaseSubtotal({ phase: 'interior_finish' })}
        </>)
      })}

      {/* ── Phase 3: Services / Comfort ───────────────────────────── */}
      {Section({ id: 'services_comfort', title: 'Heating + Ventilation — Optional', children: (<>
          {groupsForPhase('services_comfort').map(g => PkgGroupSection({ group: g }))}
          {PhaseSubtotal({ phase: 'services_comfort' })}
        </>)
      })}

      {/* ── Phase 4: Groundworks ──────────────────────────────────── */}
      {Section({ id: 'groundworks_slab', title: 'Concrete / Groundworks — Extra', children: (<>
          {groupsForPhase('groundworks_slab').map(g => PkgGroupSection({ group: g }))}
          {MatTable({ phase: 'groundworks_slab' })}
          <div className="text-[10px] text-gray-400 italic px-1">
            Concrete and groundworks are separate extras unless specifically selected. Ground-bearing slab to be reviewed by appointed structural engineer.
          </div>
          {PhaseSubtotal({ phase: 'groundworks_slab' })}
        </>)
      })}

      {/* ── Phase 5: Optional Add-Ons ─────────────────────────────── */}
      {Section({ id: 'optional_addons', title: 'Optional Add-Ons', children: (<>
          {groupsForPhase('optional_addons').map(g => PkgGroupSection({ group: g }))}
          {ProvTable({ phase: 'optional_addons' })}
          {PhaseSubtotal({ phase: 'optional_addons' })}
        </>)
      })}

      {/* ── Finishes & Furniture (from catalogue selections) ──────── */}
      {(finishLines.length > 0 || finishLoading) && (() => {
        // Group lines by cost_group
        const groups = {}
        for (const l of finishLines) {
          const g = l.cost_group || 'Other'
          if (!groups[g]) groups[g] = []
          groups[g].push(l)
        }
        const subtotal = finishTotal ?? 0
        return (
          <div className="mb-8">
            <button type="button" onClick={() => toggleDetail('finishes_catalogue')}
              className="w-full flex items-center justify-between mb-3 text-left group">
              <div>
                <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Finishes &amp; Furniture — Catalogue Selections</div>
                <div className="text-xs text-gray-500 mt-0.5">Items selected in the Finishes tab</div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-gray-900 tabular-nums">{fmt(subtotal)}</span>
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"
                  className={`w-3.5 h-3.5 text-gray-400 transition-transform ${detail.finishes_catalogue ? 'rotate-180' : ''}`}>
                  <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            </button>
            {detail.finishes_catalogue && (
              <div className="space-y-2">
                {finishLoading ? (
                  <div className="text-xs text-gray-400 px-1 py-2">Loading finish costs…</div>
                ) : Object.entries(groups).map(([groupName, lines]) => (
                  <FinishCostGroup key={groupName} groupName={groupName} lines={lines} />
                ))}
                {subtotal > 0 && (
                  <div className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg px-4 py-3">
                    <div className="text-xs text-gray-400">
                      {finishLines.filter(l => l.included !== false).length} item{finishLines.filter(l => l.included !== false).length !== 1 ? 's' : ''} selected
                      {finishLines.some(l => l.line_cost == null && l.included !== false) && (
                        <span className="ml-2 text-amber-500">· some items have no price</span>
                      )}
                    </div>
                    <div className="text-base font-semibold text-gray-900 tabular-nums">{fmt(subtotal)}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })()}

      {/* Exclusions */}
      <div className="border-t border-gray-200 pt-4 mt-2">
        <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Exclusions</div>
        <ul className="text-xs text-gray-400 space-y-1 list-disc list-inside">
          <li>Labour / installation (unless groundworks installed allowance selected)</li>
          <li>MEP — electrical distribution, plumbing, heating</li>
          <li>Delivery and crane / lifting</li>
          <li>Contractor margin and preliminaries</li>
          <li>Design fees, permits, structural engineering</li>
          <li>MVHR (available as premium ventilation option above)</li>
        </ul>
      </div>
    </div>
  )
}
