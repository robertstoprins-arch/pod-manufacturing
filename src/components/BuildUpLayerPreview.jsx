// BuildUpLayerPreview — horizontal stacked-bar preview of a build-up section.
// Props:
//   layers   Array of { name, thickness_mm, role }  (inside → outside)
//   compact  bool — show a smaller bar without legend (default false)

const ROLE_COLORS = {
  internal_finish: { bg: '#e2e8f0', text: '#334155' },
  service_void:    { bg: '#fef3c7', text: '#92400e' },
  vcl:             { bg: '#d8b4fe', text: '#581c87' },
  airtight_layer:  { bg: '#d8b4fe', text: '#581c87' },
  sheathing:       { bg: '#fdba74', text: '#7c2d12' },
  structure:       { bg: '#b45309', text: '#ffffff' },
  framing_zone:    { bg: '#f59e0b', text: '#1c1917' },
  insulation:      { bg: '#38bdf8', text: '#0c4a6e' },
  breather:        { bg: '#60a5fa', text: '#1e3a8a' },
  cavity:          { bg: '#86efac', text: '#14532d' },
  cladding:        { bg: '#a8a29e', text: '#1c1917' },
  external_finish: { bg: '#78716c', text: '#fafaf9' },
}
const FALLBACK = { bg: '#94a3b8', text: '#f1f5f9' }

function computeWidths(layers, maxPx, minPx) {
  const total = layers.reduce((s, l) => s + l.thickness_mm, 0)
  if (total === 0) return layers.map(() => maxPx / layers.length)
  const raw = layers.map(l => Math.max(minPx, (l.thickness_mm / total) * maxPx))
  const rawSum = raw.reduce((s, w) => s + w, 0)
  return raw.map(w => (w / rawSum) * maxPx)
}

export default function BuildUpLayerPreview({ layers = [], compact = false }) {
  const valid = layers.filter(l => Number(l.thickness_mm) > 0)
  if (valid.length === 0) return null

  const totalThickness = valid.reduce((s, l) => s + Number(l.thickness_mm), 0)
  const barH    = compact ? 28 : 40
  const maxPx   = compact ? 240 : 400
  const minPx   = 4
  const widths  = computeWidths(valid, maxPx, minPx)

  return (
    <div className="w-full">
      {/* Inside / Outside labels */}
      <div className="flex justify-between text-[10px] text-gray-400 mb-1 px-0.5">
        <span>Inside</span>
        <span>Outside</span>
      </div>

      {/* Stacked bar */}
      <div
        className="flex rounded overflow-hidden border border-gray-300"
        style={{ height: barH }}
      >
        {valid.map((layer, i) => {
          const color = ROLE_COLORS[layer.role] || FALLBACK
          const w     = widths[i]
          const showLabel = w >= 30
          return (
            <div
              key={i}
              title={`${layer.name}\n${layer.thickness_mm} mm`}
              style={{
                width: w,
                minWidth: minPx,
                backgroundColor: color.bg,
                color: color.text,
                flexShrink: 0,
              }}
              className="flex items-center justify-center overflow-hidden"
            >
              {showLabel && (
                <span
                  className="text-[9px] font-semibold leading-none px-0.5 truncate"
                  style={{ writingMode: w < 50 ? 'vertical-rl' : 'horizontal-tb' }}
                >
                  {layer.thickness_mm}
                </span>
              )}
            </div>
          )
        })}
      </div>

      {/* Total thickness */}
      <div className="text-xs text-gray-400 mt-1 text-right">
        Total: <span className="text-gray-900 font-semibold">{Math.round(totalThickness)} mm</span>
      </div>

      {/* Legend — full view only */}
      {!compact && (
        <div className="mt-2 space-y-0.5 max-h-36 overflow-y-auto">
          {valid.map((layer, i) => {
            const color = ROLE_COLORS[layer.role] || FALLBACK
            return (
              <div key={i} className="flex items-center gap-1.5 text-xs text-gray-600">
                <div
                  style={{ backgroundColor: color.bg }}
                  className="w-3 h-3 rounded-sm shrink-0 border border-gray-200"
                />
                <span className="flex-1 truncate" title={layer.name}>{layer.name}</span>
                <span className="text-gray-400 shrink-0 tabular-nums">{layer.thickness_mm} mm</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
