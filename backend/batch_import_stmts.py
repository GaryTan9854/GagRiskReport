"""
Batch import all Macquarie statement PDFs from a directory.

Filename format: DDMMF.pdf  (e.g. 0104F.pdf = April 1, 2026)

Usage (run from backend/ directory):
    python batch_import_stmts.py /path/to/GAGStmt/2026/
    python batch_import_stmts.py /path/to/GAGStmt/2026/ --dry-run
    python batch_import_stmts.py /path/to/GAGStmt/2026/ --date 2026-04-01  # single date
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path

# Make sure we can import from the backend package
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, init_db
from models import PriceDB, FXRate, CashBalance, DailySnapshot
from services.pdf_parser import parse_macquarie_pdf
from services.report_engine import calc_report


def filename_to_date(fname: str):
    """
    Convert DDMMF.pdf → '2026-MM-DD'.
    Returns None if the filename doesn't match.
    """
    m = re.match(r'^(\d{2})(\d{2})F\.pdf$', fname, re.IGNORECASE)
    if not m:
        return None
    day, month = m.group(1), m.group(2)
    return f"2026-{month}-{day}"


def _upsert_price(db, date, product_code, contract_month, price, source="pdf"):
    existing = (
        db.query(PriceDB)
        .filter(PriceDB.trade_date == date, PriceDB.product_code == product_code,
                PriceDB.contract_month == contract_month)
        .first()
    )
    if existing:
        existing.price = price
        existing.source = source
    else:
        db.add(PriceDB(trade_date=date, product_code=product_code,
                       contract_month=contract_month, price=price, source=source))
        db.flush()  # make new row visible to subsequent queries in same session


def _upsert_fx(db, date, currency, rate, source="pdf"):
    existing = db.query(FXRate).filter(FXRate.rate_date == date, FXRate.currency == currency).first()
    if existing:
        existing.rate = rate
        existing.source = source
    else:
        db.add(FXRate(rate_date=date, currency=currency, rate=rate, source=source))


def _upsert_cash(db, date, account, currency, amount):
    existing = (
        db.query(CashBalance)
        .filter(CashBalance.balance_date == date, CashBalance.account == account,
                CashBalance.currency == currency)
        .first()
    )
    if existing:
        existing.amount = amount
    else:
        db.add(CashBalance(balance_date=date, account=account, currency=currency, amount=amount))


def process_pdf(db, pdf_path: str, report_date: str, dry_run: bool = False):
    """Parse one PDF and upsert all its data into the DB."""
    try:
        parsed = parse_macquarie_pdf(pdf_path)
    except Exception as e:
        return False, f"Parse error: {e}"

    # Validate the parsed date matches the filename date (warn if mismatch)
    parsed_date = parsed.get("statement_date")
    if parsed_date and parsed_date != report_date:
        print(f"  ⚠  Filename date {report_date} ≠ PDF date {parsed_date}  (using PDF date)")
        report_date = parsed_date

    audusd = parsed.get("audusd_rate")
    positions = parsed.get("positions", [])

    if dry_run:
        nlv = parsed.get("nlv_aud")
        return True, f"DRY RUN — {len(positions)} positions, AUDUSD={audusd}, NLV={nlv}"

    # ── Prices ────────────────────────────────────────────────────────────────
    for pos in positions:
        _upsert_price(db, report_date, pos["product_code"], pos["contract_month"],
                      pos["current_price"], source="pdf")

    # ── FX rate ───────────────────────────────────────────────────────────────
    if audusd:
        _upsert_fx(db, report_date, "USD", audusd, source="pdf")

    # ── Cash balances ─────────────────────────────────────────────────────────
    if parsed.get("cash_aud") is not None:
        _upsert_cash(db, report_date, "futures", "AUD", parsed["cash_aud"])
    if parsed.get("cash_usd") is not None:
        _upsert_cash(db, report_date, "futures", "USD", parsed["cash_usd"])

    db.commit()

    # ── Calc report + save snapshot ───────────────────────────────────────────
    report = calc_report(db, report_date)
    report["statement"] = {
        "cash_aud": parsed.get("cash_aud"),
        "cash_usd": parsed.get("cash_usd"),
        "audusd_rate": audusd,
        "variation_margin_usd": parsed.get("variation_margin_usd"),
        "initial_margin_usd": parsed.get("initial_margin_usd"),
        "nlv_aud": parsed.get("nlv_aud"),
    }

    snap_json = json.dumps(report)
    existing = db.query(DailySnapshot).filter(DailySnapshot.report_date == report_date).first()
    if existing:
        existing.snapshot_json = snap_json
        existing.stmt_cash_aud = parsed.get("cash_aud")
        existing.stmt_cash_usd = parsed.get("cash_usd")
        existing.stmt_variation_margin_usd = parsed.get("variation_margin_usd")
        existing.stmt_initial_margin_usd = parsed.get("initial_margin_usd")
        existing.stmt_nlv_aud = parsed.get("nlv_aud")
        existing.stmt_audusd = audusd
    else:
        db.add(DailySnapshot(
            report_date=report_date,
            snapshot_json=snap_json,
            stmt_cash_aud=parsed.get("cash_aud"),
            stmt_cash_usd=parsed.get("cash_usd"),
            stmt_variation_margin_usd=parsed.get("variation_margin_usd"),
            stmt_initial_margin_usd=parsed.get("initial_margin_usd"),
            stmt_nlv_aud=parsed.get("nlv_aud"),
            stmt_audusd=audusd,
        ))
    db.commit()

    nlv = parsed.get("nlv_aud")
    return True, f"{len(positions)} positions, AUDUSD={audusd}, NLV AUD={nlv}"


def main():
    parser = argparse.ArgumentParser(description="Batch import Macquarie statement PDFs")
    parser.add_argument("dir", help="Directory containing *F.pdf files")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, don't write to DB")
    parser.add_argument("--date", help="Process only this date (YYYY-MM-DD)")
    args = parser.parse_args()

    pdf_dir = Path(args.dir)
    if not pdf_dir.is_dir():
        print(f"ERROR: {pdf_dir} is not a directory")
        sys.exit(1)

    init_db()
    db = SessionLocal()

    # Collect and sort PDFs
    files = sorted(pdf_dir.glob("*F.pdf"))
    if not files:
        print("No *F.pdf files found.")
        sys.exit(0)

    ok = 0
    fail = 0

    print(f"Found {len(files)} PDFs in {pdf_dir}")
    if args.dry_run:
        print("DRY RUN mode — no writes to DB\n")

    for pdf_path in files:
        report_date = filename_to_date(pdf_path.name)
        if report_date is None:
            print(f"  ⚠  Skipping unrecognised filename: {pdf_path.name}")
            continue

        # Filter by --date if specified
        if args.date and report_date != args.date:
            continue

        success, msg = process_pdf(db, str(pdf_path), report_date, dry_run=args.dry_run)
        icon = "✓" if success else "✗"
        print(f"  {icon}  {report_date}  ({pdf_path.name})  →  {msg}")
        if success:
            ok += 1
        else:
            fail += 1

    db.close()
    print(f"\n{'DRY RUN ' if args.dry_run else ''}Done: {ok} ok, {fail} failed")


if __name__ == "__main__":
    main()
