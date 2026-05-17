type Tab = 'report' | 'transactions' | 'roll-trades' | 'transfers' | 'import'

interface Props {
  tab: Tab
  onTab: (t: Tab) => void
  onLogout: () => void
}

const TABS: { id: Tab; label: string }[] = [
  { id: 'report',       label: 'Daily Report' },
  { id: 'transactions', label: 'Transactions' },
  { id: 'roll-trades',  label: 'Roll Trades' },
  { id: 'transfers',    label: 'Transfers' },
  { id: 'import',       label: 'Import PDF' },
]

export default function Navbar({ tab, onTab, onLogout }: Props) {
  return (
    <header className="sticky top-0 z-50 bg-brand-card border-b border-brand-border">
      <div className="max-w-[1400px] mx-auto flex items-center gap-4 px-4 py-2">
        {/* Logo */}
        <div className="flex items-center gap-2 mr-4">
          <img src="/assets/gag-icon.png?v=2" alt="GAG" className="w-7 h-7 object-contain" />
          <span className="font-bold text-white">
            <span className="text-brand-accent">GAG</span>
            <span className="text-brand-muted text-sm ml-1">Risk Report</span>
          </span>
        </div>

        {/* Nav tabs */}
        <nav className="flex gap-1">
          {TABS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => onTab(id)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                tab === id
                  ? 'bg-brand-accent text-brand-bg'
                  : 'text-brand-muted hover:text-white hover:bg-white/5'
              }`}
            >
              {label}
            </button>
          ))}
        </nav>

        <div className="flex-1" />

        {/* Logout */}
        <button
          onClick={onLogout}
          className="flex items-center gap-1.5 text-brand-muted hover:text-white text-sm px-3 py-1.5 rounded hover:bg-white/5 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Logout
        </button>
      </div>
    </header>
  )
}
