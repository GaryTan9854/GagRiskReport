export interface PLAccount {
  yesterday_pl: number
  trade_pl: number
  closing_pl: number
  today_pl: number
  total_pl: number
}

export interface FuturesRow {
  product: string
  month: string
  position: number
  delta_aud: number
  entry_price: number
  current_price: number
  pl_pct: number
  pl_aud: number
  currency: string
  multiplier: number
  closing_pl_aud: number
}

export interface FXRow {
  product: string
  position: number
  delta_aud: number
  original_cost: number
  latest_cost: number
  current_price: number
  pl_pct: number
  pl_aud: number
  delta_quote: number
  pl_quote: number
  original_cost_pl_aud: number
  accum_roll_pl_aud: number
  closing_pl_aud: number
}

export interface StatementData {
  cash_aud: number
  cash_usd: number
  audusd_rate: number
  variation_margin_usd: number
  initial_margin_usd: number
  nlv_aud: number
}

export interface RiskReport {
  report_date: string
  pl: {
    futures: PLAccount
    ib: PLAccount
    fx_combined: PLAccount
    fx2: PLAccount
    fx3: PLAccount
    total: PLAccount
  }
  pl_pct: {
    futures: number
    ib: number
    fx2: number
    fx3: number
    total: number
  }
  pl_dollar: {
    futures_ib: number
    fx2: number
    fx3: number
  }
  high_water_mark: {
    futures_ib: number
    fx2: number
    fx3: number
  }
  positions: {
    futures: FuturesRow[]
    fx1: FXRow[]
    fx2: FXRow[]
    fx3: FXRow[]
  }
  delta: { futures: number; ibkr: number; fx: number }
  nlv: { futures: number | null; ibkr: number; fx: number }
  funding: { futures: number; ibkr: number; fx: number }
  original_nlv: number
  current_nlv: number
  vix_cash: number | null
  vix_accum_pl: number | null
  fx_rates: { AUDUSD: number; AUDJPY?: number }
  statement: StatementData | null
}

export interface Transaction {
  id: number
  entry_date: string
  account: string
  product_code: string | null
  contract_month: string | null
  position: number | null
  entry_price: number | null
  currency: string | null
  fx_rate_to_aud: number | null
  commission: number | null
  total_commission: number | null
  is_close_pos: number
  cost_price: number | null
  multiplier: number | null
  price_pl: number | null
  realized_pl_orig: number | null
  realized_pl_aud: number | null
  transaction_type: string | null
  notes: string | null
}

export interface RollTrade {
  date: string
  product: string
  close_month: string
  open_month: string
  lots: number
  avg_close_price: number
  avg_open_price: number
  gross_pl_aud: number
  total_commission: number
  net_pl_aud: number
  currency: string
}
