"""
Macquarie Open Position Statement PDF parser.

Extracts:
  - Open positions (product, direction, qty, month, trade price, current price, currency)
  - Market Revaluation (variation margins)
  - Account Financial Summary (cash AUD, cash USD, variation margin, initial margin, NLV, FX rate)
"""

import re
from typing import Optional
import pdfplumber


def parse_macquarie_pdf(pdf_path: str) -> dict:
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    return _parse_text(text)


def parse_macquarie_pdf_bytes(content: bytes) -> dict:
    import io
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return _parse_text(text)


def _parse_text(text: str) -> dict:
    result = {
        "statement_date": _parse_date(text),
        "account": _parse_account(text),
        "positions": _parse_positions(text),
        "variation_margin_usd": None,
        "cash_aud": None,
        "cash_usd": None,
        "initial_margin_usd": None,
        "nlv_aud": None,
        "audusd_rate": None,
        "raw_text": text,
    }
    result.update(_parse_financial_summary(text))
    return result


def _parse_date(text: str) -> Optional[str]:
    # "31st December 2025" or "12th May 2026"
    months = {"January": "01", "February": "02", "March": "03", "April": "04",
              "May": "05", "June": "06", "July": "07", "August": "08",
              "September": "09", "October": "10", "November": "11", "December": "12"}
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)\s+(\w+)\s+(\d{4})", text)
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
        mo = months.get(month)
        if mo:
            return f"{year}-{mo}-{day.zfill(2)}"
    return None


def _parse_account(text: str) -> Optional[str]:
    m = re.search(r"(GAG\d+)", text)
    return m.group(1) if m else None


def _parse_positions(text: str) -> list:
    """
    Parse the Open Position table. Lines look like:
      18DEC25 S 51 MAR26 6778.45 6892.50 USD -290,827.50
    """
    positions = []
    product_code = None
    product_map = {
        "CBT MINI-SIZED DOW": "CBOT YM",
        "CME E-MINI S&P 500": "CME ES",
        "CME E-MINI NASDAQ": "CME NQ",
        "CBOE VIX": "CBOE VIX",
        "CME GOLD": "CMX GC",
    }
    month_map = {"JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
                 "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
                 "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"}

    for line in text.split("\n"):
        # Detect product header
        for key, code in product_map.items():
            if key in line.upper():
                product_code = code
                break

        # Position row: date direction qty month trade_price current_price currency market_rev
        m = re.match(
            r"(\d{2}[A-Z]{3}\d{2})\s+([SB])\s+(\d+)\s+([A-Z]{3}\d{2})\s+"
            r"([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+(USD|AUD|EUR|JPY|HKD|MYR)\s+"
            r"(-?[\d,]+\.?\d*)",
            line.strip(),
        )
        if m and product_code:
            direction = m.group(2)
            qty = int(m.group(3))
            month_str = m.group(4)      # e.g. "MAR26"
            trade_price = float(m.group(5).replace(",", ""))
            current_price = float(m.group(6).replace(",", ""))
            currency = m.group(7)

            # Convert month to YYMM: MAR26 → 2603
            mo_name = month_str[:3]
            yr = month_str[3:]
            mo_num = month_map.get(mo_name, "00")
            contract_month = f"20{yr}{mo_num}"

            signed_qty = -qty if direction == "S" else qty
            positions.append({
                "product_code": product_code,
                "direction": direction,
                "quantity": signed_qty,
                "contract_month": contract_month,
                "trade_price": trade_price,
                "current_price": current_price,
                "currency": currency,
            })

    return positions


def _parse_financial_summary(text: str) -> dict:
    result = {}

    # FX rate: "( 0.66680) ( 1.00000)"
    m = re.search(r"\(\s*([\d.]+)\)\s+\(\s*1\.00000\)", text)
    if m:
        result["audusd_rate"] = float(m.group(1))

    # CASH BALANCE line: three columns AUD | USD | NETT AUD
    m = re.search(r"CASH BALANCE\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)", text)
    if m:
        result["cash_aud"] = float(m.group(1).replace(",", ""))
        result["cash_usd"] = float(m.group(2).replace(",", ""))

    # Variation Margins Futures (USD column)
    m = re.search(r"Variation Margins\s+-\s+Futures\s+[\d,.-]+\s+(-?[\d,]+\.\d+)", text)
    if m:
        result["variation_margin_usd"] = float(m.group(1).replace(",", ""))

    # TOTAL EQUITY (NETT AUD column)
    m = re.search(r"TOTAL EQUITY\s+[\d,.-]+\s+[\d,.-]+\s+([\d,.-]+)", text)
    if m:
        val = m.group(1).replace(",", "")
        result["total_equity_aud"] = float(val)

    # Initial Margins (USD column)
    m = re.search(r"Initial Margins\s+[\d,.-]+\s+(-?[\d,]+\.\d+)", text)
    if m:
        result["initial_margin_usd"] = float(m.group(1).replace(",", ""))

    # Net Liquidating Value (NETT AUD column — third number on the NLV line)
    m = re.search(r"Net Liquidating Value\s+([\d,.-]+)\s+([\d,.-]+)\s+([\d,.-]+)", text)
    if m:
        result["nlv_aud"] = float(m.group(3).replace(",", ""))

    return result
