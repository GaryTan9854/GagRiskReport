from sqlalchemy import Column, Integer, Float, String, Text, DateTime
from sqlalchemy.sql import func
from database import Base


class Contract(Base):
    __tablename__ = "contracts"
    id = Column(Integer, primary_key=True)
    product_code = Column(String, unique=True, nullable=False)
    exchange = Column(String)
    multiplier = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    is_option = Column(Integer, default=0)
    strike_price = Column(Float)
    call_put = Column(String)
    expiry_date = Column(String)
    margin_per_contract = Column(Float)
    notes = Column(Text)


class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)  # futures, fx1, fx2, fx3, ibkr
    name = Column(String, nullable=False)
    funding_aud = Column(Float, default=0)
    high_water_mark = Column(Float, default=0)
    notes = Column(Text)


class Position(Base):
    """Active (open) positions. One row per lot group per account."""
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True)
    account = Column(String, nullable=False)
    product_code = Column(String, nullable=False)
    contract_month = Column(String)       # e.g. '2603' for Mar 2026
    position = Column(Float, nullable=False)   # signed qty; neg = short
    entry_price = Column(Float, nullable=False)  # original entry (or original_cost for FX)
    latest_cost = Column(Float)           # FX: price at last roll; futures: same as entry
    currency = Column(String)
    multiplier = Column(Float)
    open_date = Column(String)
    # FX roll tracking
    accumulated_roll_pl_orig = Column(Float, default=0)  # USD for AUDUSD positions
    is_active = Column(Integer, default=1)
    notes = Column(Text)


class Transaction(Base):
    """Full ledger: trades, interest, fees, cash movements."""
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    entry_date = Column(String, nullable=False)
    account = Column(String, nullable=False)
    product_code = Column(String)
    contract_month = Column(String)
    position = Column(Float)             # signed qty for trades
    entry_price = Column(Float)
    currency = Column(String)
    fx_rate_to_aud = Column(Float)
    commission = Column(Float, default=0)
    gst = Column(Float, default=0)
    total_commission = Column(Float, default=0)
    is_close_pos = Column(Integer, default=0)
    cost_price = Column(Float)           # entry price of closed position
    close_fx = Column(Float)
    multiplier = Column(Float)
    price_pl = Column(Float, default=0)
    realized_pl_orig = Column(Float, default=0)
    realized_pl_aud = Column(Float, default=0)
    transaction_type = Column(String)    # trade, interest, fee, transfer, expiry, roll
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class PriceDB(Base):
    """Daily closing prices per contract."""
    __tablename__ = "price_db"
    id = Column(Integer, primary_key=True)
    trade_date = Column(String, nullable=False)
    product_code = Column(String, nullable=False)
    contract_month = Column(String)
    price = Column(Float, nullable=False)
    source = Column(String, default="manual")  # pdf, manual


class FXRate(Base):
    """Daily FX rates. Rate = units of foreign currency per 1 AUD."""
    __tablename__ = "fx_rates"
    id = Column(Integer, primary_key=True)
    rate_date = Column(String, nullable=False)
    currency = Column(String, nullable=False)   # e.g. 'USD', 'JPY'
    rate = Column(Float, nullable=False)         # e.g. USD: 0.6668 (1 AUD = 0.6668 USD)
    source = Column(String, default="manual")


class DailySnapshot(Base):
    """Saved daily risk report snapshots (used as YesterdayPL reference)."""
    __tablename__ = "daily_snapshots"
    id = Column(Integer, primary_key=True)
    report_date = Column(String, unique=True, nullable=False)
    snapshot_json = Column(Text, nullable=False)
    # Key Macquarie statement figures (for reconciliation)
    stmt_cash_aud = Column(Float)
    stmt_cash_usd = Column(Float)
    stmt_variation_margin_usd = Column(Float)
    stmt_initial_margin_usd = Column(Float)
    stmt_nlv_aud = Column(Float)
    stmt_audusd = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class CashBalance(Base):
    """Daily cash balance per account per currency."""
    __tablename__ = "cash_balances"
    id = Column(Integer, primary_key=True)
    balance_date = Column(String, nullable=False)
    account = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    amount = Column(Float, nullable=False)


class FundTransfer(Base):
    """Capital injections, withdrawals, and inter-account transfers."""
    __tablename__ = "fund_transfers"
    id = Column(Integer, primary_key=True)
    transfer_date = Column(String, nullable=False)
    from_account = Column(String)   # NULL = external injection
    to_account = Column(String)     # NULL = withdrawal
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    fx_rate_to_aud = Column(Float)
    amount_aud = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
