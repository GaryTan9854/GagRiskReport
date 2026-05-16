import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api'
import { RiskReport } from '../../types'
import PLSummary from './PLSummary'
import FuturesPositions from './FuturesPositions'
import FXPositions from './FXPositions'
import StatementPanel from './StatementPanel'
import DateNavBar from './DateNavBar'

function latestTradingDay() {
  const d = new Date()
  // If Saturday(6) go back 1, if Sunday(0) go back 2
  const dow = d.getDay()
  if (dow === 6) d.setDate(d.getDate() - 1)
  else if (dow === 0) d.setDate(d.getDate() - 2)
  return d.toISOString().slice(0, 10)
}

export default function RiskReportPage() {
  const [date, setDate] = useState(latestTradingDay())
  const [report, setReport] = useState<RiskReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
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

  const saveSnapshot = async () => {
    setSaving(true)
    try {
      await api.saveSnapshot(date)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
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
          onClick={saveSnapshot}
          disabled={saving || hasOverrides}
          className="bg-brand-accent text-brand-bg text-sm font-semibold px-3 py-1.5 rounded hover:bg-sky-400 disabled:opacity-40 transition-colors"
        >
          {saved ? '✓ Saved' : saving ? 'Saving…' : 'Save Snapshot'}
        </button>
      </div>

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
              vixCash={report.vix_cash}
              vixAccumPl={report.vix_accum_pl}
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
        </div>
      )}
    </div>
  )
}
