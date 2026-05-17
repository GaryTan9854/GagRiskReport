import { useState, useEffect } from 'react'
import { api } from '../../api'

export interface Transfer {
  id: number
  transfer_date: string
  from_account: string
  from_label: string
  to_account: string
  to_label: string
  amount: number
  currency: string
  amount_aud: number
  notes: string | null
}

const ACCOUNTS = [
  { code: 'external',   label: 'External' },
  { code: 'futures',    label: 'Macquarie Futures (GAG01)' },
  { code: 'ibkr',       label: 'IBKR' },
  { code: 'fx_account', label: 'FX Account' },
  { code: 'fx1',        label: 'FX1' },
  { code: 'fx2',        label: 'FX2' },
  { code: 'fx3',        label: 'FX3' },
]

function fmtM(n: number): string {
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`
  if (Math.abs(n) >= 1_000)     return `${(n / 1_000).toFixed(0)}K`
  return n.toLocaleString('en-AU')
}

function fmtAUD(n: number): string {
  const abs = Math.abs(n)
  const s = abs.toLocaleString('en-AU', { maximumFractionDigits: 0 })
  return n < 0 ? `($${s})` : `$${s}`
}

const FILTER_ALL = '__all__'

export default function TransfersPage() {
  const [transfers, setTransfers]   = useState<Transfer[]>([])
  const [filter, setFilter]         = useState(FILTER_ALL)
  const [loading, setLoading]       = useState(true)
  const [showForm, setShowForm]     = useState(false)
  const [deleting, setDeleting]     = useState<number | null>(null)

  // Form state
  const today = new Date().toISOString().slice(0, 10)
  const [form, setForm] = useState({
    transfer_date: today,
    from_account: 'external',
    to_account: 'futures',
    amount: '',
    currency: 'AUD',
    notes: '',
  })
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const data = await api.getTransfers(filter === FILTER_ALL ? undefined : filter)
      setTransfers(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [filter])

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.amount || isNaN(Number(form.amount))) return
    setSaving(true)
    try {
      await api.addTransfer({
        transfer_date: form.transfer_date,
        from_account: form.from_account,
        to_account: form.to_account,
        amount: Number(form.amount),
        currency: form.currency,
        notes: form.notes || undefined,
      })
      setShowForm(false)
      setForm({ transfer_date: today, from_account: 'external', to_account: 'futures', amount: '', currency: 'AUD', notes: '' })
      load()
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('刪除這筆轉帳記錄？')) return
    setDeleting(id)
    try {
      await api.deleteTransfer(id)
      load()
    } finally {
      setDeleting(null)
    }
  }

  // Group by account for summary
  const summary: Record<string, { in: number; out: number; net: number }> = {}
  for (const acct of ACCOUNTS) {
    summary[acct.code] = { in: 0, out: 0, net: 0 }
  }
  for (const t of transfers) {
    const amt = t.amount_aud
    if (summary[t.to_account])   { summary[t.to_account].in  += amt; summary[t.to_account].net  += amt }
    if (summary[t.from_account]) { summary[t.from_account].out += amt; summary[t.from_account].net -= amt }
  }

  const shown = filter === FILTER_ALL
    ? transfers
    : transfers.filter(t => t.from_account === filter || t.to_account === filter)

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-2">
        {ACCOUNTS.filter(a => a.code !== 'external').map(acct => {
          const s = summary[acct.code] || { in: 0, out: 0, net: 0 }
          return (
            <button
              key={acct.code}
              onClick={() => setFilter(filter === acct.code ? FILTER_ALL : acct.code)}
              className={`text-left p-3 rounded-lg border transition-colors ${
                filter === acct.code
                  ? 'bg-brand-accent/10 border-brand-accent'
                  : 'bg-brand-card border-brand-border hover:border-brand-accent/40'
              }`}
            >
              <div className="text-xs text-brand-muted mb-1 truncate">{acct.label}</div>
              <div className="text-white font-semibold text-sm">{fmtM(s.net)} AUD</div>
              <div className="text-[10px] text-brand-muted mt-0.5">
                ↑{fmtM(s.in)}  ↓{fmtM(s.out)}
              </div>
            </button>
          )
        })}
      </div>

      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="text-white font-bold">
          {filter === FILTER_ALL ? '所有帳戶轉帳記錄' : ACCOUNTS.find(a => a.code === filter)?.label}
        </span>
        {filter !== FILTER_ALL && (
          <button onClick={() => setFilter(FILTER_ALL)}
            className="text-brand-muted text-xs hover:text-white px-2 py-1 rounded hover:bg-white/5">
            ✕ 清除篩選
          </button>
        )}
        <div className="flex-1" />
        <button
          onClick={() => setShowForm(v => !v)}
          className="bg-brand-accent text-brand-bg text-sm font-semibold px-3 py-1.5 rounded hover:bg-sky-400 transition-colors"
        >
          + 新增轉帳
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <form onSubmit={handleAdd}
          className="bg-brand-card border border-brand-border rounded-lg p-4 flex flex-wrap gap-3 items-end">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-brand-muted">日期</label>
            <input type="date" value={form.transfer_date}
              onChange={e => setForm(f => ({ ...f, transfer_date: e.target.value }))}
              className="bg-brand-bg border border-brand-border rounded px-2 py-1.5 text-white text-sm w-36" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-brand-muted">從</label>
            <select value={form.from_account}
              onChange={e => setForm(f => ({ ...f, from_account: e.target.value }))}
              className="bg-brand-bg border border-brand-border rounded px-2 py-1.5 text-white text-sm">
              {ACCOUNTS.map(a => <option key={a.code} value={a.code}>{a.label}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-brand-muted">至</label>
            <select value={form.to_account}
              onChange={e => setForm(f => ({ ...f, to_account: e.target.value }))}
              className="bg-brand-bg border border-brand-border rounded px-2 py-1.5 text-white text-sm">
              {ACCOUNTS.map(a => <option key={a.code} value={a.code}>{a.label}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-brand-muted">金額</label>
            <input type="number" placeholder="1000000" value={form.amount}
              onChange={e => setForm(f => ({ ...f, amount: e.target.value }))}
              className="bg-brand-bg border border-brand-border rounded px-2 py-1.5 text-white text-sm w-36" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-brand-muted">幣別</label>
            <select value={form.currency}
              onChange={e => setForm(f => ({ ...f, currency: e.target.value }))}
              className="bg-brand-bg border border-brand-border rounded px-2 py-1.5 text-white text-sm w-20">
              {['AUD','USD','JPY','EUR'].map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1 flex-1 min-w-48">
            <label className="text-xs text-brand-muted">備注</label>
            <input type="text" placeholder="說明..." value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              className="bg-brand-bg border border-brand-border rounded px-2 py-1.5 text-white text-sm" />
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={saving}
              className="bg-brand-accent text-brand-bg font-semibold px-4 py-1.5 rounded text-sm hover:bg-sky-400 disabled:opacity-40">
              {saving ? '儲存中…' : '儲存'}
            </button>
            <button type="button" onClick={() => setShowForm(false)}
              className="text-brand-muted px-3 py-1.5 rounded text-sm hover:text-white hover:bg-white/5">
              取消
            </button>
          </div>
        </form>
      )}

      {/* Table */}
      {loading ? (
        <div className="text-brand-muted py-8 text-center">載入中…</div>
      ) : (
        <div className="bg-brand-card border border-brand-border rounded-lg overflow-hidden">
          <table className="risk-table w-full">
            <thead>
              <tr>
                <th className="text-left">日期</th>
                <th className="text-left">從</th>
                <th className="text-left">至</th>
                <th className="text-right">金額</th>
                <th className="text-right">AUD</th>
                <th className="text-left">備注</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {shown.map(t => {
                const isInternal = t.from_account !== 'external' && t.to_account !== 'external'
                return (
                  <tr key={t.id}>
                    <td className="muted text-xs">{t.transfer_date}</td>
                    <td className="text-white text-xs">{t.from_label}</td>
                    <td className="text-white text-xs">{t.to_label}</td>
                    <td className="text-right text-sm">
                      {t.amount.toLocaleString('en-AU')} {t.currency}
                    </td>
                    <td className={`text-right text-sm font-semibold ${isInternal ? 'text-brand-muted' : 'pos'}`}>
                      {fmtAUD(t.amount_aud)}
                    </td>
                    <td className="muted text-xs">{t.notes || '—'}</td>
                    <td className="text-right">
                      <button
                        onClick={() => handleDelete(t.id)}
                        disabled={deleting === t.id}
                        className="text-brand-muted hover:text-brand-red text-xs px-1 disabled:opacity-40"
                        title="刪除"
                      >✕</button>
                    </td>
                  </tr>
                )
              })}
              {shown.length === 0 && (
                <tr><td colSpan={7} className="text-center text-brand-muted py-6">無記錄</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
