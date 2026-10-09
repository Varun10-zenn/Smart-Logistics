"""Vehicles router."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.schemas.common import Page
from backend.app.schemas.vehicle import VehicleCreate, VehicleRead, SoCUpdate
from backend.app.services import vehicle_service

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])

_READ_ROLES = ("admin", "fleet_manager", "station_admin")


@router.get("", response_model=Page[VehicleRead])
def list_vehicles(
    page: int = 1, page_size: int = 20,
    is_ev: Optional[bool] = None, status: Optional[str] = None,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return vehicle_service.list_vehicles(db, page, page_size, is_ev, status)


@router.get("/batteries", summary="Get EV battery overview for fleet management")
def get_fleet_batteries(
    warehouse_id: Optional[int] = None,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return vehicle_service.get_fleet_batteries(db, warehouse_id)


@router.post("", response_model=VehicleRead, status_code=201)
def create_vehicle(
    data: VehicleCreate,
    current_user=Depends(require_role("admin", "fleet_manager")),
    db: Session = Depends(get_db),
):
    return vehicle_service.create_vehicle(db, data)


@router.get("/{vehicle_id}", response_model=VehicleRead)
def get_vehicle(
    vehicle_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role in ("admin", "fleet_manager", "station_admin"):
        return vehicle_service.get_vehicle(db, vehicle_id)
    if role == "driver":
        # Driver can only see vehicle assigned to their delivery
        from backend.app.models.delivery import Driver, Delivery
        driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
        if driver is None:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "No driver profile found.", "details": {}})
        owns = db.query(Delivery).filter(
            Delivery.driver_id == driver.id,
            Delivery.vehicle_id == vehicle_id,
        ).first()
        if owns is None:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
        return vehicle_service.get_vehicle(db, vehicle_id)
    raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})


@router.patch("/{vehicle_id}/soc", response_model=VehicleRead)
def update_soc(
    vehicle_id: int, data: SoCUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role in ("admin", "fleet_manager"):
        return vehicle_service.update_soc(db, vehicle_id, data)
    if role == "driver":
        from backend.app.models.delivery import Driver, Delivery
        driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
        if driver is None:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "No driver profile found.", "details": {}})
        owns = db.query(Delivery).filter(
            Delivery.driver_id == driver.id,
            Delivery.vehicle_id == vehicle_id,
        ).first()
        if owns is None:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
        return vehicle_service.update_soc(db, vehicle_id, data)
    raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
