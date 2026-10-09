"""Charging router — includes atomic reservation endpoint."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.schemas.common import Page
from backend.app.schemas.charging import (
    StationCreate, StationRead, StationUpdate,
    ConnectorRead, SlotRead,
    ChargingRecommendRequest, ChargingRecommendResponse,
    ReservationCreate, ReservationRead,
    SessionRead,
)
from backend.app.services import charging_service, audit_service

router = APIRouter(prefix="/charging", tags=["Charging"])

_STATION_READ_ROLES = ("admin", "fleet_manager", "driver", "station_admin")


# ---------------------------------------------------------------------------
# Stations
# ---------------------------------------------------------------------------
@router.get("/stations", response_model=Page[StationRead])
def list_stations(
    page: int = 1, page_size: int = 20, status: Optional[str] = None,
    current_user=Depends(require_role(*_STATION_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return charging_service.list_stations(db, page, page_size, status)


@router.post("/stations", response_model=StationRead, status_code=201)
def create_station(
    data: StationCreate,
    current_user=Depends(require_role("admin", "station_admin")),
    db: Session = Depends(get_db),
):
    return charging_service.create_station(db, data)


@router.get("/stations/{station_id}", response_model=StationRead)
def get_station(
    station_id: int,
    current_user=Depends(require_role(*_STATION_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return charging_service.get_station(db, station_id)


@router.patch("/stations/{station_id}", response_model=StationRead)
def update_station(
    station_id: int, data: StationUpdate,
    current_user=Depends(require_role("admin", "station_admin")),
    db: Session = Depends(get_db),
):
    return charging_service.update_station(db, station_id, data)


@router.delete("/stations/{station_id}", status_code=204)
def delete_station(
    station_id: int,
    current_user=Depends(require_role("admin", "station_admin")),
    db: Session = Depends(get_db),
):
    charging_service.delete_station(db, station_id)


# ---------------------------------------------------------------------------
# Connectors & Slots
# ---------------------------------------------------------------------------
from backend.app.schemas.charging import ConnectorCreate, ConnectorUpdate, SlotCreate, SlotGenerateRequest

@router.get("/connectors", response_model=Page[ConnectorRead])
def list_connectors(
    page: int = 1, page_size: int = 20,
    station_id: Optional[int] = None, status: Optional[str] = None,
    current_user=Depends(require_role(*_STATION_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return charging_service.list_connectors(db, page, page_size, station_id, status)


@router.post("/stations/{station_id}/connectors", response_model=ConnectorRead, status_code=201)
def create_connector(
    station_id: int, data: ConnectorCreate,
    current_user=Depends(require_role("admin", "station_admin")),
    db: Session = Depends(get_db),
):
    return charging_service.create_connector(db, station_id, data)


@router.patch("/connectors/{connector_id}", response_model=ConnectorRead)
def update_connector(
    connector_id: int, data: ConnectorUpdate,
    current_user=Depends(require_role("admin", "station_admin")),
    db: Session = Depends(get_db),
):
    return charging_service.update_connector(db, connector_id, data)


@router.delete("/connectors/{connector_id}", status_code=204)
def delete_connector(
    connector_id: int,
    current_user=Depends(require_role("admin", "station_admin")),
    db: Session = Depends(get_db),
):
    charging_service.delete_connector(db, connector_id)


@router.get("/slots", response_model=Page[SlotRead])
def list_slots(
    page: int = 1, page_size: int = 20,
    connector_id: Optional[int] = None, available_only: bool = False,
    current_user=Depends(require_role(*_STATION_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return charging_service.list_slots(db, page, page_size, connector_id, available_only)


@router.post("/connectors/{connector_id}/slots", response_model=SlotRead, status_code=201)
def create_slot(
    connector_id: int, data: SlotCreate,
    current_user=Depends(require_role("admin", "station_admin")),
    db: Session = Depends(get_db),
):
    return charging_service.create_slot(db, connector_id, data)


@router.post("/connectors/{connector_id}/slots/generate", response_model=list[SlotRead])
def generate_slots(
    connector_id: int, data: SlotGenerateRequest = SlotGenerateRequest(),
    current_user=Depends(require_role("admin", "station_admin")),
    db: Session = Depends(get_db),
):
    return charging_service.generate_slots(db, connector_id, slot_minutes=data.slot_minutes, hours_ahead=data.hours_ahead)


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------
@router.post("/recommend", response_model=ChargingRecommendResponse)
def recommend_charging(
    data: ChargingRecommendRequest,
    current_user=Depends(require_role("admin", "fleet_manager", "driver")),
    db: Session = Depends(get_db),
):
    return charging_service.recommend_charging(db, data)


# ---------------------------------------------------------------------------
# Reservations (ATOMIC)
# ---------------------------------------------------------------------------
@router.post("/reservations", response_model=ReservationRead, status_code=201)
def create_reservation(
    data: ReservationCreate, request: Request,
    current_user=Depends(require_role("admin", "fleet_manager", "driver", "station_admin")),
    db: Session = Depends(get_db),
):
    result = charging_service.create_reservation(db, data)
    audit_service.log_action(
        db, user_id=current_user.id, action="CREATE_RESERVATION",
        resource_type="charging_reservations", resource_id=str(result.id),
        details={"slot_id": data.slot_id, "vehicle_id": data.vehicle_id, "driver_id": data.driver_id},
        ip_address=request.client.host if request.client else None,
    )
    return result


@router.get("/reservations", response_model=Page[ReservationRead])
def list_reservations(
    page: int = 1, page_size: int = 20,
    status: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager", "station_admin", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    # Drivers see only their own reservations
    driver_id = None
    if role == "driver":
        from backend.app.models.delivery import Driver
        d = db.query(Driver).filter(Driver.user_id == current_user.id).first()
        driver_id = d.id if d else -1
    return charging_service.list_reservations(db, page, page_size, driver_id=driver_id, status=status)


@router.post("/reservations/{reservation_id}/start", response_model=SessionRead)
def start_charging_session(
    reservation_id: int,
    current_user=Depends(require_role("admin", "fleet_manager", "driver", "station_admin")),
    db: Session = Depends(get_db),
):
    return charging_service.start_charging_session(db, reservation_id)


@router.post("/reservations/{reservation_id}/complete", response_model=SessionRead)
def complete_charging_session(
    reservation_id: int,
    target_soc: float = 90.0,
    current_user=Depends(require_role("admin", "fleet_manager", "driver", "station_admin")),
    db: Session = Depends(get_db),
):
    return charging_service.complete_charging_session(db, reservation_id, target_soc=target_soc)


@router.delete("/reservations/{reservation_id}", status_code=204)
def cancel_reservation(
    reservation_id: int, request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager", "station_admin", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    # Drivers can only cancel own reservations
    if role == "driver":
        from backend.app.models.charging import ChargingReservation
        from backend.app.models.delivery import Driver
        d = db.query(Driver).filter(Driver.user_id == current_user.id).first()
        if d is None:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "No driver profile.", "details": {}})
        res = db.query(ChargingReservation).filter(
            ChargingReservation.id == reservation_id,
            ChargingReservation.driver_id == d.id,
        ).first()
        if res is None:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    charging_service.cancel_reservation(db, reservation_id)
    audit_service.log_action(
        db, user_id=current_user.id, action="CANCEL_RESERVATION",
        resource_type="charging_reservations", resource_id=str(reservation_id),
        ip_address=request.client.host if request.client else None,
    )


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
@router.get("/sessions", response_model=Page[SessionRead])
def list_sessions(
    page: int = 1, page_size: int = 20,
    vehicle_id: Optional[int] = None, connector_id: Optional[int] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager", "station_admin", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    # Drivers see only sessions for their assigned vehicles
    if role == "driver" and vehicle_id is None:
        from backend.app.models.delivery import Driver, Delivery
        d = db.query(Driver).filter(Driver.user_id == current_user.id).first()
        if d:
            latest_delivery = db.query(Delivery).filter(Delivery.driver_id == d.id).order_by(Delivery.created_at.desc()).first()
            if latest_delivery:
                vehicle_id = latest_delivery.vehicle_id
    return charging_service.list_sessions(db, page, page_size, vehicle_id, connector_id)
