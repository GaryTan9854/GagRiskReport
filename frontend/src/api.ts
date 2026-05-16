const BASE = '/api'

function getToken(): string | null {
  return sessionStorage.getItem('gag_token')
}

function authHeaders(): HeadersInit {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init.headers || {}) },
  })
  if (res.status === 401) {
    sessionStorage.removeItem('gag_token')
    window.location.reload()
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

export const api = {
  // Auth
  login: (password: string) =>
    request<{ token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ password }),
    }),

  verify: () => request<{ valid: boolean }>('/auth/verify'),

  // Report
  getReport: (date: string) => request<import('./types').RiskReport>(`/report/${date}`),

  calcReport: (date: string, prices: Record<string, number>) =>
    request<import('./types').RiskReport>(`/report/${date}/calc`, {
      method: 'POST',
      body: JSON.stringify({ prices }),
    }),

  saveSnapshot: (date: string) =>
    request<{ saved: boolean }>(`/report/${date}/save`, { method: 'POST' }),

  listSnapshots: (limit = 30) =>
    request<{ report_date: string; nlv_aud: number }[]>(`/report/?limit=${limit}`),

  // Transactions
  getTransactions: (params: { account?: string; year?: number; entry_date?: string; transaction_type?: string; limit?: number; offset?: number } = {}) => {
    const qs = new URLSearchParams()
    if (params.account) qs.set('account', params.account)
    if (params.year) qs.set('year', String(params.year))
    if (params.entry_date) qs.set('entry_date', params.entry_date)
    if (params.transaction_type) qs.set('transaction_type', params.transaction_type)
    if (params.limit) qs.set('limit', String(params.limit))
    if (params.offset) qs.set('offset', String(params.offset))
    return request<{ total: number; items: import('./types').Transaction[] }>(`/transactions?${qs}`)
  },

  getRollTrades: (account = 'futures', product?: string) => {
    const qs = new URLSearchParams({ account })
    if (product) qs.set('product_code', product)
    return request<import('./types').RollTrade[]>(`/transactions/roll-trades?${qs}`)
  },

  // Prices
  getPrices: (date: string) => request<{ product_code: string; contract_month: string; price: number }[]>(`/prices/${date}`),

  upsertPrice: (data: { trade_date: string; product_code: string; contract_month?: string; price: number; source?: string }) =>
    request('/prices', { method: 'POST', body: JSON.stringify(data) }),

  getFXRates: (date: string) => request<Record<string, number>>(`/prices/fx/${date}`),

  upsertFXRate: (data: { rate_date: string; currency: string; rate: number }) =>
    request('/prices/fx', { method: 'POST', body: JSON.stringify(data) }),

  // PDF Import
  importPDF: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return fetch(`${BASE}/import/pdf`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: form,
    }).then(r => r.json())
  },
}
