import { useEffect, useRef } from 'react'
import { api } from '../../api'
import { useState } from 'react'

function isoToday() {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function addDays(dateStr: string, n: number): string {
  const [y, mo, d] = dateStr.split('-').map(Number)
  const utc = new Date(Date.UTC(y, mo - 1, d + n))
  return utc.toISOString().slice(0, 10)
}

// All Mon-Fri trading days from 2026-01-02 up to today
function tradingDays(): string[] {
  const days: string[] = []
  let cur = '2026-01-02'
  const end = isoToday()
  while (cur <= end) {
    const dow = new Date(cur + 'T00:00:00').getDay()
    if (dow >= 1 && dow <= 5) days.push(cur)
    cur = addDays(cur, 1)
  }
  return days
}

interface Props {
  selected: string
  onChange: (date: string) => void
}

export default function DateNavBar({ selected, onChange }: Props) {
  const [snapshots, setSnapshots] = useState<Set<string>>(new Set())
  const scrollRef = useRef<HTMLDivElement>(null)
  const activeRef = useRef<HTMLButtonElement>(null)

  const days = tradingDays()

  useEffect(() => {
    api.listSnapshots(365).then(list => {
      setSnapshots(new Set(list.map((s: { report_date: string }) => s.report_date)))
    }).catch(() => {})
  }, [])

  // Scroll active date into view whenever it changes
  useEffect(() => {
    if (activeRef.current && scrollRef.current) {
      const container = scrollRef.current
      const el = activeRef.current
      const elLeft = el.offsetLeft
      const elRight = elLeft + el.offsetWidth
      const visLeft = container.scrollLeft
      const visRight = visLeft + container.offsetWidth
      if (elLeft < visLeft + 60 || elRight > visRight - 60) {
        el.scrollIntoView({ inline: 'center', block: 'nearest', behavior: 'smooth' })
      }
    }
  }, [selected])

  const prev = () => {
    const i = days.indexOf(selected)
    if (i > 0) onChange(days[i - 1])
  }

  const next = () => {
    const i = days.indexOf(selected)
    if (i < days.length - 1) onChange(days[i + 1])
  }

  // Group display: show month label when month changes
  const rendered: JSX.Element[] = []
  let lastMonth = ''

  days.forEach((d) => {
    const dt = new Date(d + 'T00:00:00')
    const month = dt.toLocaleDateString('en-AU', { month: 'short' })
    const dayNum = dt.getDate()
    const isActive = d === selected
    const hasSnap = snapshots.has(d)

    if (month !== lastMonth) {
      lastMonth = month
      rendered.push(
        <span key={`m-${d}`} className="flex-shrink-0 text-[10px] text-brand-muted font-semibold uppercase tracking-wider self-center px-1 first:pl-0">
          {month}
        </span>
      )
    }

    rendered.push(
      <button
        key={d}
        ref={isActive ? activeRef : undefined}
        onClick={() => onChange(d)}
        title={d}
        className={`flex-shrink-0 w-8 h-8 rounded text-xs font-semibold transition-colors
          ${isActive
            ? 'bg-brand-accent text-brand-bg'
            : hasSnap
              ? 'bg-brand-card text-white hover:bg-white/10 border border-brand-accent/40'
              : 'text-brand-muted hover:bg-white/5'
          }`}
      >
        {dayNum}
      </button>
    )
  })

  return (
    <div className="flex items-center gap-1 bg-brand-card border border-brand-border rounded-lg px-2 py-1.5">
      <button
        onClick={prev}
        disabled={days.indexOf(selected) <= 0}
        className="flex-shrink-0 text-brand-muted hover:text-white disabled:opacity-30 px-1 text-base leading-none"
      >
        ‹
      </button>

      <div ref={scrollRef} className="flex items-center gap-0.5 overflow-x-auto scrollbar-hide flex-1" style={{ scrollbarWidth: 'none' }}>
        {rendered}
      </div>

      <button
        onClick={next}
        disabled={days.indexOf(selected) >= days.length - 1}
        className="flex-shrink-0 text-brand-muted hover:text-white disabled:opacity-30 px-1 text-base leading-none"
      >
        ›
      </button>
    </div>
  )
}
