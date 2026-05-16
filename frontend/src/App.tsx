import { useState, useEffect } from 'react'
import { api } from './api'
import LoginPage from './components/LoginPage'
import Navbar from './components/Navbar'
import RiskReportPage from './components/RiskReport/RiskReportPage'
import TransactionsPage from './components/Transactions/TransactionsPage'
import ImportPage from './components/Import/ImportPage'

type Tab = 'report' | 'transactions' | 'roll-trades' | 'import'

export default function App() {
  const [authed, setAuthed] = useState(false)
  const [checking, setChecking] = useState(true)
  const [tab, setTab] = useState<Tab>('report')

  useEffect(() => {
    const token = sessionStorage.getItem('gag_token')
    if (!token) { setChecking(false); return }
    api.verify()
      .then(() => setAuthed(true))
      .catch(() => sessionStorage.removeItem('gag_token'))
      .finally(() => setChecking(false))
  }, [])

  const handleLogin = (token: string) => {
    sessionStorage.setItem('gag_token', token)
    setAuthed(true)
  }

  const handleLogout = () => {
    sessionStorage.removeItem('gag_token')
    setAuthed(false)
  }

  if (checking) return (
    <div className="flex items-center justify-center h-screen text-brand-muted">Loading…</div>
  )

  if (!authed) return <LoginPage onLogin={handleLogin} />

  return (
    <div className="min-h-screen bg-brand-bg">
      <Navbar tab={tab} onTab={setTab} onLogout={handleLogout} />
      <main className="p-4 max-w-[1400px] mx-auto">
        {tab === 'report'       && <RiskReportPage />}
        {tab === 'transactions' && <TransactionsPage view="all" />}
        {tab === 'roll-trades'  && <TransactionsPage view="rolls" />}
        {tab === 'import'       && <ImportPage />}
      </main>
    </div>
  )
}
