"""Telemetry router."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.schemas.common import Page
from backend.app.schemas.telemetry import TelemetryEventCreate, TelemetryBatchCreate, TelemetryEventRead
from backend.app.services import telemetry_service

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.post("/events", response_model=TelemetryEventRead, status_code=201)
def ingest_event(
    data: TelemetryEventCreate,
    current_user=Depends(require_role("admin", "fleet_manager", "driver")),
    db: Session = Depends(get_db),
):
    return telemetry_service.ingest_event(db, data)


@router.post("/events/batch", status_code=201)
def ingest_batch(
    data: TelemetryBatchCreate,
    current_user=Depends(require_role("admin", "fleet_manager", "driver")),
    db: Session = Depends(get_db),
):
    results = telemetry_service.ingest_batch(db, data)
    return {"ingested": len(results)}


@router.get("/events", response_model=Page[TelemetryEventRead])
def list_events(
    page: int = 1, page_size: int = 20,
    vehicle_id: Optional[int] = None,
    delivery_id: Optional[int] = None,
    from_ts: Optional[datetime] = None,
    to_ts: Optional[datetime] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    # Drivers see only events for their own vehicles
    if role == "driver" and vehicle_id is None:
        from backend.app.models.delivery import Driver, Delivery
        driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
        if driver:
            delivery = db.query(Delivery).filter(Delivery.driver_id == driver.id).order_by(Delivery.created_at.desc()).first()
            if delivery:
                vehicle_id = delivery.vehicle_id
    return telemetry_service.list_events(db, page, page_size, vehicle_id, delivery_id, from_ts, to_ts)
