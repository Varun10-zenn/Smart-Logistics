"""
Charging service — includes the atomic reservation transaction.

CRITICAL: create_reservation uses SELECT FOR UPDATE + overlap validation
inside a single DB transaction to prevent double-booking.
"""
import math
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.app.models.charging import (
    ChargingStation, ChargingConnector, ChargingSlot,
    ChargingReservation, ChargingSession,
    has_charging_reservation_overlap,
)
from backend.app.schemas.common import make_page
from backend.app.schemas.charging import (
    StationCreate, StationRead, StationUpdate,
    ConnectorCreate, ConnectorUpdate, ConnectorRead,
    SlotCreate, SlotRead,
    ChargingRecommendRequest, ChargingRecommendResponse,
    ReservationCreate, ReservationRead,
    SessionRead,
)


# MySQL InnoDB reports lock waits/deadlocks as OperationalError (1205/1213);
# PostgreSQL reports them as psycopg2 errors (40P01/55P03). Both are expected
# contention, not server faults, so surface them as 409 instead of 500.
_LOCK_CONTENTION_CODES = {1205, 1213, "40P01", "55P03", "40001"}


def _commit_or_conflict(db: Session) -> None:
    """Commit, translating lock-wait/deadlock contention into HTTP 409."""
    try:
        db.commit()
    except OperationalError as err:
        db.rollback()
        code = getattr(getattr(err, "orig", None), "args", (None,))[0]
        if code in _LOCK_CONTENTION_CODES or str(code) in _LOCK_CONTENTION_CODES:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "CONFLICT",
                    "message": "Charging reservation conflicted with a concurrent operation. Please retry.",
                    "details": {},
                },
            )
        raise


# ---------------------------------------------------------------------------
# Stations
# ---------------------------------------------------------------------------
def _station_read(s: ChargingStation) -> StationRead:
    return StationRead(
        id=s.id, station_code=s.station_code, name=s.name,
        latitude=float(s.latitude), longitude=float(s.longitude),
        total_connectors=s.total_connectors, status=s.status,
    )


def list_stations(db: Session, page: int = 1, page_size: int = 20, status: str = None):
    q = db.query(ChargingStation)
    if status:
        q = q.filter(ChargingStation.status == status)
    total = q.count()
    stations = q.offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_station_read(s) for s in stations], total, page, page_size)


def create_station(db: Session, data: StationCreate) -> StationRead:
    existing = db.query(ChargingStation).filter(ChargingStation.station_code == data.station_code).first()
    if existing:
        raise HTTPException(status_code=409, detail={"code": "DUPLICATE_RESOURCE", "message": "Station code already exists.", "details": {}})
    station = ChargingStation(
        station_code=data.station_code, name=data.name,
        latitude=data.latitude, longitude=data.longitude,
        total_connectors=data.total_connectors, status=data.status,
    )
    db.add(station)
    db.commit()
    db.refresh(station)
    return _station_read(station)


def get_station(db: Session, station_id: int) -> StationRead:
    s = db.query(ChargingStation).filter(ChargingStation.id == station_id).first()
    if s is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Charging station not found.", "details": {}})
    return _station_read(s)


def update_station(db: Session, station_id: int, data: StationUpdate) -> StationRead:
    s = db.query(ChargingStation).filter(ChargingStation.id == station_id).first()
    if s is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Charging station not found.", "details": {}})
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    return _station_read(s)


def delete_station(db: Session, station_id: int) -> None:
    s = db.query(ChargingStation).filter(ChargingStation.id == station_id).first()
    if s is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Charging station not found.", "details": {}})

    # 409 when deleting a station with reservations
    active_res = (
        db.query(ChargingReservation)
        .join(ChargingSlot, ChargingReservation.slot_id == ChargingSlot.id)
        .join(ChargingConnector, ChargingSlot.connector_id == ChargingConnector.id)
        .filter(ChargingConnector.station_id == station_id, ChargingReservation.status.in_(["confirmed", "active"]))
        .first()
    )
    if active_res:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": "Cannot delete charging station with active reservations.", "details": {}}
        )

    db.delete(s)
    db.commit()


# ---------------------------------------------------------------------------
# Connectors
# ---------------------------------------------------------------------------
def list_connectors(db: Session, page: int = 1, page_size: int = 20,
                    station_id: int = None, status: str = None):
    q = db.query(ChargingConnector)
    if station_id:
        q = q.filter(ChargingConnector.station_id == station_id)
    if status:
        q = q.filter(ChargingConnector.status == status)
    total = q.count()
    connectors = q.offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_connector_read(c) for c in connectors], total, page, page_size)


def _connector_read(c: ChargingConnector) -> ConnectorRead:
    return ConnectorRead(
        id=c.id, station_id=c.station_id, connector_number=c.connector_number,
        connector_type=c.connector_type, max_power_kw=float(c.max_power_kw), status=c.status,
    )


def create_connector(db: Session, station_id: int, data: ConnectorCreate) -> ConnectorRead:
    st = db.query(ChargingStation).filter(ChargingStation.id == station_id).first()
    if not st:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Charging station not found.", "details": {}})

    num = data.connector_number
    if not num:
        max_num = db.query(ChargingConnector).filter(ChargingConnector.station_id == station_id).count()
        num = max_num + 1

    connector = ChargingConnector(
        station_id=station_id,
        connector_number=num,
        connector_type=data.connector_type,
        max_power_kw=data.max_power_kw,
        status=data.status
    )
    db.add(connector)
    db.commit()
    db.refresh(connector)
    return _connector_read(connector)


def update_connector(db: Session, connector_id: int, data: ConnectorUpdate) -> ConnectorRead:
    conn = db.query(ChargingConnector).filter(ChargingConnector.id == connector_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Charging connector not found.", "details": {}})

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(conn, field, val)

    db.commit()
    db.refresh(conn)
    return _connector_read(conn)


def delete_connector(db: Session, connector_id: int) -> None:
    conn = db.query(ChargingConnector).filter(ChargingConnector.id == connector_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Charging connector not found.", "details": {}})

    # 409 when deleting a connector with active reservations
    active_res = (
        db.query(ChargingReservation)
        .join(ChargingSlot, ChargingReservation.slot_id == ChargingSlot.id)
        .filter(ChargingSlot.connector_id == connector_id, ChargingReservation.status.in_(["confirmed", "active"]))
        .first()
    )
    if active_res:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": "Cannot delete charging connector with active reservations.", "details": {}}
        )

    db.delete(conn)
    db.commit()


# ---------------------------------------------------------------------------
# Slots & Rolling Scheduler
# ---------------------------------------------------------------------------
def _slot_read(s: ChargingSlot) -> SlotRead:
    return SlotRead(
        id=s.id, connector_id=s.connector_id,
        start_time=s.start_time, end_time=s.end_time, is_booked=s.is_booked,
    )


def list_slots(db: Session, page: int = 1, page_size: int = 20,
               connector_id: int = None, available_only: bool = False):
    q = db.query(ChargingSlot)
    if connector_id:
        q = q.filter(ChargingSlot.connector_id == connector_id)
    if available_only:
        q = q.filter(ChargingSlot.is_booked == False)
    total = q.count()
    slots = q.order_by(ChargingSlot.start_time.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_slot_read(s) for s in slots], total, page, page_size)


def create_slot(db: Session, connector_id: int, data: SlotCreate) -> SlotRead:
    conn = db.query(ChargingConnector).filter(ChargingConnector.id == connector_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Charging connector not found.", "details": {}})

    if data.start_time >= data.end_time:
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "start_time must be before end_time.", "details": {}})

    # Check slot overlap
    overlap = db.query(ChargingSlot).filter(
        ChargingSlot.connector_id == connector_id,
        ChargingSlot.start_time < data.end_time,
        ChargingSlot.end_time > data.start_time
    ).first()
    if overlap:
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": "Charging slot overlaps with an existing slot.", "details": {}})

    slot = ChargingSlot(
        connector_id=connector_id,
        start_time=data.start_time,
        end_time=data.end_time,
        is_booked=False
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return _slot_read(slot)


def generate_slots(db: Session, connector_id: int, slot_minutes: int = 60, hours_ahead: int = 24) -> list[SlotRead]:
    conn = db.query(ChargingConnector).filter(ChargingConnector.id == connector_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Charging connector not found.", "details": {}})

    from datetime import timedelta
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    end_target = now + timedelta(hours=hours_ahead)

    created_slots = []
    curr = now
    slot_delta = timedelta(minutes=slot_minutes)

    while curr < end_target:
        slot_end = curr + slot_delta
        # Check overlap
        overlap = db.query(ChargingSlot).filter(
            ChargingSlot.connector_id == connector_id,
            ChargingSlot.start_time < slot_end,
            ChargingSlot.end_time > curr
        ).first()

        if not overlap:
            s = ChargingSlot(connector_id=connector_id, start_time=curr, end_time=slot_end, is_booked=False)
            db.add(s)
            created_slots.append(s)

        curr = slot_end

    db.commit()
    for s in created_slots:
        db.refresh(s)
    return [_slot_read(s) for s in created_slots]


def generate_depot_chargers(
    db: Session,
    warehouse_id: int,
    connectors_count: int = 2,
    max_power_kw: float = 50.0,
    price_per_kwh: float = 0.0,
) -> ChargingStation:
    """
    Creates or retrieves the depot station for a warehouse, ensuring it has at least connectors_count.
    """
    from backend.app.models.warehouse import Warehouse
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not wh:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Warehouse #{warehouse_id} not found.", "details": {}},
        )

    station_code = f"DEPOT-{wh.code.upper()}"
    station = db.query(ChargingStation).filter(ChargingStation.station_code == station_code).first()

    if not station:
        station = ChargingStation(
            station_code=station_code,
            name=f"{wh.name} Depot Chargers",
            latitude=wh.latitude,
            longitude=wh.longitude,
            total_connectors=connectors_count,
            status="operational",
            warehouse_id=wh.id,
            is_depot=True,
        )
        db.add(station)
        db.flush()

    existing_connectors = (
        db.query(ChargingConnector)
        .filter(ChargingConnector.station_id == station.id)
        .all()
    )
    existing_count = len(existing_connectors)

    if existing_count < connectors_count:
        for i in range(existing_count + 1, connectors_count + 1):
            conn = ChargingConnector(
                station_id=station.id,
                connector_number=i,
                connector_type="CCS2",
                max_power_kw=max_power_kw,
                price_per_kwh=price_per_kwh,
                status="available",
            )
            db.add(conn)
            db.flush()
            generate_slots(db, conn.id, slot_minutes=60, hours_ahead=24)

    station.total_connectors = max(station.total_connectors, connectors_count)
    db.commit()
    db.refresh(station)
    return station


def auto_reserve_depot_charging(db: Session, vehicle_id: int) -> Optional[ChargingReservation]:
    """
    Finds earliest free compatible slot at the vehicle's store depot station and books it atomically.
    Returns reservation if successful, None otherwise.
    """
    from backend.app.models.vehicle import Vehicle
    from backend.app.models.user import User

    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not v or not v.warehouse_id:
        return None

    depot_station = (
        db.query(ChargingStation)
        .filter(ChargingStation.warehouse_id == v.warehouse_id, ChargingStation.is_depot == True)
        .first()
    )
    if not depot_station:
        depot_station = generate_depot_chargers(db, v.warehouse_id, connectors_count=2)

    # Filter compatible connectors
    veh_conn_type = v.connector_type or "CCS2"
    connectors = (
        db.query(ChargingConnector)
        .filter(
            ChargingConnector.station_id == depot_station.id,
            ChargingConnector.status != "offline",
            ChargingConnector.status != "maintenance",
            ChargingConnector.connector_type == veh_conn_type,
        )
        .all()
    )
    if not connectors:
        # Fallback to any connector if type mismatch
        connectors = (
            db.query(ChargingConnector)
            .filter(
                ChargingConnector.station_id == depot_station.id,
                ChargingConnector.status != "offline",
                ChargingConnector.status != "maintenance",
            )
            .all()
        )

    if not connectors:
        return None

    # 0) Idempotency check: if an active reservation already exists for this vehicle, return it
    existing_res = (
        db.query(ChargingReservation)
        .filter(
            ChargingReservation.vehicle_id == v.id,
            ChargingReservation.status.in_(["confirmed", "active"])
        )
        .order_by(ChargingReservation.created_at.desc())
        .first()
    )
    if existing_res:
        return existing_res

    now = datetime.utcnow()

    # Find driver assigned to active delivery of this vehicle or any active store driver
    from backend.app.models.delivery import Delivery, Driver
    active_delivery = (
        db.query(Delivery)
        .filter(Delivery.vehicle_id == v.id, Delivery.status.in_(["assigned", "in_transit", "out_for_delivery"]))
        .first()
    )
    driver_id = None
    if active_delivery and active_delivery.driver_id:
        driver_id = active_delivery.driver_id
    else:
        driver = (
            db.query(Driver)
            .filter(Driver.warehouse_id == v.warehouse_id, Driver.status.in_(["available", "busy"]))
            .order_by(Driver.id.asc())
            .first()
        )
        if driver:
            driver_id = driver.id

    if not driver_id:
        # If no driver exists for the store yet, fetch any registered driver or raise clean error
        first_driver = db.query(Driver).order_by(Driver.id.asc()).first()
        if first_driver:
            driver_id = first_driver.id
        else:
            return None

    for c in connectors:
        maintain_rolling_slots(db, connector_id=c.id)
        slots = (
            db.query(ChargingSlot)
            .filter(
                ChargingSlot.connector_id == c.id,
                ChargingSlot.is_booked == False,
                ChargingSlot.end_time > now,
            )
            .order_by(ChargingSlot.start_time.asc())
            .all()
        )
        for slot in slots:
            try:
                res_create = ReservationCreate(
                    slot_id=slot.id,
                    vehicle_id=v.id,
                    driver_id=driver_id,
                )
                res_read = create_reservation(db, res_create)
                res_obj = db.query(ChargingReservation).filter(ChargingReservation.id == res_read.id).first()
                if res_obj and active_delivery:
                    res_obj.delivery_id = active_delivery.id
                    db.commit()
                return res_obj
            except HTTPException as ex:
                if ex.status_code == 409:
                    continue
                raise
    return None


def maintain_rolling_slots(db: Session, connector_id: Optional[int] = None):
    """
    Scheduler helper: keeps rolling slots up to CHARGING_SLOT_HORIZON_HOURS
    for active connectors. Never creates overlapping slots; never deletes booked slots.
    """
    from backend.app.core.config import settings
    horizon_hours = getattr(settings, "CHARGING_SLOT_HORIZON_HOURS", 24)

    q = db.query(ChargingConnector).filter(ChargingConnector.status != "offline")
    if connector_id:
        q = q.filter(ChargingConnector.id == connector_id)
    connectors = q.all()

    for c in connectors:
        generate_slots(db, c.id, slot_minutes=60, hours_ahead=horizon_hours)


# ---------------------------------------------------------------------------
# Charging Recommendation (deterministic stub)
# ---------------------------------------------------------------------------
from backend.app.services.ev_charging_optimization_service import optimize_charging

def recommend_charging(db: Session, data: ChargingRecommendRequest) -> ChargingRecommendResponse:
    return optimize_charging(db, data)


# ---------------------------------------------------------------------------
# Reservations (ATOMIC — critical path)
# ---------------------------------------------------------------------------
def _reservation_read(r: ChargingReservation) -> ReservationRead:
    driver_name = None
    if r.driver and r.driver.user:
        driver_name = r.driver.user.full_name
    vehicle_code = r.vehicle.registration_number if r.vehicle else None
    station_name = None
    connector_code = None
    if r.slot and r.slot.connector:
        connector_code = f"Connector #{r.slot.connector.connector_number}"
        if r.slot.connector.station:
            station_name = r.slot.connector.station.name

    slot_time_range = None
    if r.start_time and r.end_time:
        slot_time_range = f"{r.start_time.strftime('%I:%M %p')} - {r.end_time.strftime('%I:%M %p')}"

    return ReservationRead(
        id=r.id, reservation_code=r.reservation_code,
        slot_id=r.slot_id, vehicle_id=r.vehicle_id,
        driver_id=r.driver_id, delivery_id=r.delivery_id,
        start_time=r.start_time, end_time=r.end_time,
        status=r.status, created_at=r.created_at,
        driver_name=driver_name,
        vehicle_code=vehicle_code,
        station_name=station_name,
        connector_code=connector_code,
        slot_time_range=slot_time_range,
    )


def create_reservation(db: Session, data: ReservationCreate) -> ReservationRead:
    """
    ATOMIC reservation creation:
    1. Lock the connector row (serializes every booking on this connector)
    2. SELECT slot FOR UPDATE + check is_booked
    3. Call overlap validation
    4. Create reservation + mark slot booked
    5. Commit
    """
    slot = (
        db.execute(
            select(ChargingSlot).where(ChargingSlot.id == data.slot_id)
        ).scalars().first()
    )
    if slot is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Charging slot not found.", "details": {}})

    # The overlap check below spans every slot of this connector. Locking only
    # this one slot row left sibling slots on the same connector free to be
    # booked in parallel (cross-slot double-booking). Lock the connector row
    # first so all bookers/cancellers for it serialize on a single lock.
    db.execute(
        select(ChargingConnector.id)
        .where(ChargingConnector.id == slot.connector_id)
        .with_for_update()
    )

    # Re-read the slot under the connector lock; it may have changed while waiting.
    slot = (
        db.execute(
            select(ChargingSlot)
            .where(ChargingSlot.id == data.slot_id)
            .with_for_update()
        ).scalars().first()
    )
    if slot is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Charging slot not found.", "details": {}})

    if slot.is_booked:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": "Charging slot is already booked.", "details": {}},
        )

    # Check for time-based overlap on the same connector
    overlap = has_charging_reservation_overlap(
        db,
        connector_id=slot.connector_id,
        start_time=slot.start_time,
        end_time=slot.end_time,
    )
    if overlap:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": "Charging time overlaps with an existing reservation on this connector.", "details": {}},
        )

    # Mark slot booked
    slot.is_booked = True

    # Create reservation
    code = f"RES-{uuid.uuid4().hex[:10].upper()}"
    reservation = ChargingReservation(
        reservation_code=code,
        slot_id=data.slot_id,
        vehicle_id=data.vehicle_id,
        driver_id=data.driver_id,
        delivery_id=data.delivery_id,
        start_time=slot.start_time,
        end_time=slot.end_time,
        status="confirmed",
    )
    db.add(reservation)
    _commit_or_conflict(db)
    db.refresh(reservation)
    return _reservation_read(reservation)


def list_reservations(db: Session, page: int = 1, page_size: int = 20,
                      driver_id: int = None, vehicle_id: int = None, status: str = None):
    q = db.query(ChargingReservation)
    if driver_id:
        q = q.filter(ChargingReservation.driver_id == driver_id)
    if vehicle_id:
        q = q.filter(ChargingReservation.vehicle_id == vehicle_id)
    if status:
        q = q.filter(ChargingReservation.status == status)
    total = q.count()
    reservations = q.order_by(ChargingReservation.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_reservation_read(r) for r in reservations], total, page, page_size)


def cancel_reservation(db: Session, reservation_id: int) -> None:
    r = db.query(ChargingReservation).filter(ChargingReservation.id == reservation_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Reservation not found.", "details": {}})

    # Serialize against create_reservation by taking the same connector lock
    # before releasing the slot, so the release cannot interleave with a
    # booking on the same connector.
    slot = db.query(ChargingSlot).filter(ChargingSlot.id == r.slot_id).first()
    if slot is not None:
        db.execute(
            select(ChargingConnector.id)
            .where(ChargingConnector.id == slot.connector_id)
            .with_for_update()
        )

    # Re-read under the connector lock; it may have changed while waiting.
    r = db.query(ChargingReservation).filter(ChargingReservation.id == reservation_id).with_for_update().first()
    if r is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Reservation not found.", "details": {}})
    if r.status in ("completed", "cancelled"):
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": f"Cannot cancel a reservation with status '{r.status}'.", "details": {}})
    r.status = "cancelled"
    # Release slot
    slot = db.query(ChargingSlot).filter(ChargingSlot.id == r.slot_id).with_for_update().first()
    if slot:
        slot.is_booked = False
    _commit_or_conflict(db)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
def _session_read(s: ChargingSession) -> SessionRead:
    driver_name = None
    vehicle_code = s.vehicle.registration_number if s.vehicle else None
    station_name = s.connector.station.name if (s.connector and s.connector.station) else None
    connector_code = f"Connector #{s.connector.connector_number}" if s.connector else None

    if s.reservation and s.reservation.driver and s.reservation.driver.user:
        driver_name = s.reservation.driver.user.full_name

    return SessionRead(
        id=s.id, reservation_id=s.reservation_id,
        connector_id=s.connector_id, vehicle_id=s.vehicle_id,
        start_time=s.start_time, end_time=s.end_time,
        initial_soc_percent=float(s.initial_soc_percent),
        final_soc_percent=float(s.final_soc_percent) if s.final_soc_percent is not None else None,
        energy_kwh_delivered=float(s.energy_kwh_delivered),
        driver_name=driver_name,
        vehicle_code=vehicle_code,
        station_name=station_name,
        connector_code=connector_code,
    )


def list_sessions(db: Session, page: int = 1, page_size: int = 20,
                  vehicle_id: int = None, connector_id: int = None):
    q = db.query(ChargingSession)
    if vehicle_id:
        q = q.filter(ChargingSession.vehicle_id == vehicle_id)
    if connector_id:
        q = q.filter(ChargingSession.connector_id == connector_id)
    total = q.count()
    sessions = q.order_by(ChargingSession.start_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [_session_read(s) for s in sessions]
    return make_page(items, total, page, page_size)


def start_charging_session(db: Session, reservation_id: int) -> SessionRead:
    r = db.query(ChargingReservation).filter(ChargingReservation.id == reservation_id).first()
    if not r:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Charging reservation not found.", "details": {}})

    if r.status != "confirmed":
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": f"Reservation has status '{r.status}'. Cannot start session.", "details": {}})

    slot = db.query(ChargingSlot).filter(ChargingSlot.id == r.slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Charging slot not found.", "details": {}})

    from backend.app.models.vehicle import Vehicle
    v = db.query(Vehicle).filter(Vehicle.id == r.vehicle_id).first()
    if not v:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Vehicle not found.", "details": {}})

    r.status = "active"
    v.status = "charging"

    session = ChargingSession(
        reservation_id=r.id,
        connector_id=slot.connector_id,
        vehicle_id=v.id,
        start_time=datetime.utcnow(),
        initial_soc_percent=v.current_soc_percent,
        energy_kwh_delivered=0.0
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Launch background charging session simulator if enabled
    try:
        from backend.app.services import simulator_service
        simulator_service.start_charging_simulation(db, r.id)
    except Exception as ex:
        pass

    return SessionRead(
        id=session.id, reservation_id=session.reservation_id,
        connector_id=session.connector_id, vehicle_id=session.vehicle_id,
        start_time=session.start_time, end_time=session.end_time,
        initial_soc_percent=float(session.initial_soc_percent),
        final_soc_percent=float(session.final_soc_percent) if session.final_soc_percent is not None else None,
        energy_kwh_delivered=float(session.energy_kwh_delivered)
    )


def complete_charging_session(db: Session, reservation_id: int, target_soc: float = 90.0) -> SessionRead:
    r = db.query(ChargingReservation).filter(ChargingReservation.id == reservation_id).first()
    if not r:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Charging reservation not found.", "details": {}})

    session = db.query(ChargingSession).filter(ChargingSession.reservation_id == r.id).first()
    if not session:
        # Fallback create session if start was skipped
        slot = db.query(ChargingSlot).filter(ChargingSlot.id == r.slot_id).first()
        from backend.app.models.vehicle import Vehicle
        v = db.query(Vehicle).filter(Vehicle.id == r.vehicle_id).first()
        session = ChargingSession(
            reservation_id=r.id,
            connector_id=slot.connector_id if slot else 1,
            vehicle_id=r.vehicle_id,
            start_time=r.start_time,
            initial_soc_percent=v.current_soc_percent if v else 20.0,
            energy_kwh_delivered=0.0
        )
        db.add(session)
        db.flush()

    from backend.app.models.vehicle import Vehicle
    v = db.query(Vehicle).filter(Vehicle.id == r.vehicle_id).first()

    now = datetime.utcnow()
    session.end_time = now
    session.final_soc_percent = target_soc

    battery_cap = float(v.vehicle_type.battery_capacity_kwh) if (v and v.vehicle_type and v.vehicle_type.battery_capacity_kwh) else 3.5
    soc_gained = max(0.0, target_soc - float(session.initial_soc_percent))
    energy_delivered = (soc_gained / 100.0) * battery_cap
    session.energy_kwh_delivered = round(energy_delivered, 2)

    # Cost calculation
    connector = db.query(ChargingConnector).filter(ChargingConnector.id == session.connector_id).first()
    price = float(connector.price_per_kwh) if (connector and connector.price_per_kwh is not None) else 0.0
    session.total_cost = round(energy_delivered * price, 2)

    r.status = "completed"

    if v:
        v.current_soc_percent = target_soc
        v.status = "available"  # return vehicle status to available

    # Free the slot
    slot = db.query(ChargingSlot).filter(ChargingSlot.id == r.slot_id).first()
    if slot:
        slot.is_booked = False

    db.commit()
    db.refresh(session)
    return SessionRead(
        id=session.id, reservation_id=session.reservation_id,
        connector_id=session.connector_id, vehicle_id=session.vehicle_id,
        start_time=session.start_time, end_time=session.end_time,
        initial_soc_percent=float(session.initial_soc_percent),
        final_soc_percent=float(session.final_soc_percent) if session.final_soc_percent is not None else None,
        energy_kwh_delivered=float(session.energy_kwh_delivered)
    )
