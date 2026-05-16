import { RiskReport } from '../../types'

function fmt(n: number | undefined | null, decimals = 0): string {
  if (n == null) return '—'
  const abs = Math.abs(n)
  const s = abs.toLocaleString('en-AU', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  return n < 0 ? `($${s})` : `$${s}`
}

function pctFmt(n: number | undefined | null): string {
  if (n == null) return '—'
  return `${n >= 0 ? '' : ''}${n.toFixed(2)}%`
}

function Cell({ v, bold }: { v: string; bold?: boolean }) {
  const neg = v.startsWith('(')
  const pctNeg = v.startsWith('-')
  const cls = neg || pctNeg ? 'neg' : v === '$0' || v === '—' ? 'muted' : 'pos'
  return <td className={`${cls} ${bold ? 'font-bold' : ''}`}>{v}</td>
}

interface Props { report: RiskReport }

export default function PLSummary({ report }: Props) {
  const { pl, pl_pct, pl_dollar, high_water_mark } = report
  const fx = pl.fx_combined

  const rows = [
    { label: 'Yesterday PL', futures: pl.futures.yesterday_pl, ib: pl.ib.yesterday_pl, fx: fx.yesterday_pl, fx2: pl.fx2.yesterday_pl, fx3: pl.fx3.yesterday_pl, total: pl.total.yesterday_pl },
    { label: 'Trade PL',     futures: pl.futures.trade_pl,     ib: pl.ib.trade_pl,     fx: fx.trade_pl,     fx2: pl.fx2.trade_pl,     fx3: pl.fx3.trade_pl,     total: pl.total.trade_pl },
    { label: 'Closing PL',   futures: pl.futures.closing_pl,   ib: pl.ib.closing_pl,   fx: fx.closing_pl,   fx2: pl.fx2.closing_pl,   fx3: pl.fx3.closing_pl,   total: pl.total.closing_pl },
    { label: 'Today PL',     futures: pl.futures.today_pl,     ib: pl.ib.today_pl,     fx: fx.today_pl,     fx2: pl.fx2.today_pl,     fx3: pl.fx3.today_pl,     total: pl.total.today_pl },
    { label: 'Total PL',     futures: pl.futures.total_pl,     ib: pl.ib.total_pl,     fx: fx.total_pl,     fx2: pl.fx2.total_pl,     fx3: pl.fx3.total_pl,     total: pl.total.total_pl, bold: true },
  ]

  return (
    <div className="bg-brand-card border border-brand-border rounded-lg overflow-hidden">
      <table className="risk-table">
        <thead>
          <tr>
            <th className="text-left underline">P&amp;L</th>
            <th>Futures</th>
            <th>IB</th>
            <th>FX</th>
            <th>FX2</th>
            <th>FX3</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.label}>
              <td className="muted text-xs">{r.label}</td>
              <Cell v={fmt(r.futures)} bold={r.bold} />
              <Cell v={fmt(r.ib)} bold={r.bold} />
              <Cell v={fmt(r.fx)} bold={r.bold} />
              <Cell v={fmt(r.fx2)} bold={r.bold} />
              <Cell v={fmt(r.fx3)} bold={r.bold} />
              <Cell v={fmt(r.total)} bold={r.bold} />
            </tr>
          ))}
          {/* PL% row */}
          <tr>
            <td className="muted text-xs">PL%</td>
            <Cell v={pctFmt(pl_pct.futures)} />
            <Cell v={pctFmt(pl_pct.ib)} />
            <Cell v="—" />
            <Cell v={pctFmt(pl_pct.fx2)} />
            <Cell v={pctFmt(pl_pct.fx3)} />
            <Cell v={pctFmt(pl_pct.total)} />
          </tr>
          {/* Divider */}
          <tr><td colSpan={7} className="p-0"><div className="border-t border-brand-border" /></td></tr>
          {/* PL$ combined */}
          <tr>
            <td className="muted text-xs">PL$</td>
            <td colSpan={2}><Cell v={fmt(pl_dollar.futures_ib)} /></td>
            <td />
            <Cell v={fmt(pl_dollar.fx2)} />
            <Cell v={fmt(pl_dollar.fx3)} />
            <td />
          </tr>
          <tr>
            <td className="muted text-xs">High Water Mark</td>
            <td colSpan={2} className="muted">{fmt(high_water_mark.futures_ib)}</td>
            <td />
            <td className="muted">{fmt(high_water_mark.fx2)}</td>
            <td className="muted">{fmt(high_water_mark.fx3)}</td>
            <td />
          </tr>
        </tbody>
      </table>
    </div>
  )
}
