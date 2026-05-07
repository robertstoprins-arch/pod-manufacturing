/**
 * FinishSelector â€” customer-facing finish & furniture option cards.
 *
 * Props:
 *   specId        â€” pod spec id (null = disabled)
 *   selections    â€” { packages: [...], items: [...] }  current saved state
 *   onSelections  â€” callback(newSelections) fired after successful PATCH
 */
import { useState, useEffect, useCallback } from 'react'
import PackageSelector from './PackageSelector'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const CUSTOMER_SAFE = new Set([
  'approved_for_customer_pdf', 'own_photo', 'licensed_stock', 'generated_placeholder',
])

// â”€â”€ Category groups â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const GROUPS = [
  {
    id: 'exterior',
    label: 'Exterior Finish',
    categories: ['external_cladding'],
    mode: 'radio',
    description: 'Outer cladding finish for the pod',
  },
  {
    id: 'interior_paint',
    label: 'Interior Paint',
    categories: ['internal_paint'],
    mode: 'radio',
    description: 'Painted wall finish',
  },
  {
    id: 'interior_timber',
    label: 'Interior Timber Finish',
    categories: ['internal_timber_finish'],
    mode: 'multi',
    description: 'Exposed timber or panel finishes',
  },
  {
    id: 'flooring',
    label: 'Flooring',
    categories: ['flooring'],
    mode: 'radio',
    description: 'Floor finish throughout the pod',
  },
  {
    id: 'furniture',
    label: 'Furniture Package',
    categories: ['furniture_set'],
    mode: 'radio',
    description: 'Main furniture and storage package',
  },
  {
    id: 'sanitaryware',
    label: 'Bathroom',
    categories: ['sanitaryware', 'toilet', 'vanity_unit'],
    mode: 'radio',
    description: 'Sanitaryware, WC and vanity',
  },
  {
    id: 'kitchenette',
    label: 'Kitchenette',
    categories: ['kitchenette'],
    mode: 'multi',
    description: 'Kitchen and appliance options',
  },
  {
    id: 'lighting',
    label: 'Lighting',
    categories: ['lighting'],
    mode: 'multi',
    description: 'Lighting upgrades',
  },
  {
    id: 'cctv_data',
    label: 'CCTV / Data',
    categories: ['cctv_data'],
    mode: 'multi',
    description: 'CCTV and data infrastructure',
  },
  {
    id: 'solar',
    label: 'Solar / Battery',
    categories: ['solar_battery'],
    mode: 'multi',
    description: 'PV solar and battery storage options',
  },
]

// â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function priceLabel(item) {
  if (item.unit_cost == null) return null
  const sym = item.currency === 'EUR' ? 'â‚¬' : item.currency === 'GBP' ? 'Â£' : item.currency + ' '
  const qty = item.default_quantity ?? 1
  const q = item.quantity_rule
  if (q === 'per_m2_floor_area' || q === 'per_m2_wall_area' || q === 'per_m2_roof_area') {
    return `${sym}${item.unit_cost} / mÂ²`
  }
  if (q === 'package_fixed' || q === 'each') {
    return `${sym}${(item.unit_cost * qty).toLocaleString()}`
  }
  return `${sym}${item.unit_cost}${item.unit ? ` / ${item.unit}` : ''}`
}

function itemKey(item) {
  return `item:${item.id}`
}

// â”€â”€ Option card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function OptionCard({ item, selected, mode, onToggle }) {
  const safeImage = CUSTOMER_SAFE.has(item.image_approval_status) ? item.image_url : null
  const price = priceLabel(item)

  return (
    <button
      onClick={onToggle}
      className={`relative flex flex-col rounded-lg border text-left transition-all focus:outline-none ${
        selected
          ? 'border-blue-500 bg-blue-950/30 ring-1 ring-blue-500/40'
          : 'border-[#2a2a2a] bg-[#181818] hover:border-[#404040] hover:bg-[#1e1e1e]'
      }`}
    >
      {/* Image area */}
      <div className="w-full aspect-[4/3] rounded-t-lg bg-[#111] overflow-hidden flex items-center justify-center">
        {safeImage
          ? <img src={safeImage} alt={item.image_alt_text || ''} className="object-cover w-full h-full" />
          : (
            <svg className="w-8 h-8 text-[#333]" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.2">
              <rect x="3" y="3" width="26" height="26" rx="3" />
              <circle cx="11" cy="11" r="3" />
              <path d="M3 22l8-7 5 5 4-4 9 8" strokeLinejoin="round" />
            </svg>
          )
        }
      </div>

      {/* Content */}
      <div className="p-3 flex-1 flex flex-col gap-1">
        <div className="flex items-start justify-between gap-2">
          <div className="text-xs font-semibold text-gray-100 leading-tight">
            {item.customer_name}
          </div>
          {item.included_by_default && !selected && (
            <span className="shrink-0 text-[9px] font-semibold uppercase tracking-wide text-emerald-400 bg-emerald-900/30 border border-emerald-800/40 rounded px-1.5 py-0.5">
              Included
            </span>
          )}
          {selected && (
            <span className="shrink-0 text-[9px] font-semibold uppercase tracking-wide text-blue-300 bg-blue-900/30 border border-blue-700/40 rounded px-1.5 py-0.5">
              {mode === 'radio' ? 'Selected' : 'Added'}
            </span>
          )}
        </div>

        {item.customer_description && (
          <p className="text-[11px] text-gray-500 leading-relaxed line-clamp-2">
            {item.customer_description}
          </p>
        )}

        <div className="mt-auto pt-2 flex items-center justify-between">
          {price
            ? <span className="text-xs font-medium text-gray-300">{price}</span>
            : <span className="text-xs text-gray-600">Price on enquiry</span>
          }
          {item.lead_time_note && (
            <span className="text-[10px] text-gray-600">{item.lead_time_note}</span>
          )}
        </div>
      </div>

      {/* Selected checkmark overlay */}
      {selected && (
        <div className="absolute top-2 right-2 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center shadow">
          <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M2 6l3 3 5-5" />
          </svg>
        </div>
      )}
    </button>
  )
}

// â”€â”€ Group section â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function GroupSection({ group, items, selectedKeys, onToggle }) {
  const [expanded, setExpanded] = useState(true)
  const selectedCount = items.filter(i => selectedKeys.has(itemKey(i))).length

  if (items.length === 0) return null

  return (
    <div className="mb-6">
      {/* Group header */}
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center justify-between mb-3 group"
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-gray-200">{group.label}</span>
          <span className="text-[10px] text-gray-600">{group.mode === 'radio' ? 'Choose one' : 'Choose any'}</span>
          {selectedCount > 0 && (
            <span className="text-[10px] font-semibold text-blue-400 bg-blue-900/20 border border-blue-800/30 rounded-full px-2 py-0.5">
              {selectedCount} selected
            </span>
          )}
        </div>
        <svg
          className={`w-4 h-4 text-gray-600 transition-transform ${expanded ? '' : '-rotate-90'}`}
          viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"
        >
          <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {expanded && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {items.map(item => (
            <OptionCard
              key={item.id}
              item={item}
              mode={group.mode}
              selected={selectedKeys.has(itemKey(item))}
              onToggle={() => onToggle(group, item)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// â”€â”€ Main component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export default function FinishSelector({ specId, selections, onSelections }) {
  const [catalogue, setCatalogue] = useState([])
  const [loading, setLoading]     = useState(true)
  const [saving, setSaving]       = useState(false)
  const [saveError, setSaveError] = useState(null)
  const [subTab, setSubTab]       = useState('packages')

  // selectedKeys = Set of "item:<id>" strings
  const [selectedKeys, setSelectedKeys] = useState(() => new Set())

  // Hydrate selectedKeys from saved selections prop
  useEffect(() => {
    if (!selections) {
      setSelectedKeys(new Set())
      return
    }
    const keys = new Set()
    for (const sel of selections.items ?? []) {
      if (sel.included !== false) keys.add(`item:${sel.item_id}`)
    }
    setSelectedKeys(keys)
  }, [selections])

  useEffect(() => {
    fetch(`${API}/finish-catalogue/customer`)
      .then(r => r.json())
      .then(data => setCatalogue(Array.isArray(data) ? data : []))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const toggle = useCallback(async (group, item) => {
    if (!specId) return

    const key = itemKey(item)
    let nextKeys

    if (group.mode === 'radio') {
      // Deselect all items in this group's categories, then select this one
      const groupItemIds = new Set(
        catalogue
          .filter(c => group.categories.includes(c.category))
          .map(c => `item:${c.id}`)
      )
      nextKeys = new Set([...selectedKeys].filter(k => !groupItemIds.has(k)))
      if (!selectedKeys.has(key)) {
        nextKeys.add(key)
      }
    } else {
      nextKeys = new Set(selectedKeys)
      if (nextKeys.has(key)) {
        nextKeys.delete(key)
      } else {
        nextKeys.add(key)
      }
    }

    setSelectedKeys(nextKeys)
    setSaving(true)
    setSaveError(null)

    try {
      const items = [...nextKeys]
        .filter(k => k.startsWith('item:'))
        .map(k => ({ item_id: parseInt(k.slice(5)), quantity: 1.0, included: true }))

      // Preserve existing package selections when adjusting individual items
      const payload = { packages: selections?.packages ?? [], items }
      const res = await fetch(`${API}/pod-specs/${specId}/finishes`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const saved = await res.json()
      onSelections?.(saved.selected_finishes)
    } catch (e) {
      setSaveError(e.message)
      // Revert optimistic update
      setSelectedKeys(selectedKeys)
    } finally {
      setSaving(false)
    }
  }, [specId, selectedKeys, catalogue, onSelections])

  if (!specId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center px-8 py-16">
        <svg className="w-10 h-10 text-gray-700 mb-4" viewBox="0 0 40 40" fill="none" stroke="currentColor" strokeWidth="1.2">
          <circle cx="20" cy="20" r="16" />
          <path d="M14 20h12M20 14v12" strokeLinecap="round" />
        </svg>
        <div className="text-gray-500 text-sm font-medium">Save the pod spec first</div>
        <div className="text-gray-600 text-xs mt-1">Finish selections are stored against a saved spec</div>
      </div>
    )
  }

  // Bucket catalogue items into groups (used for items sub-tab)
  const itemsByGroup = {}
  for (const group of GROUPS) {
    itemsByGroup[group.id] = catalogue.filter(item => group.categories.includes(item.category))
  }

  const totalSelected = selectedKeys.size
  const packageCount  = (selections?.packages ?? []).length

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#111]">
      {/* Sub-tab bar */}
      <div className="shrink-0 flex items-center gap-1 px-4 py-0 border-b border-[#222] bg-[#141414]">
        <SubTabBtn
          active={subTab === 'packages'}
          onClick={() => setSubTab('packages')}
          badge={packageCount > 0 ? packageCount : null}
        >
          Packages
        </SubTabBtn>
        <SubTabBtn
          active={subTab === 'items'}
          onClick={() => setSubTab('items')}
          badge={totalSelected > 0 ? totalSelected : null}
        >
          Individual Options
        </SubTabBtn>

        {/* Status indicators */}
        <div className="ml-auto flex items-center gap-2 pr-2">
          {saving && <span className="text-[11px] text-gray-500">Savingâ€¦</span>}
          {saveError && <span className="text-[11px] text-red-400">{saveError}</span>}
        </div>
      </div>

      {/* Packages sub-tab */}
      {subTab === 'packages' && (
        <PackageSelector
          specId={specId}
          selections={selections}
          onSelections={onSelections}
        />
      )}

      {/* Individual items sub-tab */}
      {subTab === 'items' && (
        <>
          {loading ? (
            <div className="flex-1 flex items-center justify-center text-gray-600 text-sm">
              Loading optionsâ€¦
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto px-6 py-5">
              {GROUPS.map(group => (
                <GroupSection
                  key={group.id}
                  group={group}
                  items={itemsByGroup[group.id] ?? []}
                  selectedKeys={selectedKeys}
                  onToggle={toggle}
                />
              ))}
              {catalogue.length === 0 && (
                <div className="text-center py-16 text-gray-600 text-sm">
                  No catalogue items found. Seed the catalogue from the Finishes admin page.
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function SubTabBtn({ active, onClick, badge, children }) {
  return (
    <button
      onClick={onClick}
      className={`relative flex items-center gap-1.5 px-4 py-3 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
        active
          ? 'border-blue-500 text-blue-300'
          : 'border-transparent text-gray-500 hover:text-gray-300'
      }`}
    >
      {children}
      {badge != null && (
        <span className={`text-[9px] font-semibold rounded-full px-1.5 py-0.5 ${
          active ? 'bg-blue-900/40 text-blue-300' : 'bg-[#2a2a2a] text-gray-500'
        }`}>
          {badge}
        </span>
      )}
    </button>
  )
}

