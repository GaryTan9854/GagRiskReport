from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import verify_token
from models import Transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


class TransactionIn(BaseModel):
    entry_date: str
    account: str
    product_code: Optional[str] = None
    contract_month: Optional[str] = None
    position: Optional[float] = None
    entry_price: Optional[float] = None
    currency: Optional[str] = None
    fx_rate_to_aud: Optional[float] = None
    commission: Optional[float] = 0
    gst: Optional[float] = 0
    total_commission: Optional[float] = 0
    is_close_pos: Optional[int] = 0
    cost_price: Optional[float] = None
    close_fx: Optional[float] = None
    multiplier: Optional[float] = None
    price_pl: Optional[float] = 0
    realized_pl_orig: Optional[float] = 0
    realized_pl_aud: Optional[float] = 0
    transaction_type: Optional[str] = "trade"
    notes: Optional[str] = None


@router.get("")
def list_transactions(
    account: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    entry_date: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    limit: int = Query(200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    q = db.query(Transaction)
    if account:
        q = q.filter(Transaction.account == account)
    if year:
        q = q.filter(Transaction.entry_date.startswith(str(year)))
    if entry_date:
        q = q.filter(Transaction.entry_date == entry_date)
    if transaction_type:
        q = q.filter(Transaction.transaction_type == transaction_type)
    q = q.order_by(Transaction.entry_date.desc(), Transaction.id.desc())
    total = q.count()
    rows = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [_serialize(r) for r in rows],
    }


@router.post("")
def create_transaction(
    body: TransactionIn,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    t = Transaction(**body.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return _serialize(t)


@router.put("/{tx_id}")
def update_transaction(
    tx_id: int,
    body: TransactionIn,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    t = db.query(Transaction).get(tx_id)
    if not t:
        raise HTTPException(404, "Transaction not found")
    for k, v in body.model_dump(exclude_none=False).items():
        setattr(t, k, v)
    db.commit()
    return _serialize(t)


@router.delete("/{tx_id}")
def delete_transaction(
    tx_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    t = db.query(Transaction).get(tx_id)
    if not t:
        raise HTTPException(404, "Transaction not found")
    db.delete(t)
    db.commit()
    return {"deleted": True}


@router.get("/roll-trades")
def roll_trades(
    account: Optional[str] = Query("futures"),
    product_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    """
    Identify roll trades: on a given date, a close + open of the same product
    near- and far-month contracts. Returns grouped roll summaries.
    """
    q = db.query(Transaction).filter(Transaction.account == account)
    if product_code:
        q = q.filter(Transaction.product_code == product_code)
    q = q.filter(Transaction.transaction_type == "trade")
    q = q.order_by(Transaction.entry_date, Transaction.id)
    all_txn = q.all()

    # Group by date + product_code
    from collections import defaultdict
    day_product = defaultdict(list)
    for t in all_txn:
        day_product[(t.entry_date, t.product_code)].append(t)

    rolls = []
    for (day, prod), txns in day_product.items():
        closes = [t for t in txns if t.is_close_pos]
        opens = [t for t in txns if not t.is_close_pos]
        if not closes or not opens:
            continue

        total_close_qty = sum(abs(t.position) for t in closes)
        avg_close_price = sum(t.entry_price * abs(t.position) for t in closes) / total_close_qty if total_close_qty else 0
        total_open_qty = sum(abs(t.position) for t in opens)
        avg_open_price = sum(t.entry_price * abs(t.position) for t in opens) / total_open_qty if total_open_qty else 0

        close_month = closes[0].contract_month
        open_month = opens[0].contract_month
        mult = closes[0].multiplier or 1
        close_fx = closes[0].fx_rate_to_aud or 1
        # For short roll: close=buy (position>0), open=sell → P&L = (open-close)×qty×mult
        # For long  roll: close=sell(position<0), open=buy  → P&L = (close-open)×qty×mult
        is_short_roll = closes[0].position is not None and closes[0].position > 0
        # P&L in contract currency (USD for ES/YM)
        gross_pl_usd = (avg_open_price - avg_close_price) * total_close_qty * mult \
            if is_short_roll else \
            (avg_close_price - avg_open_price) * total_close_qty * mult
        # fx_rate_to_aud = AUD per 1 unit of contract currency → multiply to convert
        gross_pl_aud = gross_pl_usd * close_fx if close_fx else 0
        total_commission = sum(t.total_commission or 0 for t in txns)
        net_pl_aud = gross_pl_aud - total_commission
        lots_signed = -total_close_qty if is_short_roll else total_close_qty

        rolls.append({
            "date": day,
            "product": prod,
            "close_month": close_month,
            "open_month": open_month,
            "lots": lots_signed,
            "avg_close_price": round(avg_close_price, 4),
            "avg_open_price": round(avg_open_price, 4),
            "gross_pl_usd": round(gross_pl_usd),
            "gross_pl_aud": round(gross_pl_aud),
            "total_commission": round(total_commission),
            "net_pl_aud": round(net_pl_aud),
            "currency": closes[0].currency,
        })

    return rolls


def _serialize(t: Transaction) -> dict:
    return {
        "id": t.id,
        "entry_date": t.entry_date,
        "account": t.account,
        "product_code": t.product_code,
        "contract_month": t.contract_month,
        "position": t.position,
        "entry_price": t.entry_price,
        "currency": t.currency,
        "fx_rate_to_aud": t.fx_rate_to_aud,
        "commission": t.commission,
        "gst": t.gst,
        "total_commission": t.total_commission,
        "is_close_pos": t.is_close_pos,
        "cost_price": t.cost_price,
        "multiplier": t.multiplier,
        "price_pl": t.price_pl,
        "realized_pl_orig": t.realized_pl_orig,
        "realized_pl_aud": t.realized_pl_aud,
        "transaction_type": t.transaction_type,
        "notes": t.notes,
    }
