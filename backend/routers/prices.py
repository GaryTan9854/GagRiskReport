from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import get_db
from routers.auth import verify_token
from models import PriceDB, FXRate

router = APIRouter(prefix="/prices", tags=["prices"])


class PriceIn(BaseModel):
    trade_date: str
    product_code: str
    contract_month: Optional[str] = None
    price: float
    source: Optional[str] = "manual"


class FXRateIn(BaseModel):
    rate_date: str
    currency: str
    rate: float
    source: Optional[str] = "manual"


@router.get("/{trade_date}")
def get_prices(
    trade_date: str,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    rows = db.query(PriceDB).filter(PriceDB.trade_date == trade_date).all()
    return [{"product_code": r.product_code, "contract_month": r.contract_month,
              "price": r.price, "source": r.source} for r in rows]


@router.post("")
def upsert_price(
    body: PriceIn,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    existing = (
        db.query(PriceDB)
        .filter(PriceDB.trade_date == body.trade_date,
                PriceDB.product_code == body.product_code,
                PriceDB.contract_month == body.contract_month)
        .first()
    )
    if existing:
        existing.price = body.price
        existing.source = body.source
    else:
        db.add(PriceDB(**body.model_dump()))
    db.commit()
    return {"saved": True}


@router.get("/fx/{rate_date}")
def get_fx_rates(
    rate_date: str,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    rows = db.query(FXRate).filter(FXRate.rate_date == rate_date).all()
    return {r.currency: r.rate for r in rows}


@router.post("/fx")
def upsert_fx_rate(
    body: FXRateIn,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    existing = (
        db.query(FXRate)
        .filter(FXRate.rate_date == body.rate_date, FXRate.currency == body.currency)
        .first()
    )
    if existing:
        existing.rate = body.rate
        existing.source = body.source
    else:
        db.add(FXRate(**body.model_dump()))
    db.commit()
    return {"saved": True}
