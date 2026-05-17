from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import verify_token
from models import FundTransfer

router = APIRouter(prefix="/transfers", tags=["transfers"])

ACCOUNT_LABELS = {
    "external":   "External",
    "futures":    "Macquarie Futures (GAG01)",
    "ibkr":       "IBKR",
    "fx_account": "FX Account",
    "fx1":        "FX1",
    "fx2":        "FX2",
    "fx3":        "FX3",
}


class TransferIn(BaseModel):
    transfer_date: str
    from_account: str
    to_account: str
    amount: float
    currency: str = "AUD"
    fx_rate_to_aud: Optional[float] = None
    amount_aud: Optional[float] = None
    notes: Optional[str] = None


def _row(t: FundTransfer) -> dict:
    return {
        "id": t.id,
        "transfer_date": t.transfer_date,
        "from_account": t.from_account,
        "from_label": ACCOUNT_LABELS.get(t.from_account, t.from_account),
        "to_account": t.to_account,
        "to_label": ACCOUNT_LABELS.get(t.to_account, t.to_account),
        "amount": t.amount,
        "currency": t.currency,
        "fx_rate_to_aud": t.fx_rate_to_aud,
        "amount_aud": t.amount_aud or t.amount,
        "notes": t.notes,
        "created_at": str(t.created_at),
    }


@router.get("")
def list_transfers(
    account: Optional[str] = None,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    q = db.query(FundTransfer).order_by(FundTransfer.transfer_date)
    if account:
        q = q.filter(
            (FundTransfer.from_account == account) | (FundTransfer.to_account == account)
        )
    rows = q.all()
    return [_row(r) for r in rows]


@router.post("")
def add_transfer(
    body: TransferIn,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    # Compute amount_aud if not provided
    amount_aud = body.amount_aud
    if amount_aud is None:
        if body.currency == "AUD":
            amount_aud = body.amount
        elif body.fx_rate_to_aud:
            amount_aud = body.amount * body.fx_rate_to_aud
        else:
            amount_aud = body.amount  # fallback

    t = FundTransfer(
        transfer_date=body.transfer_date,
        from_account=body.from_account,
        to_account=body.to_account,
        amount=body.amount,
        currency=body.currency,
        fx_rate_to_aud=body.fx_rate_to_aud,
        amount_aud=amount_aud,
        notes=body.notes,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _row(t)


@router.delete("/{transfer_id}")
def delete_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    t = db.query(FundTransfer).filter(FundTransfer.id == transfer_id).first()
    if not t:
        raise HTTPException(404, "Transfer not found")
    db.delete(t)
    db.commit()
    return {"deleted": True, "id": transfer_id}
