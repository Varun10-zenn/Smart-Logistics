"""Drivers router."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.schemas.common import Page
from backend.app.schemas.driver import DriverCreate, DriverRead, DriverUpdate
from backend.app.services import driver_service

router = APIRouter(prefix="/drivers", tags=["Drivers"])


@router.get("", response_model=Page[DriverRead])
def list_drivers(
    page: int = 1, page_size: int = 20, status: Optional[str] = None,
    current_user=Depends(require_role("admin", "fleet_manager")),
    db: Session = Depends(get_db),
):
    return driver_service.list_drivers(db, page, page_size, status)


@router.post("", response_model=DriverRead, status_code=201)
def create_driver(
    data: DriverCreate,
    current_user=Depends(require_role("admin", "fleet_manager")),
    db: Session = Depends(get_db),
):
    return driver_service.create_driver(db, data)


@router.get("/{driver_id}", response_model=DriverRead)
def get_driver(
    driver_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager"):
        # Driver can only see own profile
        if role == "driver":
            from backend.app.models.delivery import Driver
            own = db.query(Driver).filter(Driver.user_id == current_user.id, Driver.id == driver_id).first()
            if own is None:
                raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
        else:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    return driver_service.get_driver(db, driver_id)


@router.patch("/{driver_id}", response_model=DriverRead)
def update_driver(
    driver_id: int, data: DriverUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager"):
        if role == "driver":
            from backend.app.models.delivery import Driver
            own = db.query(Driver).filter(Driver.user_id == current_user.id, Driver.id == driver_id).first()
            if own is None:
                raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
        else:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    return driver_service.update_driver(db, driver_id, data)
