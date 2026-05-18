"""
PDF import endpoint: upload Macquarie daily statement, update prices, FX rates,
cash balances, and statement fields in the snapshot.
"""

import json
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import verify_token
from models import PriceDB, FXRate, CashBalance, DailySnapshot
from services.pdf_parser import parse_macquarie_pdf_bytes
from services.report_engine import calc_report

router = APIRouter(prefix="/import", tags=["import"])

# Directory where yearly statement PDFs live (DDMMF.pdf naming convention)
STMT_PDF_DIR = os.getenv(
    "STMT_PDF_DIR",
    os.path.join(os.path.expanduser("~"), "gagrisk-stmts"),
)


def _date_to_stmt_path(report_date: str):
    """
    Convert '2026-MM-DD' → '<STMT_PDF_DIR>/2026/DDMMF.pdf'
    Returns None if no matching file found.
    """
    try:
        year, month, day = report_date.split("-")
    except ValueError:
        return None
    filename = f"{day}{month}F.pdf"
    path = os.path.join(STMT_PDF_DIR, year, filename)
    return path if os.path.isfile(path) else None


@router.get("/stmt/{report_date}")
def get_stmt_pdf(
    report_date: str,
    _: dict = Depends(verify_token),
):
    """Serve the raw Macquarie statement PDF for a given date."""
    path = _date_to_stmt_path(report_date)
    if not path:
        raise HTTPException(404, f"No statement PDF found for {report_date}")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"GAGStmt_{report_date}.pdf",
    )


def _date_from_filename(filename: str):
    """
    Parse date from Macquarie filename format DDMMF.pdf → '2026-MM-DD'.
    e.g. '1505F.pdf' → '2026-05-15'
    Returns None if format doesn't match.
    """
    import re
    m = re.match(r"^(\d{2})(\d{2})F\.pdf$", filename, re.IGNORECASE)
    if m:
        day, month = m.group(1), m.group(2)
        return f"2026-{month}-{day}"
    return None


@router.post("/pdf")
async def import_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    content = await file.read()
    try:
        parsed = parse_macquarie_pdf_bytes(content)
    except Exception as e:
        raise HTTPException(400, f"PDF parse error: {e}")

    report_date = parsed.get("statement_date")
    # Fallback: derive date from filename (DDMMF.pdf format)
    if not report_date and file.filename:
        report_date = _date_from_filename(file.filename)
        if report_date:
            parsed["statement_date"] = report_date
    if not report_date:
        raise HTTPException(400, "Could not determine statement date from PDF")

    audusd = parsed.get("audusd_rate")

    # ── Save prices ────────────────────────────────────────────────────────────
    for pos in parsed.get("positions", []):
        _upsert_price(db, report_date, pos["product_code"], pos["contract_month"],
                      pos["current_price"], source="pdf")

    # ── Save FX rate ────────────────────────────────────────────────────────────
    if audusd:
        _upsert_fx(db, report_date, "USD", audusd, source="pdf")

    # ── Save cash balances ─────────────────────────────────────────────────────
    if parsed.get("cash_aud") is not None:
        _upsert_cash(db, report_date, "futures", "AUD", parsed["cash_aud"])
    if parsed.get("cash_usd") is not None:
        _upsert_cash(db, report_date, "futures", "USD", parsed["cash_usd"])

    db.commit()

    # ── Calculate and save snapshot ────────────────────────────────────────────
    report = calc_report(db, report_date)
    report["statement"] = {
        "cash_aud": parsed.get("cash_aud"),
        "cash_usd": parsed.get("cash_usd"),
        "audusd_rate": audusd,
        "variation_margin_usd": parsed.get("variation_margin_usd"),
        "initial_margin_usd": parsed.get("initial_margin_usd"),
        "nlv_aud": parsed.get("nlv_aud"),
    }

    existing = db.query(DailySnapshot).filter(DailySnapshot.report_date == report_date).first()
    snap_json = json.dumps(report)
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

    return {
        "report_date": report_date,
        "positions_found": len(parsed.get("positions", [])),
        "audusd": audusd,
        "nlv_aud": parsed.get("nlv_aud"),
        "report": report,
    }


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
