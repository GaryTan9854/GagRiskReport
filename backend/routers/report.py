import json
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import verify_token
from services.report_engine import calc_report
from models import DailySnapshot

router = APIRouter(prefix="/report", tags=["report"])


class PriceOverrideRequest(BaseModel):
    prices: dict = {}  # {"CME ES|2603": 7500.0, "AUDUSD": 0.720}


@router.get("/{report_date}")
def get_report(
    report_date: str,
    recalc: bool = False,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    # Return saved snapshot if available (unless recalc is requested)
    if not recalc:
        saved = db.query(DailySnapshot).filter(DailySnapshot.report_date == report_date).first()
        if saved:
            return json.loads(saved.snapshot_json)
    try:
        result = calc_report(db, report_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result


@router.post("/{report_date}/calc")
def calc_with_overrides(
    report_date: str,
    body: PriceOverrideRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    """Recalculate report with price overrides (for what-if / trial calculations)."""
    # Convert flat key format "CME ES|2603" → tuple key for engine
    overrides = {}
    for k, v in body.prices.items():
        if "|" in k:
            parts = k.split("|", 1)
            overrides[(parts[0], parts[1])] = v
        else:
            overrides[k] = v
    try:
        result = calc_report(db, report_date, price_overrides=overrides)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result


@router.post("/{report_date}/save")
def save_snapshot(
    report_date: str,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    """Save today's calculated report as the official daily snapshot."""
    result = calc_report(db, report_date)
    existing = db.query(DailySnapshot).filter(DailySnapshot.report_date == report_date).first()
    snap_json = json.dumps(result)

    stmt = result.get("statement") or {}
    if existing:
        existing.snapshot_json = snap_json
        existing.stmt_cash_aud = stmt.get("cash_aud")
        existing.stmt_cash_usd = stmt.get("cash_usd")
        existing.stmt_variation_margin_usd = stmt.get("variation_margin_usd")
        existing.stmt_initial_margin_usd = stmt.get("initial_margin_usd")
        existing.stmt_nlv_aud = stmt.get("nlv_aud")
        existing.stmt_audusd = stmt.get("audusd_rate")
    else:
        snap = DailySnapshot(
            report_date=report_date,
            snapshot_json=snap_json,
            stmt_cash_aud=stmt.get("cash_aud"),
            stmt_cash_usd=stmt.get("cash_usd"),
            stmt_variation_margin_usd=stmt.get("variation_margin_usd"),
            stmt_initial_margin_usd=stmt.get("initial_margin_usd"),
            stmt_nlv_aud=stmt.get("nlv_aud"),
            stmt_audusd=stmt.get("audusd_rate"),
        )
        db.add(snap)
    db.commit()
    return {"saved": True, "report_date": report_date}


@router.get("/")
def list_snapshots(
    limit: int = Query(30),
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token),
):
    rows = (
        db.query(DailySnapshot.report_date, DailySnapshot.stmt_nlv_aud, DailySnapshot.created_at)
        .order_by(DailySnapshot.report_date.desc())
        .limit(limit)
        .all()
    )
    return [{"report_date": r[0], "nlv_aud": r[1], "created_at": str(r[2])} for r in rows]
