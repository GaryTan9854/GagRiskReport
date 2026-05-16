"""
Seed 2025-12-31 starting state into the database.

Run once: python seed_data.py
"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, SessionLocal
from models import Account, Contract, Position, PriceDB, FXRate, CashBalance, DailySnapshot

SEED_DATE = "2025-12-31"


def seed():
    init_db()
    db = SessionLocal()

    # Idempotency check
    if db.query(Account).count() > 0:
        print("Database already seeded. Skipping.")
        db.close()
        return

    # ── Accounts ──────────────────────────────────────────────────────────────
    accounts = [
        Account(code="futures",     name="Macquarie Futures (GAG01)",
                funding_aud=15_800_000, high_water_mark=500_000),
        Account(code="ibkr",        name="Interactive Brokers",
                funding_aud=6_150_000, high_water_mark=0),
        Account(code="fx1",         name="Macquarie FX Sub-Account 1",
                funding_aud=6_000_000, high_water_mark=0),
        Account(code="fx2",         name="Macquarie FX Sub-Account 2",
                funding_aud=6_000_000, high_water_mark=100_000),
        Account(code="fx3",         name="Macquarie FX Sub-Account 3",
                funding_aud=6_000_000, high_water_mark=100_000),
        Account(code="fx_combined", name="Macquarie FX (All Sub-Accounts)",
                funding_aud=18_000_000, high_water_mark=0),
    ]
    db.add_all(accounts)

    # ── Contracts ─────────────────────────────────────────────────────────────
    contracts = [
        Contract(product_code="CME ES",  exchange="CME",  multiplier=50,  currency="USD",
                 margin_per_contract=32556),
        Contract(product_code="CBOT YM", exchange="CBOT", multiplier=5,   currency="USD",
                 margin_per_contract=11498),
        Contract(product_code="CME NQ",  exchange="CME",  multiplier=20,  currency="USD",
                 margin_per_contract=22000),
        Contract(product_code="CMX GC",  exchange="CME",  multiplier=100, currency="USD",
                 margin_per_contract=11880),
        Contract(product_code="CBOE VIX",exchange="CBOE", multiplier=1000,currency="USD",
                 margin_per_contract=7766),
        Contract(product_code="AUD/USD", exchange="FX",   multiplier=1,   currency="USD"),
        Contract(product_code="AUD/JPY", exchange="FX",   multiplier=1,   currency="JPY"),
    ]
    db.add_all(contracts)

    # ── Open Positions (as of 2025-12-31) ────────────────────────────────────
    positions = [
        # Futures — short ES (62 lots, Mar 2026)
        Position(account="futures", product_code="CME ES", contract_month="2603",
                 position=-62, entry_price=6778.44, latest_cost=6778.44,
                 currency="USD", multiplier=50, open_date="2025-12-18", is_active=1),
        # Futures — short YM (4 lots, Mar 2026)
        Position(account="futures", product_code="CBOT YM", contract_month="2603",
                 position=-4, entry_price=48236.00, latest_cost=48236.00,
                 currency="USD", multiplier=5, open_date="2025-12-18", is_active=1),
        # FX3 — long AUDUSD position 1 (original 0.74920, rolled to 0.79776)
        Position(account="fx3", product_code="AUD/USD", contract_month=None,
                 position=1, entry_price=0.74920, latest_cost=0.79776,
                 currency="USD", multiplier=1, open_date=None,
                 accumulated_roll_pl_orig=0, is_active=1,
                 notes="Original cost 0.74920"),
        # FX3 — long AUDUSD position 2 (original 0.61570, rolled to 0.62797)
        Position(account="fx3", product_code="AUD/USD", contract_month=None,
                 position=1, entry_price=0.61570, latest_cost=0.62797,
                 currency="USD", multiplier=1, open_date=None,
                 accumulated_roll_pl_orig=0, is_active=1,
                 notes="Original cost 0.61570"),
    ]
    db.add_all(positions)

    # ── Prices (2025-12-31 closing prices from Macquarie statement) ───────────
    prices = [
        PriceDB(trade_date=SEED_DATE, product_code="CME ES",  contract_month="2603",
                price=6892.50, source="pdf"),
        PriceDB(trade_date=SEED_DATE, product_code="CBOT YM", contract_month="2603",
                price=48336.00, source="pdf"),
        PriceDB(trade_date=SEED_DATE, product_code="VIX",     contract_month="CASH",
                price=14.95, source="manual"),
    ]
    db.add_all(prices)

    # ── FX Rates (2025-12-31) ─────────────────────────────────────────────────
    # From Macquarie statement: 1 AUD = 0.66680 USD
    # FX3 report shows AUD/USD current price 0.66702 for FX positions
    fx_rates = [
        FXRate(rate_date=SEED_DATE, currency="USD", rate=0.66680, source="pdf"),
    ]
    db.add_all(fx_rates)

    # ── Cash Balances (2025-12-31 from Macquarie statement) ──────────────────
    cash = [
        CashBalance(balance_date=SEED_DATE, account="futures", currency="AUD", amount=3_493_790.98),
        CashBalance(balance_date=SEED_DATE, account="futures", currency="USD", amount=2_834_202.56),
        CashBalance(balance_date=SEED_DATE, account="ibkr",    currency="AUD", amount=35_799.00),
        # FX combined NLV (from risk report)
        CashBalance(balance_date=SEED_DATE, account="fx_combined", currency="AUD", amount=21_947_898.00),
    ]
    db.add_all(cash)

    # ── Save 2025-12-31 snapshot ──────────────────────────────────────────────
    snapshot_2025 = {
        "report_date": SEED_DATE,
        "pl": {
            "futures":     {"yesterday_pl": -8855590, "trade_pl": 0, "closing_pl": 266567,  "today_pl": 266567,  "total_pl": -8589022},
            "ib":          {"yesterday_pl": -6114201, "trade_pl": 0, "closing_pl": 0,        "today_pl": 0,        "total_pl": -6114201},
            "fx_combined": {"yesterday_pl":  3954466, "trade_pl": 0, "closing_pl": -7568,    "today_pl": -7568,    "total_pl":  3946898},
            "fx2":         {"yesterday_pl":   894776, "trade_pl": 0, "closing_pl": 0,        "today_pl": 0,        "total_pl":   894776},
            "fx3":         {"yesterday_pl":   353732, "trade_pl": 0, "closing_pl": -7568,    "today_pl": -7568,    "total_pl":   346164},
            "total":       {"yesterday_pl": -11014325,"trade_pl": 0, "closing_pl": 258999,   "today_pl": 258999,   "total_pl": -10755326},
        },
        "positions": {
            "futures": [
                {"product": "CME ES",  "month": "2603", "position": -62, "delta_aud": -32043716,
                 "entry_price": 6778.44, "current_price": 6892.50, "pl_pct": -1.68, "pl_aud": -530268,
                 "currency": "USD", "multiplier": 50, "closing_pl_aud": 266567},
                {"product": "CBOT YM","month": "2603", "position": -4,  "delta_aud": -1449790,
                 "entry_price": 48236.00,"current_price": 48336.00,"pl_pct": -0.21,"pl_aud": -2999,
                 "currency": "USD", "multiplier": 5,  "closing_pl_aud": 0},
            ],
            "fx1": [],
            "fx2": [],
            "fx3": [
                {"product": "AUD/USD", "position": 1, "delta_aud": 1000000,
                 "original_cost": 0.74920, "latest_cost": 0.79776, "current_price": 0.66702,
                 "pl_pct": -10.97, "pl_aud": -196000, "delta_quote": 797756, "pl_quote": -130736,
                 "original_cost_pl_aud": -123205, "accum_roll_pl_aud": -72795, "closing_pl_aud": -3784},
                {"product": "AUD/USD", "position": 1, "delta_aud": 1000000,
                 "original_cost": 0.61570, "latest_cost": 0.62797, "current_price": 0.66702,
                 "pl_pct": 8.34, "pl_aud": 58537, "delta_quote": 627974, "pl_quote": 39046,
                 "original_cost_pl_aud": 76939, "accum_roll_pl_aud": -18402, "closing_pl_aud": -3784},
            ],
        },
        "delta": {"futures": -33493506, "ibkr": 0, "fx": 2000000},
        "nlv": {"futures": 7210977, "ibkr": 35799, "fx": 21947898},
        "funding": {"futures": 15800000, "ibkr": 6150000, "fx": 18000000},
        "original_nlv": 39950000,
        "current_nlv": 29194674,
        "vix_cash": 14.95,
        "vix_accum_pl": -2964277,
        "fx_rates": {"AUDUSD": 0.66702},
        "statement": {
            "cash_aud": 3493790.98,
            "cash_usd": 2834202.56,
            "audusd_rate": 0.66680,
            "variation_margin_usd": -355582.50,
            "initial_margin_usd": -2967250.36,
            "nlv_aud": 7210977.63,
        },
    }

    db.add(DailySnapshot(
        report_date=SEED_DATE,
        snapshot_json=json.dumps(snapshot_2025),
        stmt_cash_aud=3_493_790.98,
        stmt_cash_usd=2_834_202.56,
        stmt_variation_margin_usd=-355_582.50,
        stmt_initial_margin_usd=-2_967_250.36,
        stmt_nlv_aud=7_210_977.63,
        stmt_audusd=0.66680,
    ))

    db.commit()
    db.close()
    print(f"✅ Seed complete. Starting state: {SEED_DATE}")
    print("   Futures: CME ES -62 @ 6778.44, CBOT YM -4 @ 48236.00")
    print("   FX3: 2× AUD/USD long")
    print("   Total PL: ($10,755,326)")


if __name__ == "__main__":
    seed()
