import { useState } from 'react'
import { FXRow } from '../../types'

function fmt(n: number): string {
  const abs = Math.abs(n)
  const s = abs.toLocaleString('en-AU', { maximumFractionDigits: 0 })
  return n < 0 ? `($${s})` : `$${s}`
}

function fmtRate(n: number): string {
  return n.toFixed(5)
}

function EditableRate({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(fmtRate(value))

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
      onDoubleClick={() => { setDraft(fmtRate(value)); setEditing(true) }}
      title="Double-click to edit"
    >
      {fmtRate(value)}
    </span>
  )
}

interface Props {
  title: string
  rows: FXRow[]
  onPriceEdit: (key: string, value: number) => void
}

export default function FXPositions({ title, rows, onPriceEdit }: Props) {
  return (
    <div className="bg-brand-card border border-brand-border rounded-lg overflow-hidden">
      <div className="px-4 py-2 border-b border-brand-border">
        <span className="text-white font-semibold text-sm">{title}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="risk-table whitespace-nowrap">
          <thead>
            <tr>
              <th>Product</th>
              <th>Position</th>
              <th>Delta$ AUD</th>
              <th>Original Cost</th>
              <th>Latest Cost</th>
              <th>Current Price</th>
              <th>P/L (%)</th>
              <th>P/L$ AUD</th>
              <th>Delta$ (Quote)</th>
              <th>PL$ (Quote)</th>
              <th>Original Cost PL$</th>
              <th>Accumulated Roll PL$</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              // Key for AUDUSD: "AUDUSD", for AUDJPY: "AUDJPY"
              const rateKey = r.product.replace('/', '')
              return (
                <tr key={i}>
                  <td className="text-white font-medium">{r.product}</td>
                  <td className={r.position < 0 ? 'neg' : 'pos'}>{r.position}</td>
                  <td className={r.delta_aud < 0 ? 'neg' : 'pos'}>{fmt(r.delta_aud)}</td>
                  <td className="muted">{fmtRate(r.original_cost)}</td>
                  <td className="muted">{fmtRate(r.latest_cost)}</td>
                  <td>
                    <EditableRate
                      value={r.current_price}
                      onChange={v => onPriceEdit(rateKey, v)}
                    />
                  </td>
                  <td className={r.pl_pct < 0 ? 'neg' : 'pos'}>{r.pl_pct.toFixed(2)}%</td>
                  <td className={r.pl_aud < 0 ? 'neg' : 'pos'}>{fmt(r.pl_aud)}</td>
                  <td className="muted">{fmt(r.delta_quote)}</td>
                  <td className={r.pl_quote < 0 ? 'neg' : 'pos'}>{fmt(r.pl_quote)}</td>
                  <td className={r.original_cost_pl_aud < 0 ? 'neg' : 'pos'}>{fmt(r.original_cost_pl_aud)}</td>
                  <td className={r.accum_roll_pl_aud < 0 ? 'neg' : 'pos'}>{fmt(r.accum_roll_pl_aud)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
