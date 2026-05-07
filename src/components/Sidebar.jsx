import { UserButton } from '@clerk/clerk-react'

function Icon({ id }) {
  const defs = {
    dashboard: (
      <>
        <rect x="2" y="2" width="5.5" height="5.5" rx="0.5" />
        <rect x="8.5" y="2" width="5.5" height="5.5" rx="0.5" />
        <rect x="2" y="8.5" width="5.5" height="5.5" rx="0.5" />
        <rect x="8.5" y="8.5" width="5.5" height="5.5" rx="0.5" />
      </>
    ),
    designer: (
      <>
        <path d="M4 13h8M8 3v10" strokeLinecap="round" />
        <path d="M5 3h6" strokeLinecap="round" />
      </>
    ),
    build_ups: (
      <>
        <rect x="2" y="3" width="12" height="2.5" rx="0.5" />
        <rect x="2" y="6.75" width="12" height="2.5" rx="0.5" />
        <rect x="2" y="10.5" width="12" height="2.5" rx="0.5" />
      </>
    ),
    orders: (
      <>
        <rect x="2.5" y="1.5" width="11" height="13" rx="1" />
        <path d="M5 5.5h6M5 8h6M5 10.5h4" strokeLinecap="round" />
      </>
    ),
    production: (
      <>
        <circle cx="8" cy="8" r="2.5" />
        <path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.5 3.5l1.1 1.1M11.4 11.4l1.1 1.1M12.5 3.5l-1.1 1.1M4.6 11.4l-1.1 1.1" strokeLinecap="round" />
      </>
    ),
    inventory: (
      <>
        <path d="M8 1.5L14 4.75v6.5L8 14.5 2 11.25V4.75L8 1.5z" />
        <path d="M8 1.5V14.5M2 4.75l6 3.25 6-3.25" strokeLinecap="round" />
      </>
    ),
    schedule: (
      <>
        <rect x="1.5" y="3" width="13" height="12" rx="1.5" />
        <path d="M5 1.5v3M11 1.5v3M1.5 7h13" strokeLinecap="round" />
      </>
    ),
    finish_catalogue: (
      <>
        <circle cx="5" cy="8" r="2.5" />
        <circle cx="11" cy="5" r="2" />
        <circle cx="11" cy="11" r="2" />
        <path d="M7.5 8h1.5M9 5h.5M9 11h.5" strokeLinecap="round" />
      </>
    ),
  }
  return (
    <svg
      viewBox="0 0 16 16"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.25"
      strokeLinejoin="round"
    >
      {defs[id] ?? null}
    </svg>
  )
}

const nav = [
  { id: 'dashboard',        label: 'Dashboard' },
  { id: 'designer',         label: 'Pod Designer' },
  { id: 'build_ups',        label: 'Build-Ups' },
  { id: 'materials',        label: 'Materials' },
  { id: 'finish_catalogue', label: 'Finishes' },
  { id: 'orders',           label: 'Orders' },
  { id: 'production',       label: 'Production' },
  { id: 'inventory',        label: 'Inventory' },
  { id: 'schedule',         label: 'Schedule' },
]

export default function Sidebar({ page, setPage }) {
  return (
    <aside className="w-56 bg-[#1a1a1a] border-r border-[#272727] flex flex-col shrink-0">
      <div className="px-5 py-5 border-b border-[#272727]">
        <div className="text-[10px] font-medium text-gray-500 tracking-widest uppercase">Top-R Solutions</div>
        <div className="text-[15px] font-semibold text-white mt-0.5 tracking-tight">Pod Manufacture</div>
      </div>
      <nav className="flex-1 px-2 py-3 space-y-0.5">
        {nav.map(item => (
          <button
            key={item.id}
            onClick={() => setPage(item.id)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded text-[13px] font-medium transition-colors ${
              page === item.id
                ? 'bg-white/10 text-white'
                : 'text-gray-500 hover:text-gray-200 hover:bg-white/5'
            }`}
          >
            <Icon id={item.id} />
            {item.label}
          </button>
        ))}
      </nav>
      <div className="px-4 py-4 border-t border-[#272727] flex items-center gap-3">
        <UserButton appearance={{ elements: { avatarBox: 'w-7 h-7' } }} />
        <span className="text-[11px] text-gray-600">v1.0</span>
      </div>
    </aside>
  )
}
