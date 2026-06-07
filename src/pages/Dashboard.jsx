import { useState, useEffect, useCallback } from 'react'
import { useApi } from '../api/useApi'

// ── Issue pill labels (blocker_code → human label) ────────────────────────────

const BLOCKER_LABELS = {
  QUOTE_PRICE_MISSING:           'Missing price',
  QUOTE_INPUT_INCOMPLETE:        'No dimensions',
  QUOTE_ESTIMATE_USED:           'Estimate ready',
  QUOTE_READY_TO_SEND:           'Ready to send',
  QUOTE_DOCUMENTS_NOT_GENERATED: 'No portal link',
  FOLLOW_UP_DUE:                 'Follow-up due',
  CLIENT_CHANGES_REQUESTED:      'Changes req.',
  DEPOSIT_NOT_PAID:              'Awaiting deposit',
  DEPOSIT_INVOICE_MISSING:       'No invoice config',
  BOM_NOT_GENERATED:             'No BOM',
  RFQ_NOT_SENT:                  'RFQ not sent',
  SUPPLIER_RESPONSE_PENDING:     'Awaiting response',
  SUPPLIER_AWARD_MISSING:        'Award missing',
  READY_FOR_PRODUCTION_REVIEW:   'Ready',
}

const SEV_PILL = {
  info:    'bg-blue-50 text-blue-700',
  warning: 'bg-amber-100 text-amber-700',
  error:   'bg-red-100 text-red-700',
  blocked: 'bg-red-100 text-red-700',
}

const STATUS_LABELS = {
  draft: 'Draft', sent: 'Sent', follow_up_due: 'Follow-Up',
  accepted: 'Accepted', lost: 'Lost', expired: 'Expired',
  converted: 'Converted', changes_requested: 'Changes Req.',
}

const STATUS_COLORS = {
  draft:             'bg-gray-100 text-gray-600',
  sent:              'bg-blue-50 text-blue-700',
  follow_up_due:     'bg-orange-50 text-orange-700',
  accepted:          'bg-green-50 text-green-700',
  lost:              'bg-red-50 text-red-600',
  expired:           'bg-gray-50 text-gray-400',
  converted:         'bg-purple-50 text-purple-700',
  changes_requested: 'bg-amber-50 text-amber-700',
}

const DOC_BADGE = {
  available:     { label: 'Available',     cls: 'text-green-600' },
  on_demand:     { label: 'On-demand',     cls: 'text-blue-600'  },
  not_generated: { label: 'Not generated', cls: 'text-amber-600' },
  failed:        { label: 'Failed',        cls: 'text-red-600'   },
  not_applicable:{ label: '—',             cls: 'text-gray-300'  },
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function DashboardPage({ setPage }) {
  const api = useApi()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const d = await api('/dashboard/summary')
      setData(d)
      setLastRefresh(new Date())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [api])

  useEffect(() => { load() }, [load])

  const goToQuotes = () => setPage?.('quotes')

  if (loading && !data) return (
    <div className="p-8 text-sm text-gray-400">Loading dashboard…</div>
  )
  if (error) return (
    <div className="p-8 text-sm text-red-600 bg-red-50 rounded-lg m-6">
      <strong>Dashboard error:</strong> {error}
    </div>
  )
  if (!data) return null

  const {
    summary_cards, action_required, recent_enquiries,
    pricing_health, bom_rfq_health, payment_status,
    document_status, agent_readable_state,
  } = data

  const ar = agent_readable_state || {}
  const systemOk = ar.system_status === 'healthy'

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Operational Dashboard</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Status:{' '}
            <span className={systemOk ? 'text-green-600 font-medium' : 'text-amber-600 font-medium'}>
              {ar.system_status ?? '—'}
            </span>
            {ar.open_action_count != null && ` · ${ar.open_action_count} action${ar.open_action_count !== 1 ? 's' : ''} open`}
            {lastRefresh && ` · Updated ${lastRefresh.toLocaleTimeString()}`}
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="text-xs text-gray-500 hover:text-gray-800 border border-gray-200 rounded-lg px-3 py-1.5 bg-white hover:bg-gray-50 disabled:opacity-50"
        >
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {/* ── Summary cards ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-3">
        {(summary_cards || []).map(card => (
          <SummaryCard key={card.key} card={card} />
        ))}
      </div>

      {/* ── Action Required ────────────────────────────────────────────────── */}
      {action_required?.length > 0 && (
        <Section
          title="Action Required"
          badge={action_required.length}
          badgeColor="bg-amber-100 text-amber-700"
        >
          <div className="divide-y divide-gray-100 -mx-4 -mb-4">
            {action_required.map(item => (
              <ActionItem key={item.id} item={item} onOpen={goToQuotes} />
            ))}
          </div>
        </Section>
      )}

      {action_required?.length === 0 && (
        <div className="flex items-center gap-3 bg-green-50 border border-green-200 rounded-xl px-4 py-3">
          <span className="text-green-600 text-lg">✓</span>
          <span className="text-sm text-green-700 font-medium">All clear — no actions required right now.</span>
        </div>
      )}

      {/* ── Recent Enquiries + Health ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Recent Enquiries — 2/3 width */}
        <div className="lg:col-span-2">
          <Section title="Recent Enquiries" badge={recent_enquiries?.length}>
            {recent_enquiries?.length === 0 && (
              <p className="text-xs text-gray-400">No enquiries yet.</p>
            )}
            <div className="space-y-1.5">
              {(recent_enquiries || []).map(e => (
                <EnquiryRow key={e.quote_id} enquiry={e} onOpen={goToQuotes} />
              ))}
            </div>
          </Section>
        </div>

        {/* Health side column — 1/3 width */}
        <div className="space-y-4">
          <HealthCard title="Pricing" items={[
            { label: 'Priced',         value: pricing_health?.complete,      color: 'text-green-600' },
            { label: 'Missing price',  value: pricing_health?.missing_price, color: pricing_health?.missing_price > 0 ? 'text-amber-600' : 'text-gray-400' },
            { label: 'No BOM',         value: pricing_health?.no_bom,        color: pricing_health?.no_bom > 0        ? 'text-amber-600' : 'text-gray-400' },
            { label: 'Has BOM',        value: pricing_health?.has_bom,       color: 'text-green-600' },
          ]} />

          <HealthCard title="RFQ / Supplier" items={[
            { label: 'RFQ not sent',        value: bom_rfq_health?.rfq_not_sent,              color: bom_rfq_health?.rfq_not_sent > 0              ? 'text-amber-600' : 'text-gray-400' },
            { label: 'Awaiting response',   value: bom_rfq_health?.rfq_awaiting_response,     color: 'text-blue-600'  },
            { label: 'Responses received',  value: bom_rfq_health?.supplier_responses_received, color: 'text-blue-600' },
            { label: 'Award missing',       value: bom_rfq_health?.supplier_award_missing,    color: bom_rfq_health?.supplier_award_missing > 0    ? 'text-amber-600' : 'text-gray-400' },
            { label: 'Awards complete',     value: bom_rfq_health?.supplier_awards_complete,  color: 'text-green-600' },
          ]} />

          <HealthCard title="Payments" items={[
            { label: 'Awaiting deposit',  value: payment_status?.awaiting_deposit,  color: payment_status?.awaiting_deposit > 0 ? 'text-amber-600' : 'text-gray-400' },
            { label: 'Deposit received',  value: payment_status?.deposit_received,  color: 'text-green-600' },
            { label: 'Paid in full',      value: payment_status?.paid_in_full,      color: 'text-green-700' },
            { label: 'Overdue',           value: payment_status?.overdue,           color: payment_status?.overdue > 0          ? 'text-red-600'   : 'text-gray-400' },
          ]} />
        </div>
      </div>

      {/* ── Document Status ────────────────────────────────────────────────── */}
      {document_status?.length > 0 && (
        <Section title="Document Status">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-[10px] text-gray-400 uppercase tracking-wide border-b border-gray-100">
                  <th className="pb-2 pr-4 font-semibold">Reference</th>
                  <th className="pb-2 pr-4 font-semibold">Client</th>
                  <th className="pb-2 pr-4 font-semibold">Status</th>
                  <th className="pb-2 pr-4 font-semibold">Deposit Invoice</th>
                  <th className="pb-2 pr-4 font-semibold">BOM</th>
                  <th className="pb-2 font-semibold">RFQ JSON</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {document_status.map(d => (
                  <tr
                    key={d.quote_id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={goToQuotes}
                  >
                    <td className="py-2 pr-4 font-medium text-gray-900">{d.reference}</td>
                    <td className="py-2 pr-4 text-gray-500">{d.client_name}</td>
                    <td className="py-2 pr-4"><StatusPill status={d.status} /></td>
                    <td className="py-2 pr-4"><DocBadge status={d.documents.deposit_invoice_pdf} /></td>
                    <td className="py-2 pr-4"><DocBadge status={d.documents.bom} /></td>
                    <td className="py-2"><DocBadge status={d.documents.rfq_json} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {/* ── Agent-readable state (developer/agent view) ─────────────────────── */}
      <details className="text-xs text-gray-400 select-none">
        <summary className="cursor-pointer hover:text-gray-600 font-medium py-1">
          Agent-readable state
        </summary>
        <pre className="mt-2 p-4 bg-gray-900 text-gray-200 rounded-xl text-[11px] overflow-auto leading-relaxed">
          {JSON.stringify(agent_readable_state, null, 2)}
        </pre>
      </details>

    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SummaryCard({ card }) {
  const hasAlert = card.count > 0 && card.severity !== 'info'
  return (
    <div className={`rounded-xl border p-3 ${hasAlert ? 'border-amber-200 bg-amber-50' : 'border-gray-200 bg-white'}`}>
      <div className={`text-2xl font-bold ${hasAlert ? 'text-amber-700' : 'text-gray-900'}`}>
        {card.count}
      </div>
      <div className="text-[10px] text-gray-400 mt-0.5 leading-tight">{card.label}</div>
    </div>
  )
}

function Section({ title, badge, badgeColor = 'bg-gray-100 text-gray-500', children }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-3">
        <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
        {badge != null && (
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${badgeColor}`}>{badge}</span>
        )}
      </div>
      {children}
    </div>
  )
}

function ActionItem({ item, onOpen }) {
  const pillCls = SEV_PILL[item.severity] || SEV_PILL.info
  const issueLabel = BLOCKER_LABELS[item.blocker_code] || item.title

  const meta = [item.client_email, item.pod_type, item.dimensions].filter(Boolean).join(' · ')
  const pricePart = item.price != null
    ? `${item.currency} ${Number(item.price).toLocaleString()}`
    : `${item.currency || '€'}—`

  const deliveryLabel = {
    supply_install: 'Supply & install',
    turnkey: 'Turnkey',
    supply_only: 'Supply only',
  }
  const leadTimePart = item.lead_time || '—'
  const deliveryPart = deliveryLabel[item.delivery] || item.delivery || '—'

  return (
    <div className="flex items-start justify-between gap-3 px-4 py-2.5 hover:bg-gray-50">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] font-semibold text-gray-900">{item.reference}</span>
          {item.client_name && item.client_name !== 'Unknown' && (
            <span className="text-[11px] text-gray-600">· {item.client_name}</span>
          )}
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${pillCls}`}>
            {issueLabel}
          </span>
        </div>
        {meta && <p className="text-[10px] text-gray-400 mt-0.5 leading-tight">{meta}</p>}
        <p className="text-[10px] text-gray-500 mt-0.5 leading-tight">
          <span className="font-semibold text-gray-700">{pricePart}</span>
          {' · '}Lead time: {leadTimePart}
          {' · '}Delivery: {deliveryPart}
          {item.recommended_action && (
            <> · Next: <span className="font-medium text-gray-700">{item.recommended_action}</span></>
          )}
        </p>
      </div>
      <button
        onClick={onOpen}
        className="flex-shrink-0 text-[10px] border border-gray-200 rounded px-2 py-1 bg-white hover:bg-gray-50 text-gray-500 whitespace-nowrap mt-0.5"
      >
        Open
      </button>
    </div>
  )
}

const POD_TYPE_LABELS = { office: 'Office Pod', garden: 'Garden Pod', custom: 'Custom' }

function EnquiryRow({ enquiry, onOpen }) {
  const podLabel = POD_TYPE_LABELS[enquiry.pod_type] || enquiry.pod_type
  const pricePart = enquiry.pricing_status === 'complete' && enquiry.total_inc_vat != null
    ? `${enquiry.currency} ${Number(enquiry.total_inc_vat).toLocaleString()}`
    : null

  const meta = [enquiry.client_email, podLabel, enquiry.dimensions].filter(Boolean).join(' · ')

  return (
    <div
      className="flex items-start justify-between gap-3 px-3 py-2 hover:bg-gray-50 cursor-pointer group"
      onClick={onOpen}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] font-semibold text-gray-900">{enquiry.reference}</span>
          {enquiry.client_name && enquiry.client_name !== 'Unknown' && (
            <span className="text-[11px] text-gray-600">· {enquiry.client_name}</span>
          )}
          <StatusPill status={enquiry.status} />
          {pricePart && <span className="text-[11px] font-semibold text-gray-700">{pricePart}</span>}
          {enquiry.pricing_status === 'missing' && (
            <span className="text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full font-medium">unpriced</span>
          )}
        </div>
        {meta && <p className="text-[10px] text-gray-400 mt-0.5 leading-tight">{meta}</p>}
        {enquiry.next_action && (
          <p className="text-[10px] text-gray-400 mt-0.5">Next: {enquiry.next_action}</p>
        )}
      </div>
      <span className="text-[10px] text-gray-300 flex-shrink-0 group-hover:text-gray-500 mt-0.5">
        {enquiry.created_at
          ? new Date(enquiry.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
          : ''}
      </span>
    </div>
  )
}

function HealthCard({ title, items }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-3">{title}</h3>
      <div className="space-y-2">
        {(items || []).map(item => (
          <div key={item.label} className="flex items-center justify-between">
            <span className="text-xs text-gray-500">{item.label}</span>
            <span className={`text-sm font-bold ${item.color}`}>{item.value ?? 0}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function StatusPill({ status }) {
  const cls = STATUS_COLORS[status] || 'bg-gray-100 text-gray-500'
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${cls}`}>
      {STATUS_LABELS[status] || status}
    </span>
  )
}

function DocBadge({ status }) {
  const c = DOC_BADGE[status] || { label: status || '—', cls: 'text-gray-400' }
  return <span className={`text-[10px] ${c.cls}`}>{c.label}</span>
}
