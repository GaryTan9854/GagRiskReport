"""
Daily Risk Report calculation engine.

Terminology:
  - delta_aud      : total notional AUD exposure (signed)
  - closing_pl_aud : overnight mark-to-market PL vs yesterday's price
  - trade_pl_aud   : intraday PL from trades executed today
  - today_pl_aud   : closing_pl + trade_pl
  - total_pl_aud   : yesterday's total_pl + today_pl (cumulative since inception)
"""

import json
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from models import Position, PriceDB, FXRate, DailySnapshot, Transaction, CashBalance

FACE_VALUE_FX = 1_000_000  # 1 支 = 1 million AUD


def _prev_trading_date(d: str, db: Session) -> Optional[str]:
    """Return the most recent date before d that has a saved snapshot."""
    row = (
        db.query(DailySnapshot.report_date)
        .filter(DailySnapshot.report_date < d)
        .order_by(DailySnapshot.report_date.desc())
        .first()
    )
    return row[0] if row else None


def _get_price(db: Session, trade_date: str, product_code: str,
               contract_month: str) -> tuple:
    """
    Get closing price for a contract on a date.
    Returns (price, actual_contract_month) or (None, None).

    Priority (to handle contract rolls correctly):
      1. Exact date + exact contract_month  (perfect)
      2. Exact date + any contract_month    (PDF exists for this date — use the active contract)
      3. Most recent historical exact month (no PDF for this date, carry forward)
      4. Most recent historical any month   (last resort)
    """
    # 1. Perfect match
    row = db.query(PriceDB).filter(
        PriceDB.trade_date == trade_date,
        PriceDB.product_code == product_code,
        PriceDB.contract_month == contract_month,
    ).first()
    if row:
        return row.price, row.contract_month

    # 2. Same date, any contract (PDF imported but position rolled — use current contract price)
    row = db.query(PriceDB).filter(
        PriceDB.trade_date == trade_date,
        PriceDB.product_code == product_code,
    ).order_by(PriceDB.contract_month.desc()).first()
    if row:
        return row.price, row.contract_month

    # 3. Most recent historical exact month
    row = db.query(PriceDB).filter(
        PriceDB.trade_date < trade_date,
        PriceDB.product_code == product_code,
        PriceDB.contract_month == contract_month,
    ).order_by(PriceDB.trade_date.desc()).first()
    if row:
        return row.price, row.contract_month

    # 4. Most recent historical any month
    row = db.query(PriceDB).filter(
        PriceDB.trade_date < trade_date,
        PriceDB.product_code == product_code,
    ).order_by(PriceDB.trade_date.desc()).first()
    return (row.price, row.contract_month) if row else (None, None)


def _get_fx(db: Session, rate_date: str, currency: str) -> float:
    """Get FX rate (units of currency per 1 AUD). Returns 1.0 for AUD."""
    if currency == "AUD":
        return 1.0
    row = (
        db.query(FXRate)
        .filter(FXRate.rate_date <= rate_date, FXRate.currency == currency)
        .order_by(FXRate.rate_date.desc())
        .first()
    )
    return row.rate if row else 1.0


def _get_yesterday_snapshot(db: Session, report_date: str) -> Optional[dict]:
    prev_date = _prev_trading_date(report_date, db)
    if not prev_date:
        return None
    row = db.query(DailySnapshot).filter(DailySnapshot.report_date == prev_date).first()
    return json.loads(row.snapshot_json) if row else None


def _calc_futures_position(pos: Position, current_price: float, prev_price: Optional[float],
                            audusd: float) -> dict:
    """Calculate all fields for a single futures position row."""
    multiplier = pos.multiplier or 50
    pl_pct = (current_price - pos.entry_price) / pos.entry_price * (1 if pos.position > 0 else -1)
    pl_orig = (current_price - pos.entry_price) * pos.position * multiplier
    pl_aud = pl_orig / audusd

    delta_aud = pos.position * current_price * multiplier / audusd

    closing_pl_aud = 0.0
    if prev_price is not None:
        closing_pl_orig = (current_price - prev_price) * pos.position * multiplier
        closing_pl_aud = closing_pl_orig / audusd

    return {
        "product": pos.product_code,
        "month": pos.contract_month,
        "position": pos.position,
        "delta_aud": round(delta_aud),
        "entry_price": pos.entry_price,
        "current_price": current_price,
        "pl_pct": round(pl_pct * 100, 2),
        "pl_aud": round(pl_aud),
        "currency": pos.currency or "USD",
        "multiplier": multiplier,
        "closing_pl_aud": round(closing_pl_aud),
    }


def _calc_fx_position(pos: Position, current_audusd: float, prev_audusd: Optional[float]) -> dict:
    """
    FX forward position (1 支 = 1M AUD).
    pos.entry_price = original_cost (AUD/USD rate at first entry)
    pos.latest_cost = rate at last roll (None if never rolled)
    """
    face = FACE_VALUE_FX
    original_cost = pos.entry_price
    latest_cost = pos.latest_cost if pos.latest_cost is not None else original_cost

    # P/L% uses original cost
    pl_pct = (current_audusd - original_cost) / original_cost * (1 if pos.position > 0 else -1)

    # P/L$ AUD uses latest cost (current roll period)
    pl_usd_latest = (current_audusd - latest_cost) * pos.position * face
    pl_aud_latest = pl_usd_latest / current_audusd if current_audusd else 0

    # Original cost P/L$
    pl_usd_orig = (current_audusd - original_cost) * pos.position * face
    pl_aud_orig = pl_usd_orig / current_audusd if current_audusd else 0

    # Accumulated roll P/L = P/L from original - P/L from latest
    accum_roll_pl_aud = pl_aud_orig - pl_aud_latest

    # Delta$ AUD = face value of position (AUD exposure)
    delta_aud = pos.position * face

    # Delta$ in quote currency (USD) = face × latest_cost
    delta_quote = pos.position * face * latest_cost

    # PL$ in quote currency
    pl_quote = pl_usd_latest

    # Closing PL
    closing_pl_aud = 0.0
    if prev_audusd is not None:
        closing_pl_usd = (current_audusd - prev_audusd) * pos.position * face
        closing_pl_aud = closing_pl_usd / current_audusd if current_audusd else 0

    return {
        "product": pos.product_code,
        "position": pos.position,
        "delta_aud": round(delta_aud),
        "original_cost": original_cost,
        "latest_cost": latest_cost,
        "current_price": current_audusd,
        "pl_pct": round(pl_pct * 100, 2),
        "pl_aud": round(pl_aud_latest),
        "delta_quote": round(delta_quote),
        "pl_quote": round(pl_quote),
        "original_cost_pl_aud": round(pl_aud_orig),
        "accum_roll_pl_aud": round(accum_roll_pl_aud),
        "closing_pl_aud": round(closing_pl_aud),
    }


def calc_report(db: Session, report_date: str, price_overrides: dict = None) -> dict:
    """
    Calculate the full daily risk report for report_date.
    price_overrides: {('CME ES', '2603'): 7500.0, 'AUDUSD': 0.720, ...}
    """
    if price_overrides is None:
        price_overrides = {}

    # ── FX rates ──────────────────────────────────────────────────────────────
    def audusd(d): return _get_fx(db, d, "USD")
    def audjpy(d): return _get_fx(db, d, "JPY")
    def audeur(d): return _get_fx(db, d, "EUR")

    today_audusd = price_overrides.get("AUDUSD") or audusd(report_date)
    today_audjpy = price_overrides.get("AUDJPY") or audjpy(report_date)

    # ── Yesterday snapshot ────────────────────────────────────────────────────
    yesterday = _get_yesterday_snapshot(db, report_date)

    # ── Open positions ────────────────────────────────────────────────────────
    all_positions = db.query(Position).filter(Position.is_active == 1).all()
    futures_positions = [p for p in all_positions if p.account == "futures"]
    fx_positions = {
        "fx1": [p for p in all_positions if p.account == "fx1"],
        "fx2": [p for p in all_positions if p.account == "fx2"],
        "fx3": [p for p in all_positions if p.account == "fx3"],
    }

    # ── Futures positions ─────────────────────────────────────────────────────
    futures_rows = []
    futures_delta_aud = 0.0
    futures_closing_pl = 0.0

    for pos in futures_positions:
        key = (pos.product_code, pos.contract_month)
        override = price_overrides.get(key)
        if override:
            current_price, actual_month = override, pos.contract_month
        else:
            current_price, actual_month = _get_price(db, report_date, pos.product_code, pos.contract_month)
        if current_price is None:
            continue

        # Yesterday price for closing PL — match on product + whichever month was active then
        prev_price = None
        if yesterday:
            for prev_row in yesterday.get("positions", {}).get("futures", []):
                if prev_row["product"] == pos.product_code:
                    prev_price = prev_row["current_price"]
                    break

        row = _calc_futures_position(pos, current_price, prev_price, today_audusd)
        row["month"] = actual_month  # show the contract month actually priced
        futures_rows.append(row)
        futures_delta_aud += row["delta_aud"]
        futures_closing_pl += row["closing_pl_aud"]

    # ── Trades executed today ─────────────────────────────────────────────────
    today_trades = (
        db.query(Transaction)
        .filter(Transaction.entry_date == report_date, Transaction.account == "futures",
                Transaction.transaction_type == "trade")
        .all()
    )

    futures_trade_pl = 0.0
    for t in today_trades:
        key = (t.product_code, t.contract_month)
        current_price = price_overrides.get(key) or _get_price(db, report_date, t.product_code, t.contract_month)
        if current_price is None:
            current_price = t.entry_price

        if t.is_close_pos:
            # Closed position: realized PL
            futures_trade_pl += t.realized_pl_aud or 0
        else:
            # New position opened today: MTM gain/loss since trade
            mult = t.multiplier or 50
            key = (t.product_code, t.contract_month)
            override = price_overrides.get(key)
            if override:
                current_price = override
            else:
                current_price, _ = _get_price(db, report_date, t.product_code, t.contract_month)
                if current_price is None:
                    current_price = t.entry_price
            pl_orig = (current_price - t.entry_price) * t.position * mult
            fx = t.fx_rate_to_aud or today_audusd
            futures_trade_pl += pl_orig / fx if fx else 0

    # ── FX positions (per sub-account) ────────────────────────────────────────
    fx_results = {}
    for acct, positions in fx_positions.items():
        rows = []
        closing_pl = 0.0
        delta_aud = 0.0

        # Get yesterday's AUDUSD for closing PL
        prev_audusd = None
        if yesterday:
            prev_audusd = yesterday.get("fx_rates", {}).get("AUDUSD")

        for pos in positions:
            # For AUD/JPY positions
            if "JPY" in (pos.currency or ""):
                current_rate = price_overrides.get("AUDJPY") or today_audjpy
                prev_rate = yesterday.get("fx_rates", {}).get("AUDJPY") if yesterday else None
            else:
                current_rate = price_overrides.get("AUDUSD") or today_audusd
                prev_rate = prev_audusd

            row = _calc_fx_position(pos, current_rate, prev_rate)
            rows.append(row)
            closing_pl += row["closing_pl_aud"]
            delta_aud += row["delta_aud"]

        fx_results[acct] = {
            "rows": rows,
            "closing_pl": round(closing_pl),
            "delta_aud": round(delta_aud),
        }

    # ── Build P&L summary per account ────────────────────────────────────────
    def build_pl(acct_key: str, closing_pl: float, trade_pl: float, yesterday_snap: Optional[dict]) -> dict:
        y_total_pl = 0.0
        if yesterday_snap:
            y_total_pl = yesterday_snap.get("pl", {}).get(acct_key, {}).get("total_pl", 0.0)

        today_pl = round(closing_pl + trade_pl)
        total_pl = round(y_total_pl + today_pl)

        return {
            "yesterday_pl": round(y_total_pl),
            "trade_pl": round(trade_pl),
            "closing_pl": round(closing_pl),
            "today_pl": today_pl,
            "total_pl": total_pl,
        }

    # Futures
    futures_pl = build_pl("futures", futures_closing_pl, futures_trade_pl, yesterday)

    # FX accounts (no manual trades for now — only closing PL)
    fx1_pl = build_pl("fx1", fx_results["fx1"]["closing_pl"], 0, yesterday)
    fx2_pl = build_pl("fx2", fx_results["fx2"]["closing_pl"], 0, yesterday)
    fx3_pl = build_pl("fx3", fx_results["fx3"]["closing_pl"], 0, yesterday)

    # IB — static for now (no positions), carried from yesterday
    ib_total_pl = yesterday.get("pl", {}).get("ib", {}).get("total_pl", 0) if yesterday else 0
    ib_pl = {"yesterday_pl": ib_total_pl, "trade_pl": 0, "closing_pl": 0, "today_pl": 0, "total_pl": ib_total_pl}

    # FX combined (FX1 + FX2 + FX3) — shown as single "FX" column in report header
    fx_combined_pl_total = (
        (yesterday.get("pl", {}).get("fx_combined", {}).get("total_pl", 0) if yesterday else 0)
        + fx1_pl["today_pl"] + fx2_pl["today_pl"] + fx3_pl["today_pl"]
    )
    fx_combined_pl = {
        "yesterday_pl": (yesterday.get("pl", {}).get("fx_combined", {}).get("total_pl", 0) if yesterday else 0),
        "trade_pl": 0,
        "closing_pl": fx1_pl["closing_pl"] + fx2_pl["closing_pl"] + fx3_pl["closing_pl"],
        "today_pl": fx1_pl["today_pl"] + fx2_pl["today_pl"] + fx3_pl["today_pl"],
        "total_pl": fx_combined_pl_total,
    }

    # Grand totals
    total_today_pl = futures_pl["today_pl"] + ib_pl["today_pl"] + fx_combined_pl["today_pl"]
    total_total_pl = futures_pl["total_pl"] + ib_pl["total_pl"] + fx_combined_pl_total

    total_pl_summary = {
        "yesterday_pl": futures_pl["yesterday_pl"] + ib_pl["yesterday_pl"] + fx_combined_pl["yesterday_pl"],
        "trade_pl": futures_trade_pl,
        "closing_pl": futures_closing_pl + fx_combined_pl["closing_pl"],
        "today_pl": total_today_pl,
        "total_pl": total_total_pl,
    }

    # ── NLV ───────────────────────────────────────────────────────────────────
    # Read latest cash balances
    def latest_cash(account: str, currency: str) -> float:
        row = (
            db.query(CashBalance)
            .filter(CashBalance.account == account, CashBalance.currency == currency,
                    CashBalance.balance_date <= report_date)
            .order_by(CashBalance.balance_date.desc())
            .first()
        )
        return row.amount if row else 0.0

    futures_cash_aud = latest_cash("futures", "AUD")
    futures_cash_usd = latest_cash("futures", "USD")

    # NLV from Macquarie: cash + variation margin + initial margin released
    # We'll use the snapshot if available, otherwise compute from cash
    yesterday_stmt = yesterday.get("statement") if yesterday else None
    stmt_nlv_aud = yesterday_stmt.get("nlv_aud") if yesterday_stmt else None

    # Compute funding/PL percentages
    futures_funding = db.query(Account).filter_by(code="futures").first()
    futures_funding_aud = futures_funding.funding_aud if futures_funding else 0
    ib_funding = db.query(Account).filter_by(code="ibkr").first()
    ib_funding_aud = ib_funding.funding_aud if ib_funding else 0
    fx_funding = db.query(Account).filter_by(code="fx_combined").first()
    fx_funding_aud = fx_funding.funding_aud if fx_funding else 0

    total_funding_aud = futures_funding_aud + ib_funding_aud + fx_funding_aud

    def pl_pct(total_pl, funding):
        return round(total_pl / funding * 100, 2) if funding else 0.0

    # PL$ and High Water Mark
    futures_hwm = futures_funding.high_water_mark if futures_funding else 500000
    fx2_hwm = (db.query(Account).filter_by(code="fx2").first() or type("A", (), {"high_water_mark": 100000})()).high_water_mark
    fx3_hwm = (db.query(Account).filter_by(code="fx3").first() or type("A", (), {"high_water_mark": 100000})()).high_water_mark

    # ── Cash balances latest ──────────────────────────────────────────────────
    ibkr_nlv = latest_cash("ibkr", "AUD") or (yesterday.get("nlv", {}).get("ibkr") if yesterday else 35799)
    fx_nlv = latest_cash("fx_combined", "AUD") or (yesterday.get("nlv", {}).get("fx") if yesterday else 0)

    # ── VIX ───────────────────────────────────────────────────────────────────
    vix_price = _get_price(db, report_date, "VIX", "CASH")
    vix_accum_pl = yesterday.get("vix_accum_pl") if yesterday else None

    result = {
        "report_date": report_date,
        "pl": {
            "futures": futures_pl,
            "ib": ib_pl,
            "fx_combined": fx_combined_pl,
            "fx2": fx2_pl,
            "fx3": fx3_pl,
            "total": total_pl_summary,
        },
        "pl_pct": {
            "futures": pl_pct(futures_pl["total_pl"], futures_funding_aud),
            "ib": pl_pct(ib_pl["total_pl"], ib_funding_aud),
            "fx2": pl_pct(fx2_pl["total_pl"], fx_funding_aud / 3 if fx_funding_aud else 0),
            "fx3": pl_pct(fx3_pl["total_pl"], fx_funding_aud / 3 if fx_funding_aud else 0),
            "total": pl_pct(total_total_pl, total_funding_aud),
        },
        "pl_dollar": {
            "futures_ib": round(futures_pl["total_pl"] + ib_pl["total_pl"]),
            "fx2": fx2_pl["total_pl"],
            "fx3": fx3_pl["total_pl"],
        },
        "high_water_mark": {
            "futures_ib": futures_hwm,
            "fx2": fx2_hwm,
            "fx3": fx3_hwm,
        },
        "positions": {
            "futures": futures_rows,
            "fx1": fx_results["fx1"]["rows"],
            "fx2": fx_results["fx2"]["rows"],
            "fx3": fx_results["fx3"]["rows"],
        },
        "delta": {
            "futures": round(futures_delta_aud),
            "ibkr": 0,
            "fx": round(sum(v["delta_aud"] for v in fx_results.values())),
        },
        "nlv": {
            "futures": round(stmt_nlv_aud) if stmt_nlv_aud else None,
            "ibkr": round(ibkr_nlv),
            "fx": round(fx_nlv),
        },
        "funding": {
            "futures": futures_funding_aud,
            "ibkr": ib_funding_aud,
            "fx": fx_funding_aud,
        },
        "original_nlv": total_funding_aud,
        "current_nlv": round((stmt_nlv_aud or 0) + ibkr_nlv + fx_nlv),
        "vix_cash": vix_price,
        "vix_accum_pl": vix_accum_pl,
        "fx_rates": {
            "AUDUSD": today_audusd,
            "AUDJPY": today_audjpy,
        },
        "statement": None,  # populated when PDF is imported
    }

    return result


# avoid circular import
from models import Account  # noqa: E402
