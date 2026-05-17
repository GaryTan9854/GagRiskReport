import { useState } from 'react'
import { FuturesRow } from '../../types'

function fmt(n: number): string {
  const abs = Math.abs(n)
  const s = abs.toLocaleString('en-AU', { maximumFractionDigits: 0 })
  return n < 0 ? `($${s})` : `$${s}`
}

interface Props {
  rows: FuturesRow[]
  onPriceEdit: (key: string, value: number) => void
}

function EditablePrice({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(String(value))

  const commit = () => {
    const n = parseFloat(draft)
    if (!isNaN(n) && n !== value) onChange(n)
    setEditing(false)
  }

  if (editing) {
    return (
      <input
        className="price-input"
        value={draft}
        autoFocus
        onChange={e => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={e => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') setEditing(false) }}
      />
    )
  }

  return (
    <span
      className="price-editable text-brand-accent"
      onDoubleClick={() => { setDraft(String(value)); setEditing(true) }}
      title="Double-click to edit (trial calculation)"
    >
      {value.toLocaleString('en-AU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
    </span>
  )
}

export default function FuturesPositions({ rows, onPriceEdit }: Props) {
  return (
    <div className="bg-brand-card border border-brand-border rounded-lg overflow-hidden">
      <div className="px-4 py-2 border-b border-brand-border">
        <span className="text-white font-semibold text-sm">Futures Positions</span>
        <span className="text-brand-muted text-xs ml-2">(double-click Current Price to trial-calculate)</span>
      </div>
      <table className="risk-table">
        <thead>
          <tr>
            <th>Product</th>
            <th>Month</th>
            <th>Position</th>
            <th>Delta$ AUD</th>
            <th>Entry Price</th>
            <th>Current Price</th>
            <th>P/L (%)</th>
            <th>P/L$ AUD</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const priceKey = `${r.product}|${r.month}`
            return (
              <tr key={i}>
                <td className="text-white font-medium">{r.product}</td>
                <td className="muted">{r.month}</td>
                <td className={r.position < 0 ? 'neg' : 'pos'}>{r.position}</td>
                <td className={r.delta_aud < 0 ? 'neg' : 'pos'}>{fmt(r.delta_aud)}</td>
                <td className="muted">
                  {r.entry_price.toLocaleString('en-AU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
                <td>
                  <EditablePrice
                    value={r.current_price}
                    onChange={v => onPriceEdit(priceKey, v)}
                  />
                </td>
                <td className={r.pl_pct < 0 ? 'neg' : 'pos'}>{r.pl_pct.toFixed(2)}%</td>
                <td className={r.pl_aud < 0 ? 'neg' : 'pos'}>{fmt(r.pl_aud)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>

    </div>
  )
}
