const stats = [
  { label: 'Active Builds', value: '7',   delta: '+2 this month' },
  { label: 'Completed',     value: '34',  delta: '12 this year' },
  { label: 'In Queue',      value: '5',   delta: '3 pending sign-off' },
  { label: 'On-Time Rate',  value: '91%', delta: '+3% vs last quarter' },
]

const recentActivity = [
  { id: 'POD-041', client: 'Harrington Homes', type: '2-Bed Pod',   stage: 'Fit-Out',       date: '2026-04-28', status: 'On Track' },
  { id: 'POD-040', client: 'Greenfield Devs',  type: '1-Bed Pod',   stage: 'QC Inspection', date: '2026-04-27', status: 'Attention' },
  { id: 'POD-039', client: 'Urban Nest Ltd',   type: 'Studio Pod',  stage: 'Delivered',     date: '2026-04-25', status: 'Complete' },
  { id: 'POD-038', client: 'Skyline Build Co', type: '3-Bed Pod',   stage: 'Framing',       date: '2026-04-24', status: 'On Track' },
  { id: 'POD-037', client: 'M&J Properties',   type: '2-Bed Pod',   stage: 'Delivered',     date: '2026-04-22', status: 'Complete' },
]

const statusStyle = {
  'On Track':  'bg-green-50 text-green-700 border border-green-200',
  'Attention': 'bg-amber-50 text-amber-700 border border-amber-200',
  'Complete':  'bg-gray-100 text-gray-500 border border-gray-200',
  'Delayed':   'bg-red-50 text-red-700 border border-red-200',
}

const stageProgress = [
  { stage: 'Foundation',       count: 1 },
  { stage: 'Framing',          count: 2 },
  { stage: 'Insulation / MEP', count: 1 },
  { stage: 'Fit-Out',          count: 2 },
  { stage: 'QC Inspection',    count: 1 },
]

export default function Dashboard() {
  return (
    <div className="p-8 space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">Live overview of pod manufacturing operations</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-4 gap-4">
        {stats.map(s => (
          <div key={s.label} className="bg-white border border-gray-200 rounded-lg p-5">
            <div className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">{s.label}</div>
            <div className="text-4xl font-semibold text-gray-900 mt-2 tabular-nums">{s.value}</div>
            <div className="text-xs text-gray-400 mt-1">{s.delta}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Recent orders table */}
        <div className="col-span-2 bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Recent Orders</h2>
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left pb-2.5 pr-4 text-[11px] font-medium text-gray-400 uppercase tracking-wider">Order</th>
                <th className="text-left pb-2.5 pr-4 text-[11px] font-medium text-gray-400 uppercase tracking-wider">Client</th>
                <th className="text-left pb-2.5 pr-4 text-[11px] font-medium text-gray-400 uppercase tracking-wider">Type</th>
                <th className="text-left pb-2.5 pr-4 text-[11px] font-medium text-gray-400 uppercase tracking-wider">Stage</th>
                <th className="text-left pb-2.5 text-[11px] font-medium text-gray-400 uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {recentActivity.map(row => (
                <tr key={row.id}>
                  <td className="py-2.5 pr-4 font-mono text-xs text-gray-600 font-medium">{row.id}</td>
                  <td className="py-2.5 pr-4 text-xs text-gray-700">{row.client}</td>
                  <td className="py-2.5 pr-4 text-xs text-gray-500">{row.type}</td>
                  <td className="py-2.5 pr-4 text-xs text-gray-500">{row.stage}</td>
                  <td className="py-2.5">
                    <span className={`text-xs px-2 py-0.5 rounded ${statusStyle[row.status]}`}>
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Production pipeline */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Production Pipeline</h2>
          <div className="space-y-4">
            {stageProgress.map(s => (
              <div key={s.stage}>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="text-gray-500">{s.stage}</span>
                  <span className="text-gray-700 font-medium tabular-nums">
                    {s.count} unit{s.count !== 1 ? 's' : ''}
                  </span>
                </div>
                <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gray-700 rounded-full transition-all"
                    style={{ width: `${(s.count / 7) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
