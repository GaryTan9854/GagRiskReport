import { RiskReport } from '../../types'

function fmt(n: number | undefined | null): string {
  if (n == null) return '—'
  const abs = Math.abs(n)
  const s = abs.toLocaleString('en-AU', { maximumFractionDigits: 0 })
  return n < 0 ? `($${s})` : `$${s}`
}

function fmtUsd(n: number | undefined | null): string {
  if (n == null) return '—'
  const abs = Math.abs(n)
  const s = abs.toLocaleString('en-AU', { maximumFractionDigits: 0 })
  return n < 0 ? `(US$${s})` : `US$${s}`
}

function fmtM(n: number): string {
  return `[${(n / 1_000_000).toFixed(1)}M]`
}

interface Props { report: RiskReport }

export default function StatementPanel({ report }: Props) {
  const { delta, nlv, funding, original_nlv, current_nlv, statement } = report

  return (
    <div className="flex flex-col gap-3">
      {/* Portfolio positions panel */}
      <div className="bg-brand-card border border-brand-border rounded-lg overflow-hidden">
        <table className="risk-table">
          <thead>
            <tr>
              <th className="text-left underline">Positions</th>
              <th>Futures {fmtM(funding.futures)}</th>
              <th>IBKR {fmtM(funding.ibkr)}</th>
              <th>FX {fmtM(funding.fx)}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="muted text-xs">Delta $</td>
              <td className={delta.futures < 0 ? 'neg' : 'pos'}>{fmt(delta.futures)}</td>
              <td className="muted">{fmt(delta.ibkr) === '$0' ? '$0' : fmt(delta.ibkr)}</td>
              <td className={delta.fx < 0 ? 'neg' : 'pos'}>{fmt(delta.fx)}</td>
            </tr>
            <tr><td colSpan={4} className="p-0"><div className="border-t border-brand-border" /></td></tr>
            <tr>
              <td className="muted text-xs">NLV</td>
              <td className="text-white">{fmt(nlv.futures)}</td>
              <td className="text-white">{fmt(nlv.ibkr)}</td>
              <td className="text-white">{fmt(nlv.fx)}</td>
            </tr>
            <tr><td colSpan={4} className="p-0"><div className="border-t border-brand-border" /></td></tr>
            <tr>
              <td className="muted text-xs">Original NLV</td>
              <td colSpan={3} className="text-white font-semibold">{fmt(original_nlv)}</td>
            </tr>
            <tr>
              <td className="muted text-xs">Current NLV</td>
              <td colSpan={3} className={current_nlv < original_nlv ? 'neg font-semibold' : 'pos font-semibold'}>{fmt(current_nlv)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Macquarie statement panel — only shown when PDF was imported */}
      {statement && (
        <div className="bg-brand-card border border-brand-border rounded-lg overflow-hidden">
          <table className="risk-table">
            <thead>
              <tr>
                <th className="text-left underline" colSpan={2}>Macquarie Stmt</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="muted text-xs">NLV (AUD)</td>
                <td className="text-white font-semibold">{fmt(statement.nlv_aud)}</td>
              </tr>
              <tr><td colSpan={2} className="p-0"><div className="border-t border-brand-border" /></td></tr>
              <tr>
                <td className="muted text-xs">Cash AUD</td>
                <td className="text-white">{fmt(statement.cash_aud)}</td>
              </tr>
              <tr>
                <td className="muted text-xs">Cash USD</td>
                <td className="text-white">{fmtUsd(statement.cash_usd)}</td>
              </tr>
              <tr><td colSpan={2} className="p-0"><div className="border-t border-brand-border" /></td></tr>
              <tr>
                <td className="muted text-xs">Var Margin (USD)</td>
                <td className={
                  statement.variation_margin_usd == null ? 'muted' :
                  statement.variation_margin_usd < 0 ? 'neg' : 'pos'
                }>{fmtUsd(statement.variation_margin_usd)}</td>
              </tr>
              <tr>
                <td className="muted text-xs">Init Margin (USD)</td>
                <td className="text-white">{fmtUsd(statement.initial_margin_usd)}</td>
              </tr>
              <tr><td colSpan={2} className="p-0"><div className="border-t border-brand-border" /></td></tr>
              <tr>
                <td className="muted text-xs">AUD/USD</td>
                <td className="text-white font-mono text-xs">{statement.audusd_rate?.toFixed(5) ?? '—'}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
