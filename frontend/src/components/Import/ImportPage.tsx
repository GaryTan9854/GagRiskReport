import { useState } from 'react'
import { api } from '../../api'

export default function ImportPage() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')

  const handleImport = async () => {
    if (!file) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const r = await api.importPDF(file)
      if (r.detail) throw new Error(r.detail)
      setResult(r)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Import failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl space-y-4">
      <h2 className="text-white font-bold text-lg">Import Macquarie PDF</h2>
      <p className="text-brand-muted text-sm">
        Upload the daily Open Position Statement from Macquarie. Prices, FX rates, cash balances
        and NLV will be automatically extracted and saved.
      </p>

      <div className="bg-brand-card border border-brand-border rounded-lg p-6 space-y-4">
        <div
          className="border-2 border-dashed border-brand-border rounded-lg p-8 text-center cursor-pointer hover:border-brand-accent transition-colors"
          onDragOver={e => { e.preventDefault() }}
          onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f?.type === 'application/pdf') setFile(f) }}
          onClick={() => document.getElementById('pdf-input')?.click()}
        >
          <input
            id="pdf-input"
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={e => setFile(e.target.files?.[0] || null)}
          />
          {file ? (
            <div>
              <p className="text-brand-accent font-semibold">{file.name}</p>
              <p className="text-brand-muted text-sm mt-1">{(file.size / 1024).toFixed(0)} KB</p>
            </div>
          ) : (
            <div className="text-brand-muted">
              <p className="text-2xl mb-2">📄</p>
              <p>Drop PDF here or click to select</p>
              <p className="text-xs mt-1">Macquarie Open Position Statement</p>
            </div>
          )}
        </div>

        <button
          onClick={handleImport}
          disabled={!file || loading}
          className="w-full bg-brand-accent text-brand-bg font-semibold py-2 rounded hover:bg-sky-400 disabled:opacity-40 transition-colors"
        >
          {loading ? 'Importing…' : 'Import PDF'}
        </button>

        {error && <p className="text-brand-red text-sm">{error}</p>}

        {result && (
          <div className="bg-brand-bg rounded p-4 text-sm space-y-2">
            <p className="text-brand-green font-semibold">✓ Import successful</p>
            <div className="text-brand-muted space-y-1">
              <div className="flex justify-between">
                <span>Statement Date:</span>
                <span className="text-white">{String(result.report_date)}</span>
              </div>
              <div className="flex justify-between">
                <span>Positions Found:</span>
                <span className="text-white">{String(result.positions_found)}</span>
              </div>
              <div className="flex justify-between">
                <span>AUD/USD Rate:</span>
                <span className="text-white">{result.audusd != null ? Number(result.audusd).toFixed(5) : '—'}</span>
              </div>
              <div className="flex justify-between">
                <span>Futures NLV:</span>
                <span className="text-white">
                  {result.nlv_aud != null ? `$${Number(result.nlv_aud).toLocaleString('en-AU', { maximumFractionDigits: 0 })}` : '—'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
