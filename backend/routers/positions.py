from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import verify_token
from models import Position

router = APIRouter(prefix="/positions", tags=["positions"])


class PositionIn(BaseModel):
    account: str
    product_code: str
    contract_month: Optional[str] = None
    position: float
    entry_price: float
    latest_cost: Optional[float] = None
    currency: Optional[str] = None
    multiplier: Optional[float] = None
    open_date: Optional[str] = None
    accumulated_roll_pl_orig: Optional[float] = 0
    notes: Optional[str] = None


class FXRollIn(BaseModel):
    new_latest_cost: float
    roll_pl_usd: float  # P&L captured in this roll (in USD)


@router.get("")
def list_positions(
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    rows = db.query(Position).filter(Position.is_active == 1).all()
    return [_serialize(r) for r in rows]


@router.post("")
def create_position(
    body: PositionIn,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    p = Position(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return _serialize(p)


@router.put("/{pos_id}")
def update_position(
    pos_id: int,
    body: PositionIn,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    p = db.query(Position).get(pos_id)
    if not p:
        raise HTTPException(404, "Position not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    db.commit()
    return _serialize(p)


@router.post("/{pos_id}/close")
def close_position(
    pos_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    p = db.query(Position).get(pos_id)
    if not p:
        raise HTTPException(404, "Position not found")
    p.is_active = 0
    db.commit()
    return {"closed": True}


@router.post("/{pos_id}/fx-roll")
def fx_roll(
    pos_id: int,
    body: FXRollIn,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    """Update FX position latest_cost after a roll and accumulate roll P&L."""
    p = db.query(Position).get(pos_id)
    if not p:
        raise HTTPException(404, "Position not found")
    p.accumulated_roll_pl_orig = (p.accumulated_roll_pl_orig or 0) + body.roll_pl_usd
    p.latest_cost = body.new_latest_cost
    db.commit()
    return _serialize(p)


def _serialize(p: Position) -> dict:
    return {
        "id": p.id,
        "account": p.account,
        "product_code": p.product_code,
        "contract_month": p.contract_month,
        "position": p.position,
        "entry_price": p.entry_price,
        "latest_cost": p.latest_cost,
        "currency": p.currency,
        "multiplier": p.multiplier,
        "open_date": p.open_date,
        "accumulated_roll_pl_orig": p.accumulated_roll_pl_orig,
        "is_active": p.is_active,
        "notes": p.notes,
    }
