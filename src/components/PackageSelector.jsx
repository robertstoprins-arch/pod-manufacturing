/**
 * PackageSelector â€” preset finish package cards.
 *
 * Props:
 *   specId        â€” pod spec id (null = disabled)
 *   selections    â€” { packages: [{package_id, quantity}], items: [...] }
 *   onSelections  â€” callback(newSelections) fired after successful PATCH
 */
import { useState, useEffect, useCallback } from 'react'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const CUSTOMER_SAFE = new Set([
  'approved_for_customer_pdf', 'own_photo', 'licensed_stock', 'generated_placeholder',
])

// Which package categories are mutually exclusive (radio) vs. additive (multi)
const RADIO_CATEGORIES = new Set([
  'complete_interior', 'exterior_finish', 'bathroom', 'flooring',
])

const CATEGORY_LABELS = {
  complete_interior:  'Complete Interior Packages',
  exterior_finish:    'Exterior Finish',
  bathroom:           'Bathroom',
  flooring:           'Flooring',
  lighting:           'Lighting',
  kitchen:            'Kitchenette',
  furniture:          'Furniture',
  cctv_data:          'CCTV / Data',
  solar:              'Solar / Battery',
  services:           'Services',
  other:              'Other',
}

function categoryLabel(cat) {
  return CATEGORY_LABELS[cat] ?? cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function fmt(cat) {
  return cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

// â”€â”€ Item summary list inside a package card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function ItemSummary({ items, expanded }) {
  if (!expanded || !items?.length) return null
  return (
    <ul className="mt-2 space-y-0.5">
      {items.slice(0, 8).map(item => (
        <li key={item.id} className="flex items-center gap-1.5 text-[11px] text-gray-500">
          <span className="w-1 h-1 rounded-full bg-gray-600 shrink-0" />
          <span className="truncate">{item.customer_name || item.catalogue_name}</span>
          {!item.is_required && (
            <span className="ml-auto text-[9px] text-gray-700 shrink-0">optional</span>
          )}
        </li>
      ))}
      {items.length > 8 && (
        <li className="text-[11px] text-gray-600 pl-2.5">+ {items.length - 8} more items</li>
      )}
    </ul>
  )
}

// â”€â”€ Package price estimate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function packagePriceEstimate(pkg) {
  let total = 0
  let hasUnknown = false
  for (const item of pkg.items ?? []) {
    if (item.unit_cost == null) { hasUnknown = true; continue }
    const qty = item.quantity_override ?? item.quantity ?? 1
    total += item.unit_cost * qty
  }
  if (total === 0 && hasUnknown) return null
  const sym = 'â‚¬'
  const label = Math.round(total).toLocaleString()
  return hasUnknown ? `from ${sym}${label}` : `${sym}${label}`
}

// â”€â”€ Package card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function PackageCard({ pkg, selected, onToggle }) {
  const [showItems, setShowItems] = useState(false)
  const safeImage = CUSTOMER_SAFE.has(pkg.image_approval_status) ? pkg.image_url : null
  const price = packagePriceEstimate(pkg)
  const itemCount = pkg.items?.length ?? 0

  return (
    <div className={`rounded-lg border transition-all ${
      selected
        ? 'border-blue-500 bg-blue-950/25 ring-1 ring-blue-500/30'
        : 'border-[#2a2a2a] bg-[#181818]'
    }`}>
      {/* Image */}
      <div className="w-full aspect-[16/7] rounded-t-lg bg-[#111] overflow-hidden flex items-center justify-center">
        {safeImage
          ? <img src={safeImage} alt={pkg.customer_name || pkg.name || ''} className="object-cover w-full h-full" />
          : (
            <svg className="w-10 h-10 text-[#2a2a2a]" viewBox="0 0 40 40" fill="none" stroke="currentColor" strokeWidth="1.2">
              <rect x="4" y="4" width="32" height="32" rx="4" />
              <path d="M4 28l10-9 6 6 5-5 11 9" strokeLinejoin="round" />
              <circle cx="13" cy="13" r="3.5" />
            </svg>
          )
        }
      </div>

      {/* Body */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-3 mb-1">
          <div className="text-sm font-semibold text-gray-100 leading-tight">
            {pkg.customer_name || pkg.name}
          </div>
          {selected && (
            <div className="shrink-0 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center">
              <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M2 6l3 3 5-5" />
              </svg>
            </div>
          )}
        </div>

        {pkg.customer_description && (
          <p className="text-xs text-gray-500 leading-relaxed mb-3">{pkg.customer_description}</p>
        )}

        {/* What's included */}
        {itemCount > 0 && (
          <button
            onClick={() => setShowItems(v => !v)}
            className="flex items-center gap-1.5 text-[11px] text-gray-600 hover:text-gray-400 transition-colors mb-2"
          >
            <svg
              className={`w-3 h-3 transition-transform ${showItems ? '' : '-rotate-90'}`}
              viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5"
            >
              <path d="M2 4l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {showItems ? 'Hide' : 'Show'} {itemCount} included item{itemCount !== 1 ? 's' : ''}
          </button>
        )}
        <ItemSummary items={pkg.items} expanded={showItems} />

        {/* Footer: price + button */}
        <div className="mt-3 flex items-center justify-between gap-3">
          <div className="text-sm font-medium text-gray-300">
            {price ?? <span className="text-gray-600 text-xs">Price on enquiry</span>}
          </div>
          <button
            onClick={onToggle}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              selected
                ? 'bg-blue-900/40 border border-blue-700/50 text-blue-300 hover:bg-blue-900/60'
                : 'bg-white/5 border border-[#333] text-gray-300 hover:bg-white/10 hover:border-[#555]'
            }`}
          >
            {selected ? 'Deselect' : 'Select'}
          </button>
        </div>
      </div>
    </div>
  )
}

// â”€â”€ Category group â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function CategoryGroup({ category, packages, selectedPackageIds, onToggle }) {
  const isRadio = RADIO_CATEGORIES.has(category)
  const anySelected = packages.some(p => selectedPackageIds.has(p.id))

  return (
    <div className="mb-8">
      <div className="flex items-center gap-3 mb-4">
        <h3 className="text-sm font-semibold text-gray-200">{categoryLabel(category)}</h3>
        <span className="text-[10px] text-gray-600">{isRadio ? 'Choose one' : 'Choose any'}</span>
        {anySelected && (
          <span className="text-[10px] font-semibold text-blue-400 bg-blue-900/20 border border-blue-800/30 rounded-full px-2 py-0.5">
            Selected
          </span>
        )}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {packages.map(pkg => (
          <PackageCard
            key={pkg.id}
            pkg={pkg}
            selected={selectedPackageIds.has(pkg.id)}
            onToggle={() => onToggle(pkg, category, isRadio)}
          />
        ))}
      </div>
    </div>
  )
}

// â”€â”€ Main component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export default function PackageSelector({ specId, selections, onSelections }) {
  const [packages, setPackages]   = useState([])
  const [loading, setLoading]     = useState(true)
  const [saving, setSaving]       = useState(false)
  const [saveError, setSaveError] = useState(null)

  // Set of selected package ids
  const [selectedIds, setSelectedIds] = useState(() => new Set())

  // Hydrate from selections prop
  useEffect(() => {
    if (!selections) { setSelectedIds(new Set()); return }
    const ids = new Set((selections.packages ?? []).map(p => p.package_id))
    setSelectedIds(ids)
  }, [selections])

  useEffect(() => {
    fetch(`${API}/finish-packages/customer`)
      .then(r => r.json())
      .then(data => setPackages(Array.isArray(data) ? data : []))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const toggle = useCallback(async (pkg, category, isRadio) => {
    if (!specId) return

    let nextIds
    if (isRadio) {
      // Deselect all packages in same category, then select this one (unless it was already selected)
      const categoryIds = new Set(
        packages.filter(p => p.package_category === category).map(p => p.id)
      )
      nextIds = new Set([...selectedIds].filter(id => !categoryIds.has(id)))
      if (!selectedIds.has(pkg.id)) nextIds.add(pkg.id)
    } else {
      nextIds = new Set(selectedIds)
      nextIds.has(pkg.id) ? nextIds.delete(pkg.id) : nextIds.add(pkg.id)
    }

    // Compute which catalogue items are brought in by the selected packages
    const packagePayload = [...nextIds].map(id => ({ package_id: id, quantity: 1.0 }))

    // Merge package items into the items list (keep any existing manual item overrides)
    const existingItems = selections?.items ?? []
    // Item ids coming from selected packages
    const packageItemIds = new Set()
    for (const id of nextIds) {
      const p = packages.find(p => p.id === id)
      for (const item of p?.items ?? []) packageItemIds.add(item.finish_catalogue_item_id)
    }
    // Keep manual items (not brought in by any package) that were explicitly selected
    const manualItems = existingItems.filter(i => !packageItemIds.has(i.item_id))
    // Add all items from selected packages
    const packageItems = []
    for (const id of nextIds) {
      const p = packages.find(p => p.id === id)
      for (const pi of p?.items ?? []) {
        if (!packageItems.some(i => i.item_id === pi.finish_catalogue_item_id)) {
          packageItems.push({ item_id: pi.finish_catalogue_item_id, quantity: pi.effective_quantity, included: true })
        }
      }
    }
    const mergedItems = [...manualItems, ...packageItems]

    const payload = { packages: packagePayload, items: mergedItems }

    setSelectedIds(nextIds)
    setSaving(true)
    setSaveError(null)

    try {
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
      setSelectedIds(selectedIds) // revert
    } finally {
      setSaving(false)
    }
  }, [specId, selectedIds, packages, selections, onSelections])

  if (!specId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center px-8 py-16">
        <div className="text-gray-500 text-sm font-medium">Save the pod spec first</div>
        <div className="text-gray-600 text-xs mt-1">Package selections are stored against a saved spec</div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-600 text-sm">Loading packagesâ€¦</div>
    )
  }

  // Group packages by category, preserve sort_order
  const sorted = [...packages].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
  const byCategory = {}
  for (const pkg of sorted) {
    const cat = pkg.package_category ?? 'other'
    if (!byCategory[cat]) byCategory[cat] = []
    byCategory[cat].push(pkg)
  }

  const totalSelected = selectedIds.size

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#111]">
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-6 py-3 border-b border-[#222] bg-[#141414]">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-gray-200">Finish Packages</span>
          {totalSelected > 0 && (
            <span className="text-[11px] text-gray-400">
              {totalSelected} package{totalSelected !== 1 ? 's' : ''} selected
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {saving && <span className="text-[11px] text-gray-500">Savingâ€¦</span>}
          {saveError && <span className="text-[11px] text-red-400">{saveError}</span>}
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {packages.length === 0 ? (
          <div className="text-center py-16 text-gray-600 text-sm">
            No packages found. Add packages from the Finishes admin page.
          </div>
        ) : (
          Object.entries(byCategory).map(([cat, pkgs]) => (
            <CategoryGroup
              key={cat}
              category={cat}
              packages={pkgs}
              selectedPackageIds={selectedIds}
              onToggle={toggle}
            />
          ))
        )}
      </div>
    </div>
  )
}

