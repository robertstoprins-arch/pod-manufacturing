import { useState, useEffect } from 'react'
import { apiFetch } from '../api/client'

// ── Package group definitions ─────────────────────────────────────────────────
// provisional_allowance: the one client-facing value shown.
// low / high: kept internally for estimating — never shown in client-facing UI.
// link fields: placeholder for future supplier / reference links.

export const PACKAGE_GROUPS = [
  {
    id: 'roof_finish', label: 'Roof Finish', type: 'bool', phase: 'base_envelope',
    options: [
      {
        code: 'roof_epdm_standard', name: 'EPDM Roof Finish',
        provisional_allowance: 700, low: 700, high: 700,
        notes: 'EPDM membrane, adhesive, trims and outlet allowance.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
    ],
  },
  {
    id: 'heating', label: 'Heating', type: 'radio', phase: 'services_comfort',
    options: [
      {
        code: 'electric_radiators_base', name: 'Electric Radiators — Base',
        provisional_allowance: 450, low: 250, high: 600,
        notes: 'Slim wall-mounted electric radiator allowance.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
      {
        code: 'electric_radiators_smart', name: 'Smart Electric Radiators',
        provisional_allowance: 1050, low: 700, high: 1400,
        notes: 'Smart controls / WiFi radiator allowance.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
      {
        code: 'air_to_air_heat_pump', name: 'Air-to-Air Heat Pump Upgrade',
        provisional_allowance: 2250, low: 1500, high: 3000,
        notes: 'Heating and cooling upgrade allowance.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
    ],
  },
  {
    id: 'ventilation', label: 'Ventilation', type: 'multi', phase: 'services_comfort',
    options: [
      {
        code: 'trickle_vents_allowance', name: 'Trickle Vents',
        provisional_allowance: 140, low: 80, high: 200,
        notes: 'Background ventilation allowance via window trickle vents.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
      {
        code: 'bathroom_extract', name: 'Bathroom Extract Fan',
        provisional_allowance: 120, low: 120, high: 300,
        notes: 'Required where bathroom / shower room is selected.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
      {
        code: 'kitchen_extract', name: 'Kitchen Extract Provision',
        provisional_allowance: 400, low: 200, high: 600,
        notes: 'Cooker hood or wall extract provision.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
      {
        code: 'mvhr_premium', name: 'MVHR Premium Option',
        provisional_allowance: 2250, low: 1500, high: 3000,
        notes: 'Premium ventilation option only. Not included in base specification.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
    ],
  },
  {
    id: 'cctv_data', label: 'CCTV / Data', type: 'multi', phase: 'optional_addons',
    options: [
      {
        code: 'cctv_cat6_prewire', name: 'CAT6 Prewire',
        provisional_allowance: 575, low: 350, high: 800,
        notes: 'CAT6 home-runs to external camera positions and data/comms location.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
      {
        code: 'basic_4_camera_ip', name: 'Basic 4-Camera IP CCTV Package',
        provisional_allowance: 1400, low: 800, high: 2000,
        notes: 'Provisional sum for 4 cameras installed at client\'s discretion. Camera positions, brand, NVR/storage and final specification to be confirmed.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
    ],
  },
  {
    id: 'pv_ready', label: 'PV-Ready Provision', type: 'bool', phase: 'optional_addons',
    options: [
      {
        code: 'pv_ready_roof', name: 'PV-Ready Roof Provision',
        provisional_allowance: 425, low: 250, high: 600,
        notes: 'Spare conduit and marked fixing/ballast zones. PV installation not included.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
    ],
  },
  {
    id: 'finishes', label: 'Interior Finishes', type: 'radio', phase: 'interior_finish',
    options: [
      {
        code: 'budget_finishes', name: 'Budget Internal Finishes',
        provisional_allowance: 3250, low: 2500, high: 4000,
        notes: 'Basic flooring, paint, skirting/trim allowance.',
        includes: [
          'Laminate or vinyl floor finish allowance',
          'Basic floor underlay',
          'Standard skirting boards',
          'Basic architraves',
          'Paint / primer material allowance',
          'Basic decorating material allowance',
          'Standard internal door set allowance, if selected in layout',
          'Basic internal and external light fitting allowances where selected',
        ],
        excludes: [
          'Loose furniture',
          'Kitchenette',
          'Sanitaryware',
          'Specialist wall finishes',
          'Tiling',
          'Upgraded lighting design',
          'Client-selected premium products',
        ],
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
      {
        code: 'standard_finishes', name: 'Standard Internal Finishes',
        provisional_allowance: 5750, low: 4500, high: 7000,
        notes: 'Improved flooring, decorating, trims and internal finish allowance.',
        includes: [
          'Improved laminate, vinyl or engineered-effect floor finish allowance',
          'Floor underlay, trims and thresholds',
          'Standard skirting boards',
          'Architraves',
          'Paint / primer material allowance',
          'Decorating material allowance',
          'Internal door set allowance, if selected in layout',
          'Internal and external light fitting allowances where selected',
          'Upgraded trims / finish allowance compared with budget option',
        ],
        excludes: [
          'Loose furniture',
          'Kitchenette',
          'Sanitaryware',
          'Specialist joinery',
          'Tiling',
          'Premium decorative finishes',
          'Client-selected premium products',
        ],
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
    ],
  },
  {
    id: 'furniture', label: 'Furniture / Client Discretion', type: 'qty', phase: 'optional_addons',
    options: [
      {
        code: 'kitchenette', name: 'Kitchenette Allowance',
        provisional_allowance: 600, low: 600, high: 600,
        notes: 'Client discretion item. Included only if selected.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
      {
        code: 'single_bed', name: 'Single Bed Package',
        provisional_allowance: 270, low: 270, high: 270,
        notes: 'Frame and mattress allowance. Included only if selected.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
      {
        code: 'double_bed', name: 'Double Bed Package',
        provisional_allowance: 370, low: 370, high: 370,
        notes: 'Frame and mattress allowance. Included only if selected.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
      {
        code: 'office_desk', name: 'Office Desk + Chair',
        provisional_allowance: 370, low: 370, high: 370,
        notes: 'Client discretion office furniture allowance. Included only if selected.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
      {
        code: 'vanity_unit', name: 'Vanity Unit Allowance',
        provisional_allowance: 150, low: 150, high: 150,
        notes: 'Budget vanity allowance. Client-selected sanitaryware may cost more.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
    ],
  },
  {
    id: 'groundworks', label: 'Base Preparation / Foundations', type: 'radio', phase: 'groundworks_slab',
    options: [
      {
        code: 'screw_pile_foundation', name: 'Screw Pile Foundation Provision',
        provisional_allowance: 3500, low: 2500, high: 5000,
        notes: 'Provisional allowance for screw pile foundation option. Final design, pile quantity, depth and specification to be confirmed.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
      {
        code: 'pad_foundation', name: 'Pad Foundation Provision',
        provisional_allowance: 2500, low: 1500, high: 4000,
        notes: 'Provisional allowance for pad foundation option. Final pad sizes, reinforcement and bearing requirements to be confirmed.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
      {
        code: 'ground_bearing_slab', name: 'Ground-Bearing Slab / Concrete Base Provision',
        provisional_allowance: 3500, low: 2000, high: 5000,
        notes: 'Provisional allowance for ground-bearing concrete base option. Excavation, sub-base, formwork, reinforcement and concrete scope to be confirmed.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
      {
        code: 'support_frame_base', name: 'Support Frame Base Provision',
        provisional_allowance: 2800, low: 1800, high: 4500,
        notes: 'Provisional allowance for raised support frame or alternative base support strategy where suitable.',
        reference_url: null, datasheet_url: null, supplier_url: null, notes_url: null,
      },
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
  framing_zone_insulation: 'base_envelope',
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

const fmt  = n => n == null ? '—' : `EUR ${Math.round(n).toLocaleString('en')}`
const fmtD = n => `EUR ${n.toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

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
        <span className="text-[10px] text-gray-400 mr-0.5">EUR</span>
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

// ── FinishCostGroup ───────────────────────────────────────────────────────────

function FinishCostGroup({ groupName, lines }) {
  const [open, setOpen] = useState(true)
  const total = lines.filter(l => l.line_cost != null && l.included !== false)
    .reduce((s, l) => s + l.line_cost, 0)

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden mb-3">
      <button type="button" onClick={() => setOpen(o => !o)}
        className="w-full px-3 py-2 flex items-center justify-between border-b border-gray-100 text-left">
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
    const markupAmt = Math.round(cost * s.default_markup_percent / 100 * 100) / 100
    const exVat     = Math.round((cost + markupAmt) * 100) / 100
    const vatAmt    = Math.round(exVat * s.vat_rate_percent / 100 * 100) / 100
    const incVat    = Math.round((exVat + vatAmt) * 100) / 100
    const rtn       = s.round_to_nearest > 0
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

  const finishSelectionsKey = specId
    ? `${specId}:${JSON.stringify(finishSelections ?? null)}`
    : null

  useEffect(() => {
    if (!specId) { setFinishLines([]); setFinishTotal(0); return }
    setFinishLoading(true)
    apiFetch(`/pod-specs/${specId}/finish-cost`)
      .then(data => {
        setFinishLines(data.lines ?? [])
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

  const setRadio    = (gid, code) => onPackages(p => ({ ...p, [gid]: p[gid] === code ? null : code }))
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

  // provisional_allowance takes priority; fall back to midpoint of low/high
  const pkgProvisional = code => {
    const opt = PKG_BY_CODE[code]
    if (!opt) return null
    if (opt.provisional_allowance != null) return opt.provisional_allowance
    const lo = opt.low; const hi = opt.high
    return (lo != null && hi != null) ? Math.round((lo + hi) / 2) : (lo ?? hi)
  }

  // ── Phase totals ────────────────────────────────────────────────────────────

  // Exclude structure (concrete slab) from client-facing material totals
  const matPhaseTotal = phase =>
    bomLines
      .filter(l => linePhase(l) === phase && l.role !== 'structure' && l.line_cost != null)
      .reduce((s, l) => s + l.line_cost, 0)

  // Include concrete in internal cost (for selling price calc) but not displayed
  const matPhaseTotalInternal = phase =>
    bomLines
      .filter(l => linePhase(l) === phase && l.line_cost != null)
      .reduce((s, l) => s + l.line_cost, 0)

  const pkgPhaseTotal = phase => {
    let total = 0
    for (const g of PACKAGE_GROUPS) {
      if (g.phase !== phase) continue
      for (const o of g.options) {
        if (!isActive(g.id, o.code)) continue
        const qty = g.type === 'qty' ? (packages.furniture?.[o.code] ?? 1) : 1
        const t = pkgProvisional(o.code)
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

  // Single grand total using provisional allowances (internal cost, incl concrete)
  const internalMatTotal = PHASES.reduce((s, p) => s + matPhaseTotalInternal(p), 0)
  const provAllTotal = allowances.reduce((s, a) => s + effCost(a), 0)
  const pkgTotal = PHASES.reduce((s, p) => s + pkgPhaseTotal(p), 0)
  const grandTotal = Math.round(internalMatTotal + provAllTotal + pkgTotal + (finishTotal ?? 0))

  const toggleDetail = p => setDetail(d => ({ ...d, [p]: !d[p] }))

  // ── Section wrapper ─────────────────────────────────────────────────────────
  const Section = ({ id, title, subtitle, children }) => (
    <div className="mb-8">
      <button type="button" onClick={() => toggleDetail(id)}
        className="w-full flex items-center justify-between mb-4 text-left group">
        <div>
          <div className="text-sm font-bold text-gray-900">{title}</div>
          {subtitle && <div className="text-xs text-gray-400 font-normal mt-0.5">{subtitle}</div>}
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

  // ── BOM materials table (excludes concrete slab for groundworks) ─────────
  const MatTable = ({ phase }) => {
    const lines = bomLines.filter(l => linePhase(l) === phase && l.role !== 'structure')
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
              <tr key={i} className="border-b border-gray-100 last:border-b-0">
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

  // ── Package option card ─────────────────────────────────────────────────────
  const PkgGroupSection = ({ group }) => {
    const g = group
    const isRadio = g.type === 'radio'
    const isQty   = g.type === 'qty'
    const isBool  = g.type === 'bool'

    return (
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="px-4 py-2.5 border-b border-gray-100 flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-700">{g.label}</span>
          <span className="text-[10px] text-gray-400">
            {isRadio && 'choose one'}
            {isQty   && 'client discretion'}
            {g.type === 'multi' && 'select all that apply'}
          </span>
        </div>
        <div className="divide-y divide-gray-100">
          {g.options.map(opt => {
            const active   = isActive(g.id, opt.code)
            const qty      = isQty ? (packages.furniture?.[opt.code] ?? 0) : 1
            const prov     = pkgProvisional(opt.code)
            const lineCost = active ? (prov ?? 0) * qty : 0

            return (
              <div key={opt.code} className={`px-4 py-3 transition-colors ${active ? 'bg-gray-50' : ''}`}>
                <div className="flex items-start gap-3">
                  {/* Toggle */}
                  {isRadio && (
                    <button type="button" onClick={() => setRadio(g.id, opt.code)}
                      className={`mt-0.5 w-4 h-4 rounded-full border-2 shrink-0 transition-colors ${active ? 'border-gray-900 bg-gray-900' : 'border-gray-300'}`}
                    />
                  )}
                  {g.type === 'multi' && (
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
                    {/* Title + provisional allowance */}
                    <div className="flex items-baseline justify-between gap-2">
                      <span className={`text-sm font-medium leading-snug ${active ? 'text-gray-900' : 'text-gray-500'}`}>
                        {opt.name}
                        {isQty && (
                          <span className="ml-2 text-[10px] font-normal text-gray-400 bg-gray-100 rounded px-1.5 py-0.5">client discretion</span>
                        )}
                      </span>
                      <div className="shrink-0 text-right">
                        {active && lineCost > 0 ? (
                          <span className="text-sm font-semibold text-gray-900 tabular-nums">{fmt(lineCost)}</span>
                        ) : prov != null ? (
                          <span className="text-xs text-gray-400 tabular-nums">{fmt(prov)} provisional</span>
                        ) : null}
                      </div>
                    </div>

                    {/* Notes */}
                    {opt.notes && (
                      <div className="text-xs text-gray-400 mt-1 leading-relaxed">{opt.notes}</div>
                    )}

                    {/* Includes / excludes for finishes */}
                    {active && opt.includes && (
                      <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-0.5">
                        <div>
                          <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Includes</div>
                          {opt.includes.map((item, i) => (
                            <div key={i} className="text-[10px] text-gray-500 leading-relaxed flex gap-1">
                              <span className="text-gray-300 shrink-0">–</span>
                              <span>{item}</span>
                            </div>
                          ))}
                        </div>
                        {opt.excludes && (
                          <div>
                            <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Excludes</div>
                            {opt.excludes.map((item, i) => (
                              <div key={i} className="text-[10px] text-gray-400 leading-relaxed flex gap-1">
                                <span className="text-gray-300 shrink-0">–</span>
                                <span>{item}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Provisional allowance label when active */}
                    {active && prov != null && (
                      <div className="mt-1.5 text-[10px] text-gray-400">
                        provisional allowance · final specification and supplier selection to be confirmed
                      </div>
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
        <div className="px-3 py-2 border-b border-gray-100 flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-700">Provisional sums</span>
          <span className="text-[10px] text-gray-400">Tick to include · edit qty &amp; rate</span>
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

  // ── Phase subtotal ──────────────────────────────────────────────────────────
  const PhaseSubtotal = ({ phase }) => {
    const total = phaseTotal(phase)
    if (total === 0) return null
    return (
      <div className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 mt-1">
        <div className="text-xs text-gray-400">Subtotal</div>
        <div className="text-base font-semibold text-gray-900 tabular-nums">{fmt(total)}</div>
      </div>
    )
  }

  const groupsForPhase = phase => PACKAGE_GROUPS.filter(g => g.phase === phase)

  return (
    <div className="flex-1 overflow-auto p-6">

      {provError && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
          ⚠ {provError}
        </div>
      )}

      {/* Grand total banner — single provisional figure */}
      <div className="bg-gray-900 rounded-xl px-6 py-5 mb-3 flex items-center justify-between">
        <div>
          <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">Total Estimate — Internal Cost</div>
          <div className="text-3xl font-semibold text-white tabular-nums">{fmt(grandTotal)}</div>
          <div className="text-xs text-gray-500 mt-1">Based on selected packages · provisional allowances</div>
        </div>
        <div className="text-right text-xs text-gray-500 max-w-[220px] leading-relaxed">
          Optional package costs are provisional allowances only. Final price depends on specification and client choices.
        </div>
      </div>

      {/* Markup / selling price bar */}
      {(() => {
        const sp = computeSellingPrice(grandTotal, settings)
        return (
          <div className="bg-gray-800 rounded-xl px-6 py-4 mb-8 border border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Selling Price Calculation</div>
              <button type="button" onClick={openSettings} title="Edit markup settings"
                className="p-1.5 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-gray-700 transition-colors">
                <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                  <path fillRule="evenodd" d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.31 1.55a6.003 6.003 0 011.527.88l1.48-.56a1 1 0 011.21.433l1.18 2.044a1 1 0 01-.25 1.298l-1.24.93a6.07 6.07 0 010 1.762l1.24.93a1 1 0 01.25 1.298l-1.18 2.044a1 1 0 01-1.21.434l-1.48-.56a6.003 6.003 0 01-1.527-.88l-.31 1.55A1 1 0 0111.18 19H8.82a1 1 0 01-.98-.804l-.31-1.55a6.003 6.003 0 01-1.527-.88l-1.48.56a1 1 0 01-1.21-.433L2.13 13.849a1 1 0 01.25-1.298l1.24-.93a6.07 6.07 0 010-1.762l-1.24-.93a1 1 0 01-.25-1.298L3.31 5.587a1 1 0 011.21-.434l1.48.56a6.003 6.003 0 011.527-.88l.31-1.55zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
            {settings && sp ? (
              <div className="grid grid-cols-2 gap-x-8 gap-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-400">Internal cost</span>
                  <span className="text-gray-200 tabular-nums font-medium">{fmt(grandTotal)}</span>
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
                    <span className="text-amber-400 font-semibold">Rounded (to EUR {settings.round_to_nearest})</span>
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
                <span className="text-xs font-medium text-gray-600">Round to nearest (EUR)</span>
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

      {/* ── 1. Base Envelope ─────────────────────────────────────── */}
      <Section id="base_envelope"
        title="Base Envelope / Weatherproof Shell"
        subtitle="Insulated shell, cladding, roof finish and openings">
        <MatTable phase="base_envelope" />
        {groupsForPhase('base_envelope').map(g => <PkgGroupSection key={g.id} group={g} />)}
        <ProvTable phase="base_envelope" />
        <PhaseSubtotal phase="base_envelope" />
      </Section>

      {/* ── 2. Interior Finishes ─────────────────────────────────── */}
      <Section id="interior_finish"
        title="Interior Finishes — Optional"
        subtitle="Flooring, decorating, trims and internal finish packages">
        {groupsForPhase('interior_finish').map(g => <PkgGroupSection key={g.id} group={g} />)}
        <ProvTable phase="interior_finish" />
        <div className="text-xs text-gray-400 px-1 leading-relaxed">
          Furniture and sanitaryware are client discretion items and are not included in the base pod unless selected.
        </div>
        <PhaseSubtotal phase="interior_finish" />
      </Section>

      {/* ── 3. Heating + Ventilation ─────────────────────────────── */}
      <Section id="services_comfort"
        title="Heating + Ventilation — Optional"
        subtitle="Heating and ventilation provisional allowances">
        {groupsForPhase('services_comfort').map(g => <PkgGroupSection key={g.id} group={g} />)}
        <PhaseSubtotal phase="services_comfort" />
      </Section>

      {/* ── 4. Base Preparation / Foundations ───────────────────── */}
      <Section id="groundworks_slab"
        title="Base Preparation / Foundations — Extra"
        subtitle="Foundation and base preparation options">
        {groupsForPhase('groundworks_slab').map(g => <PkgGroupSection key={g.id} group={g} />)}
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 space-y-1">
          <div className="text-xs font-semibold text-amber-800">Engineer's disclaimer</div>
          <div className="text-xs text-amber-700 leading-relaxed">
            Foundation and base calculations to be completed by the client's appointed engineer.
          </div>
          <div className="text-xs text-amber-600 leading-relaxed">
            Different foundation options may be available, including screw piles, pad foundations, ground-bearing concrete base or other engineered support systems. Final suitability depends on site investigation, ground conditions, access and engineer design.
          </div>
        </div>
        <PhaseSubtotal phase="groundworks_slab" />
      </Section>

      {/* ── 5. Optional Add-Ons ──────────────────────────────────── */}
      <Section id="optional_addons"
        title="Optional Add-Ons"
        subtitle="CCTV / data, PV provision, furniture and client discretion items">
        {groupsForPhase('optional_addons').map(g => <PkgGroupSection key={g.id} group={g} />)}
        <div className="text-xs text-gray-400 px-1 leading-relaxed">
          PV system, inverter, battery, grid connection and certification are not included unless separately selected.
        </div>
        <ProvTable phase="optional_addons" />
        <PhaseSubtotal phase="optional_addons" />
      </Section>

      {/* ── Finishes catalogue selections ────────────────────────── */}
      {(finishLines.length > 0 || finishLoading) && (() => {
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
              className="w-full flex items-center justify-between mb-4 text-left group">
              <div>
                <div className="text-sm font-bold text-gray-900">Finishes &amp; Furniture — Catalogue Selections</div>
                <div className="text-xs text-gray-400 font-normal mt-0.5">Items selected in the Finishes tab</div>
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
      <div className="border-t border-gray-200 pt-5 mt-2">
        <div className="text-xs font-bold text-gray-700 mb-2">Exclusions</div>
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
