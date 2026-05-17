import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api'
import { RiskReport } from '../../types'
import PLSummary from './PLSummary'
import FuturesPositions from './FuturesPositions'
import FXPositions from './FXPositions'
import StatementPanel from './StatementPanel'
import DateNavBar from './DateNavBar'
import DayActivities from './DayActivities'

function latestTradingDay() {
  const now = new Date()
  let y = now.getFullYear(), mo = now.getMonth(), d = now.getDate()
  const dow = now.getDay()
  if (dow === 6) d -= 1
  else if (dow === 0) d -= 2
  const dt = new Date(Date.UTC(y, mo, d))
  return dt.toISOString().slice(0, 10)
}

export default function RiskReportPage() {
  const [date, setDate] = useState(latestTradingDay())
  const [report, setReport] = useState<RiskReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  // Price overrides for what-if (key = "CME ES|2603" or "AUDUSD")
  const [overrides, setOverrides] = useState<Record<string, number>>({})

  const load = useCallback(async (d: string, ovr: Record<string, number> = {}) => {
    setLoading(true)
    setError('')
    try {
      const r = Object.keys(ovr).length > 0
        ? await api.calcReport(d, ovr)
        : await api.getReport(d)
      setReport(r)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load report')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(date) }, [date, load])

  const handleDateChange = (d: string) => {
    setDate(d)
    setOverrides({})
  }

  const handlePriceEdit = (key: string, value: number) => {
    const next = { ...overrides, [key]: value }
    setOverrides(next)
    load(date, next)
  }

  const resetOverrides = () => {
    setOverrides({})
    load(date)
  }

  const [stmtLoading, setStmtLoading] = useState(false)
  const [stmtMsg, setStmtMsg]         = useState('')

  const showMsg = (msg: string) => {
    setStmtMsg(msg)
    setTimeout(() => setStmtMsg(''), 3000)
  }

  const openStmt = async () => {
    setStmtLoading(true)
    try {
      const token = sessionStorage.getItem('gag_token')
      const res = await fetch(`/api/import/stmt/${date}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        showMsg(`本日 (${date}) 沒有 Stmt`)
        return
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
    } catch {
      showMsg('無法開啟 Stmt，請稍後再試')
    } finally {
      setStmtLoading(false)
    }
  }

  const hasOverrides = Object.keys(overrides).length > 0
  const dateLabel = new Date(date + 'T00:00:00').toLocaleDateString('en-AU', {
    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric',
  })

  return (
    <div className="space-y-3">
      {/* Date navigation bar */}
      <DateNavBar selected={date} onChange={handleDateChange} />

      {/* Header bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-white font-bold">{dateLabel}</span>

        <div className="flex-1" />

        {hasOverrides && (
          <>
            <span className="text-yellow-400 text-xs font-semibold px-2 py-1 bg-yellow-400/10 rounded">
              ⚡ Trial mode – prices overridden
            </span>
            <button onClick={resetOverrides}
              className="text-brand-muted text-sm hover:text-white px-2 py-1 rounded hover:bg-white/5">
              Reset
            </button>
          </>
        )}

        <button
          onClick={openStmt}
          disabled={stmtLoading}
          className="bg-brand-card border border-brand-border text-brand-muted text-sm font-semibold px-3 py-1.5 rounded hover:text-white hover:border-brand-accent/60 disabled:opacity-40 transition-colors"
          title={`Open Macquarie statement for ${date}`}
        >
          {stmtLoading ? '…' : 'Stmt'}
        </button>
      </div>

      {/* No-stmt toast */}
      {stmtMsg && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50
                        bg-brand-card border border-brand-border text-brand-muted
                        text-sm px-5 py-3 rounded-lg shadow-lg
                        animate-fade-in">
          {stmtMsg}
        </div>
      )}

      {loading && <div className="text-brand-muted py-8 text-center">Loading report…</div>}
      {error   && <div className="text-brand-red py-4">{error}</div>}

      {report && !loading && (
        <div className="space-y-4">
          {/* Top summary: P&L + Positions side by side */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <div className="xl:col-span-2">
              <PLSummary report={report} />
            </div>
            <StatementPanel report={report} />
          </div>

          {/* Futures Positions */}
          {report.positions.futures.length > 0 && (
            <FuturesPositions
              rows={report.positions.futures}
              onPriceEdit={handlePriceEdit}
            />
          )}

          {/* FX Positions */}
          {report.positions.fx2.length > 0 && (
            <FXPositions title="FX2 Positions" rows={report.positions.fx2} onPriceEdit={handlePriceEdit} />
          )}
          {report.positions.fx3.length > 0 && (
            <FXPositions title="FX3 Positions" rows={report.positions.fx3} onPriceEdit={handlePriceEdit} />
          )}
          {report.positions.fx1.length > 0 && (
            <FXPositions title="FX1 Positions" rows={report.positions.fx1} onPriceEdit={handlePriceEdit} />
          )}

          {/* Day activities */}
          <DayActivities date={date} />
        </div>
      )}
    </div>
  )
}
