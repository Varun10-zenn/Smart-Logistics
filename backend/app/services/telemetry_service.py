"""Telemetry service."""
from datetime import datetime, timezone
from typing import List
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.telemetry import TelemetryEvent
from backend.app.models.vehicle import Vehicle
from backend.app.schemas.common import make_page
from backend.app.schemas.telemetry import (
    TelemetryEventCreate, TelemetryBatchCreate, TelemetryEventRead
)
from backend.app.services import safety_service


def _to_read(e: TelemetryEvent) -> TelemetryEventRead:
    return TelemetryEventRead(
        id=e.id,
        vehicle_id=e.vehicle_id,
        delivery_id=e.delivery_id,
        timestamp=e.timestamp,
        latitude=float(e.latitude),
        longitude=float(e.longitude),
        speed_kmh=float(e.speed_kmh),
        soc_percent=float(e.soc_percent) if e.soc_percent is not None else None,
    )


def ingest_event(db: Session, data: TelemetryEventCreate) -> TelemetryEventRead:
    vehicle = db.query(Vehicle).filter(Vehicle.id == data.vehicle_id).first()
    if vehicle is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Vehicle not found.", "details": {}})

    event = TelemetryEvent(
        vehicle_id=data.vehicle_id,
        delivery_id=data.delivery_id,
        timestamp=data.timestamp,
        latitude=data.latitude,
        longitude=data.longitude,
        speed_kmh=data.speed_kmh,
        acceleration_mpss=data.acceleration_ms2 or 0.0,
        soc_percent=data.soc_percent or vehicle.current_soc_percent,
        heading_degrees=data.heading_degrees,
    )
    db.add(event)

    # Update vehicle last telemetry and SoC
    vehicle.last_telemetry_at = data.timestamp
    if data.soc_percent is not None:
        vehicle.current_soc_percent = data.soc_percent

    db.commit()
    db.refresh(event)
    
    if data.delivery_id:
        safety_service.analyze_telemetry(db, event)
        
    return _to_read(event)


def ingest_batch(db: Session, data: TelemetryBatchCreate) -> List[TelemetryEventRead]:
    results = []
    for event_data in data.events:
        results.append(ingest_event(db, event_data))
    return results


def list_events(db: Session, page: int = 1, page_size: int = 20,
                vehicle_id: int = None, delivery_id: int = None,
                from_ts: datetime = None, to_ts: datetime = None):
    q = db.query(TelemetryEvent)
    if vehicle_id:
        q = q.filter(TelemetryEvent.vehicle_id == vehicle_id)
    if delivery_id:
        q = q.filter(TelemetryEvent.delivery_id == delivery_id)
    if from_ts:
        q = q.filter(TelemetryEvent.timestamp >= from_ts)
    if to_ts:
        q = q.filter(TelemetryEvent.timestamp <= to_ts)
    total = q.count()
    events = q.order_by(TelemetryEvent.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_to_read(e) for e in events], total, page, page_size)
