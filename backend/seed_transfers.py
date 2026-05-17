"""
One-time script: seed historical fund transfers.
Run: DB_PATH=/Users/gary/db/gagrisk/gag_risk.db venv/bin/python seed_transfers.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from database import SessionLocal, init_db
from models import FundTransfer

TRANSFERS = [
    # ── Macquarie Futures (GAG01) — external injections ──────────────────────
    ("2012-12-12", "external", "futures", 1_000_000, "AUD", "Capital injection"),
    ("2015-01-29", "external", "futures",   500_000, "AUD", "Capital injection"),
    ("2015-02-02", "external", "futures",   500_000, "AUD", "Capital injection"),
    ("2016-07-22", "external", "futures", 1_000_000, "AUD", "Capital injection"),
    ("2016-12-13", "external", "futures", 1_000_000, "AUD", "Capital injection"),
    ("2017-09-20", "external", "futures", 1_000_000, "AUD", "Capital injection"),
    ("2017-09-25", "external", "futures",   500_000, "AUD", "Capital injection"),
    ("2017-10-09", "external", "futures",   500_000, "AUD", "Capital injection"),
    ("2018-10-04", "external", "futures", 1_000_000, "AUD", "Capital injection"),
    ("2019-05-06", "external", "futures",   400_000, "AUD", "Capital injection"),
    ("2019-07-03", "external", "futures", 1_000_000, "AUD", "Capital injection"),
    ("2020-01-27", "external", "futures",   960_000, "AUD", "Capital injection"),
    ("2020-03-10", "external", "futures", 1_640_000, "AUD", "Capital injection (0.8M + 0.84M)"),
    ("2020-05-29", "external", "futures",10_000_000, "AUD", "Capital injection"),
    # ── IBKR — external injections ───────────────────────────────────────────
    ("2020-07-01", "external", "ibkr",    2_000_000, "AUD", "Capital injection (approx date)"),
    ("2020-09-04", "external", "ibkr",    2_000_000, "AUD", "Capital injection"),
    ("2021-01-22", "external", "ibkr",    1_000_000, "AUD", "Capital injection"),
    ("2021-03-03", "external", "ibkr",    1_000_000, "AUD", "Capital injection"),
    ("2021-03-04", "external", "ibkr",    1_000_000, "AUD", "Capital injection"),
    ("2022-01-31", "external", "ibkr",    1_000_000, "AUD", "Capital injection"),
    ("2022-06-21", "ibkr",    "external",    50_000, "AUD", "Withdrawal"),
    # ── FX Account — external injection + internal movements ─────────────────
    ("2020-06-01", "external",    "fx_account", 21_000_000, "AUD", "FX Fund total capital (approx date)"),
    ("2020-06-15", "fx_account",  "futures",    10_000_000, "AUD", "Internal: FX Fund → Macquarie Futures margin support"),
    ("2026-05-11", "fx_account",  "futures",     3_000_000, "AUD", "Internal: FX Account → Macquarie Futures margin top-up"),
]

def main():
    init_db()
    db = SessionLocal()
    added = 0
    for date, frm, to, amount, ccy, notes in TRANSFERS:
        db.add(FundTransfer(
            transfer_date=date,
            from_account=frm,
            to_account=to,
            amount=amount,
            currency=ccy,
            amount_aud=amount,   # all AUD here
            notes=notes,
        ))
        added += 1
    db.commit()
    db.close()
    print(f"Inserted {added} fund transfers.")

if __name__ == "__main__":
    main()
