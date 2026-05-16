import { useState, useEffect } from 'react'
import { api } from '../../api'
import { Transaction, RollTrade } from '../../types'

const CURRENT_YEAR = new Date().getFullYear()
const YEARS = [0, CURRENT_YEAR, CURRENT_YEAR - 1, CURRENT_YEAR - 2].filter(Boolean)

function fmt(n: number | null): string {
  if (n == null) return '—'
  return n < 0 ? `($${Math.abs(n).toLocaleString()})` : `$${n.toLocaleString()}`
}

function RollTradeRow({ r }: { r: RollTrade }) {
  return (
    <tr>
      <td className="muted">{r.date}</td>
      <td className="text-white font-medium">{r.product}</td>
      <td className="muted">{r.close_month}</td>
      <td className="muted">{r.open_month}</td>
      <td className="muted text-right">{r.lots}</td>
      <td className="muted text-right">{r.avg_close_price.toLocaleString()}</td>
      <td className="muted text-right">{r.avg_open_price.toLocaleString()}</td>
      <td className={`text-right ${r.gross_pl_aud < 0 ? 'neg' : 'pos'}`}>{fmt(r.gross_pl_aud)}</td>
      <td className="neg text-right">{fmt(-r.total_commission)}</td>
      <td className={`text-right font-semibold ${r.net_pl_aud < 0 ? 'neg' : 'pos'}`}>{fmt(r.net_pl_aud)}</td>
    </tr>
  )
}

function TxRow({ t }: { t: Transaction }) {
  const isClose = t.is_close_pos === 1
  return (
    <tr>
      <td className="muted text-xs">{t.entry_date}</td>
      <td className="muted text-xs">{t.account}</td>
      <td className="text-white">{t.product_code || '—'}</td>
      <td className="muted text-xs">{t.contract_month || '—'}</td>
      <td className={`text-right ${t.position && t.position < 0 ? 'neg' : 'pos'}`}>
        {t.position != null ? t.position : '—'}
      </td>
      <td className="muted text-right">
        {t.entry_price != null ? t.entry_price.toLocaleString('en-AU', { minimumFractionDigits: 2 }) : '—'}
      </td>
      <td className="muted text-xs">{t.currency || '—'}</td>
      <td className={`text-xs px-2 py-0.5 rounded text-center ${isClose ? 'bg-orange-500/20 text-orange-400' : 'bg-blue-500/20 text-blue-400'}`}>
        {isClose ? 'Close' : t.transaction_type || 'Open'}
      </td>
      <td className={`text-right ${t.realized_pl_aud && t.realized_pl_aud < 0 ? 'neg' : 'pos'}`}>
        {fmt(t.realized_pl_aud)}
      </td>
      <td className="muted text-xs max-w-xs truncate">{t.notes || ''}</td>
    </tr>
  )
}

export default function TransactionsPage({ view }: { view: 'all' | 'rolls' }) {
  const [year, setYear] = useState(0)
  const [account, setAccount] = useState('')
  const [txns, setTxns] = useState<Transaction[]>([])
  const [rolls, setRolls] = useState<RollTrade[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    if (view === 'rolls') {
      api.getRollTrades(account || 'futures')
        .then(setRolls)
        .finally(() => setLoading(false))
    } else {
      api.getTransactions({ year: year || undefined, account: account || undefined, limit: 200 })
        .then(r => { setTxns(r.items); setTotal(r.total) })
        .finally(() => setLoading(false))
    }
  }, [view, year, account])

  return (
    <div className="space-y-3">
      {/* Filter bar */}
      <div className="flex items-center gap-3">
        <h2 className="text-white font-bold text-lg">
          {view === 'rolls' ? 'Roll Trades' : 'Transactions'}
        </h2>
        <select
          value={account}
          onChange={e => setAccount(e.target.value)}
          className="bg-brand-card border border-brand-border rounded px-2 py-1 text-sm text-white"
        >
          <option value="">All Accounts</option>
          <option value="futures">Futures</option>
          <option value="fx1">FX1</option>
          <option value="fx2">FX2</option>
          <option value="fx3">FX3</option>
          <option value="ibkr">IBKR</option>
        </select>
        {view === 'all' && (
          <select
            value={year}
            onChange={e => setYear(Number(e.target.value))}
            className="bg-brand-card border border-brand-border rounded px-2 py-1 text-sm text-white"
          >
            <option value={0}>All Years</option>
            {YEARS.filter(Boolean).map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        )}
        {view === 'all' && <span className="text-brand-muted text-sm">{total} records</span>}
        {loading && <span className="text-brand-muted text-sm">Loading…</span>}
      </div>

      <div className="bg-brand-card border border-brand-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          {view === 'rolls' ? (
            <table className="risk-table">
              <thead>
                <tr>
                  <th className="text-left">Date</th>
                  <th className="text-left">Product</th>
                  <th>Close Month</th>
                  <th>Open Month</th>
                  <th>Lots</th>
                  <th>Avg Close</th>
                  <th>Avg Open</th>
                  <th>Gross PL (AUD)</th>
                  <th>Commission</th>
                  <th>Net PL (AUD)</th>
                </tr>
              </thead>
              <tbody>
                {rolls.length === 0 && !loading && (
                  <tr><td colSpan={10} className="muted text-center py-6">No roll trades found</td></tr>
                )}
                {rolls.map((r, i) => <RollTradeRow key={i} r={r} />)}
              </tbody>
            </table>
          ) : (
            <table className="risk-table">
              <thead>
                <tr>
                  <th className="text-left">Date</th>
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
                {txns.length === 0 && !loading && (
                  <tr><td colSpan={10} className="muted text-center py-6">No transactions found</td></tr>
                )}
                {txns.map(t => <TxRow key={t.id} t={t} />)}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
