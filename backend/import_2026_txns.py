"""
Import 2026 transactions from:
  ../2026 GA Global Futures Transactions.xlsx

Run after seed_data.py:
  python import_2026_txns.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, SessionLocal
from models import Transaction
import openpyxl

XLSX_PATH = os.path.join(os.path.dirname(__file__), "..",
                         "2026 GA Global Futures Transactions.xlsx")

ACCOUNT_MAP = {
    "CME ES":   "futures",
    "CBOT YM":  "futures",
    "CME NQ":   "futures",
    "CMX GC":   "futures",
    "CBOE VIX": "futures",
    "Cash AUD": "futures",
    "Cash USD": "futures",
    "SFE AP":   "futures",
    "SGX SSI":  "futures",
    "SGX A50":  "futures",
    "HKE HSI":  "futures",
}

TYPE_MAP = {
    "Cash AUD": "interest",
    "Cash USD": "interest",
}


def _excel_date(val):
    """Convert Excel serial date or datetime to YYYY-MM-DD string."""
    if val is None:
        return None
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    try:
        # Excel serial date
        from datetime import date, timedelta
        delta = timedelta(days=int(val) - 2)
        return (date(1900, 1, 1) + delta).isoformat()
    except Exception:
        return str(val)


def _contract_month(val) -> str | None:
    """Convert contract code like 2603 or 202603 to '2603'."""
    if val is None:
        return None
    s = str(int(val)) if isinstance(val, float) else str(val)
    if len(s) == 4:
        return s  # already YYMM
    if len(s) == 6:
        return s[2:]  # YYYYMM → YYMM
    return s


def import_transactions():
    init_db()
    db = SessionLocal()

    if db.query(Transaction).count() > 0:
        print("Transactions already imported. Skipping.")
        db.close()
        return

    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    ws = wb.active

    # Positional columns (0-indexed):
    # 0:blank  1:EntryDate  2:ProductCode  3:ContractMonth  4:Position  5:EntryPrice
    # 6:Currency  7:ForexRate  8:CommOrInt  9:GST  10:TotalComm  11:isClosePos
    # 12:Cost  13:CloseFX  14:Multiplier  15:PricePL  16:RealPLOrig  17:RealPLAUD
    # 18:Notes

    def _float(v):
        if v is None or v is True or v is False:
            return float(v) if isinstance(v, bool) else None
        try:
            return float(v)
        except Exception:
            return None

    added = 0
    for row in ws.iter_rows(values_only=True):
        if not row or row[1] is None:
            continue

        entry_date = _excel_date(row[1])
        if not entry_date:
            continue

        product_code = str(row[2] or '').strip()
        if not product_code:
            continue

        # Normalize product code (handle typos like "Cash aUD")
        product_code_upper = product_code.upper()
        for key in ACCOUNT_MAP:
            if key.upper() == product_code_upper:
                product_code = key
                break

        account = ACCOUNT_MAP.get(product_code, 'futures')
        tx_type = TYPE_MAP.get(product_code, 'trade')

        notes_raw = str(row[18] or '').strip()
        if 'Interest' in notes_raw or 'interest' in notes_raw:
            tx_type = 'interest'
        elif 'Fee' in notes_raw or 'fee' in notes_raw:
            tx_type = 'fee'

        is_close = 1 if row[11] is True else 0
        contract_month = _contract_month(row[3])

        t = Transaction(
            entry_date=entry_date,
            account=account,
            product_code=product_code,
            contract_month=contract_month,
            position=_float(row[4]),
            entry_price=_float(row[5]),
            currency=str(row[6] or '').strip() or None,
            fx_rate_to_aud=_float(row[7]),
            commission=_float(row[8]),
            gst=_float(row[9]),
            total_commission=_float(row[10]),
            is_close_pos=is_close,
            cost_price=_float(row[12]),
            close_fx=_float(row[13]),
            multiplier=_float(row[14]),
            price_pl=_float(row[15]),
            realized_pl_orig=_float(row[16]),
            realized_pl_aud=_float(row[17]),
            transaction_type=tx_type,
            notes=notes_raw or None,
        )
        db.add(t)
        added += 1

    db.commit()
    db.close()
    print(f"✅ Imported {added} transactions from 2026 xlsx")


if __name__ == "__main__":
    import_transactions()
