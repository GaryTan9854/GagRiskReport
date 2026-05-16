import { useState } from 'react'
import { api } from '../api'

export default function LoginPage({ onLogin }: { onLogin: (token: string) => void }) {
  const [pw, setPw] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const { token } = await api.login(pw)
      onLogin(token)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-bg">
      <div className="bg-brand-card border border-brand-border rounded-xl p-8 w-80">
        <div className="text-center mb-6">
          <img src="/gag-icon.png" alt="GAG" className="w-16 h-16 object-contain mx-auto" />
          <h1 className="text-xl font-bold text-white mt-2">
            <span className="text-brand-accent">GAG</span> Risk Report
          </h1>
          <p className="text-brand-muted text-sm mt-1">GA Global Pty Ltd</p>
        </div>
        <form onSubmit={submit} className="flex flex-col gap-3">
          <input
            type="password"
            value={pw}
            onChange={e => setPw(e.target.value)}
            placeholder="Password"
            className="bg-brand-bg border border-brand-border rounded px-3 py-2 text-white focus:outline-none focus:border-brand-accent"
            autoFocus
          />
          {error && <p className="text-brand-red text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading || !pw}
            className="bg-brand-accent text-brand-bg font-semibold rounded py-2 hover:bg-sky-400 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Logging in…' : 'Login'}
          </button>
        </form>
      </div>
    </div>
  )
}
