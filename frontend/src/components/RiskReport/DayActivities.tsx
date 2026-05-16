import { useEffect, useState } from 'react'
import { api } from '../../api'
import { Transaction } from '../../types'

interface RollGroup {
  product: string
  close_month: string
  open_month: string
  lots_signed: number
  avg_close_price: number
  avg_open_price: number
  pts: number
  pct: number
  gross_pl_usd: number
  gross_pl_aud: number
  total_commission: number
  net_pl_aud: number
}

function detectRolls(txns: Transaction[]): { rolls: RollGroup[]; others: Transaction[] } {
  const trades = txns.filter(t => t.transaction_type === 'trade')
  const nonTrades = txns.filter(t => t.transaction_type !== 'trade')

  // Group by product_code
  const byProduct = new Map<string, Transaction[]>()
  for (const t of trades) {
    const key = t.product_code || '?'
    if (!byProduct.has(key)) byProduct.set(key, [])
    byProduct.get(key)!.push(t)
  }

  const rolls: RollGroup[] = []
  const rollTxnIds = new Set<number>()

  byProduct.forEach((txns, product) => {
    const closes = txns.filter(t => t.is_close_pos === 1)
    const opens = txns.filter(t => t.is_close_pos !== 1)
    if (!closes.length || !opens.length) return

    const closeMonths = new Set(closes.map(t => t.contract_month))
    const openMonths = new Set(opens.map(t => t.contract_month))
    if (closeMonths.size !== 1 || openMonths.size !== 1) return
    if ([...closeMonths][0] === [...openMonths][0]) return  // same month = not a roll

    const totalCloseQty = closes.reduce((s, t) => s + Math.abs(t.position ?? 0), 0)
    const avgClose = closes.reduce((s, t) => s + (t.entry_price ?? 0) * Math.abs(t.position ?? 0), 0) / (totalCloseQty || 1)
    const totalOpenQty = opens.reduce((s, t) => s + Math.abs(t.position ?? 0), 0)
    const avgOpen = opens.reduce((s, t) => s + (t.entry_price ?? 0) * Math.abs(t.position ?? 0), 0) / (totalOpenQty || 1)

    const mult = closes[0].multiplier ?? 1
    const fxRate = closes[0].fx_rate_to_aud ?? 1
    const isShort = (closes[0].position ?? 0) > 0  // buying to close = was short
    const lots_signed = isShort ? -totalCloseQty : totalCloseQty

    const gross_pl_usd = isShort
      ? (avgOpen - avgClose) * totalCloseQty * mult
      : (avgClose - avgOpen) * totalCloseQty * mult
    const gross_pl_aud = gross_pl_usd * fxRate
    const total_commission = txns.reduce((s, t) => s + (t.total_commission ?? 0), 0)
    const pts = avgOpen - avgClose

    rolls.push({
      product,
      close_month: [...closeMonths][0] ?? '',
      open_month: [...openMonths][0] ?? '',
      lots_signed,
      avg_close_price: avgClose,
      avg_open_price: avgOpen,
      pts,
      pct: avgClose ? (pts / avgClose) * 100 : 0,
      gross_pl_usd,
      gross_pl_aud,
      total_commission,
      net_pl_aud: gross_pl_aud - total_commission,
    })

    txns.forEach(t => rollTxnIds.add(t.id))
  })

  const others = [...nonTrades, ...trades.filter(t => !rollTxnIds.has(t.id))]
  return { rolls, others }
}

function fmtAud(n: number) {
  return n < 0 ? `($${Math.abs(Math.round(n)).toLocaleString()})` : `$${Math.round(n).toLocaleString()}`
}
function fmtUsd(n: number) {
  return n < 0 ? `(US$${Math.abs(Math.round(n)).toLocaleString()})` : `US$${Math.round(n).toLocaleString()}`
}

export default function DayActivities({ date }: { date: string }) {
  const [txns, setTxns] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.getTransactions({ entry_date: date, limit: 100 })
      .then(r => setTxns(r.items))
      .finally(() => setLoading(false))
  }, [date])

  if (loading) return null
  if (!txns.length) return null

  const { rolls, others } = detectRolls(txns)

  return (
    <div className="space-y-3 mt-1">
      <h3 className="text-white font-semibold text-sm">Activities — {date}</h3>

      {/* Roll trades */}
      {rolls.length > 0 && (
        <div className="bg-brand-card border border-brand-border rounded-lg overflow-hidden">
          <div className="px-3 py-1.5 border-b border-brand-border">
            <span className="text-xs text-brand-muted font-semibold uppercase tracking-wider">Roll Trades</span>
          </div>
          <div className="overflow-x-auto">
            <table className="risk-table">
              <thead>
                <tr>
                  <th className="text-left">Product</th>
                  <th>Close Mth</th>
                  <th>Open Mth</th>
                  <th>Lots</th>
                  <th>Avg Close</th>
                  <th>Avg Open</th>
                  <th>Pts (%)</th>
                  <th>Gross PL (USD)</th>
                  <th>Gross PL (AUD)</th>
                  <th>Commission</th>
                  <th>Net PL (AUD)</th>
                </tr>
              </thead>
              <tbody>
                {rolls.map((r, i) => {
                  const sign = r.pts >= 0 ? '+' : ''
                  return (
                    <tr key={i}>
                      <td className="text-white font-medium">{r.product}</td>
                      <td className="muted">{r.close_month}</td>
                      <td className="muted">{r.open_month}</td>
                      <td className="muted text-right">{r.lots_signed}</td>
                      <td className="muted text-right">{r.avg_close_price.toLocaleString(undefined, { maximumFractionDigits: 4 })}</td>
                      <td className="muted text-right">{r.avg_open_price.toLocaleString(undefined, { maximumFractionDigits: 4 })}</td>
                      <td className={`text-right font-semibold ${r.pts >= 0 ? 'pos' : 'neg'}`}>
                        {sign}{r.pts.toFixed(3)} ({sign}{r.pct.toFixed(2)}%)
                      </td>
                      <td className={`text-right ${r.gross_pl_usd < 0 ? 'neg' : 'pos'}`}>{fmtUsd(r.gross_pl_usd)}</td>
                      <td className={`text-right ${r.gross_pl_aud < 0 ? 'neg' : 'pos'}`}>{fmtAud(r.gross_pl_aud)}</td>
                      <td className="neg text-right">{fmtAud(-r.total_commission)}</td>
                      <td className={`text-right font-semibold ${r.net_pl_aud < 0 ? 'neg' : 'pos'}`}>{fmtAud(r.net_pl_aud)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Other transactions */}
      {others.length > 0 && (
        <div className="bg-brand-card border border-brand-border rounded-lg overflow-hidden">
          <div className="px-3 py-1.5 border-b border-brand-border">
            <span className="text-xs text-brand-muted font-semibold uppercase tracking-wider">Transactions</span>
          </div>
          <div className="overflow-x-auto">
            <table className="risk-table">
              <thead>
                <tr>
                  <th className="text-left">Account</th>
                  <th className="text-left">Product</th>
                  <th>Contract</th>
                  <th>Qty</th>
                  <th>Price</th>
                  <th>Ccy</th>
                  <th>Type</th>
                  <th>Realized PL (AUD)</th>
                  <th className="text-left">Notes</th>
                </tr>
              </thead>
              <tbody>
                {others.map(t => {
                  const isClose = t.is_close_pos === 1
                  return (
                    <tr key={t.id}>
                      <td className="muted text-xs">{t.account}</td>
                      <td className="text-white">{t.product_code || '—'}</td>
                      <td className="muted">{t.contract_month || '—'}</td>
                      <td className={`text-right ${t.position && t.position < 0 ? 'neg' : 'pos'}`}>
                        {t.position ?? '—'}
                      </td>
                      <td className="muted text-right">
                        {t.entry_price != null ? t.entry_price.toLocaleString('en-AU', { minimumFractionDigits: 2 }) : '—'}
                      </td>
                      <td className="muted text-xs">{t.currency || '—'}</td>
                      <td>
                        <span className={`text-xs px-2 py-0.5 rounded ${isClose ? 'bg-orange-500/20 text-orange-400' : 'bg-blue-500/20 text-blue-400'}`}>
                          {isClose ? 'Close' : t.transaction_type || 'Open'}
                        </span>
                      </td>
                      <td className={`text-right ${t.realized_pl_aud && t.realized_pl_aud < 0 ? 'neg' : 'pos'}`}>
                        {t.realized_pl_aud != null ? fmtAud(t.realized_pl_aud) : '—'}
                      </td>
                      <td className="muted text-xs max-w-xs truncate">{t.notes || ''}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
