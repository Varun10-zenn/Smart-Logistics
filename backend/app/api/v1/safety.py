"""Safety router."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.schemas.common import Page
from backend.app.schemas.safety import SafetyScoreRead, SafetyEventRead, SafetyAlertRead
from backend.app.services import safety_service

router = APIRouter(prefix="/safety", tags=["Safety"])


def _get_driver_id(current_user, db: Session) -> Optional[int]:
    if current_user.role.code == "driver":
        from backend.app.models.delivery import Driver
        d = db.query(Driver).filter(Driver.user_id == current_user.id).first()
        return d.id if d else None
    return None


@router.get("/scores", response_model=Page[SafetyScoreRead])
def list_scores(
    page: int = 1, page_size: int = 20,
    delivery_id: Optional[int] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    return safety_service.list_scores(db, page, page_size, delivery_id)


@router.get("/scores/{delivery_id}", response_model=SafetyScoreRead)
def get_score(
    delivery_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    return safety_service.get_score_by_delivery(db, delivery_id)


@router.get("/events", response_model=Page[SafetyEventRead])
def list_safety_events(
    page: int = 1, page_size: int = 20,
    delivery_id: Optional[int] = None,
    current_user=Depends(require_role("admin", "fleet_manager")),
    db: Session = Depends(get_db),
):
    return safety_service.list_events(db, page, page_size, delivery_id)


@router.get("/alerts", response_model=Page[SafetyAlertRead])
def list_alerts(
    page: int = 1, page_size: int = 20,
    delivery_id: Optional[int] = None,
    acknowledged: Optional[bool] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    # Drivers see only alerts for their own deliveries
    if role == "driver" and delivery_id is None:
        from backend.app.models.delivery import Driver, Delivery
        driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
        if driver:
            latest = db.query(Delivery).filter(Delivery.driver_id == driver.id).order_by(Delivery.created_at.desc()).first()
            delivery_id = latest.id if latest else -1
    return safety_service.list_alerts(db, page, page_size, delivery_id, acknowledged)


@router.patch("/alerts/{alert_id}/acknowledge", response_model=SafetyAlertRead)
def acknowledge_alert(
    alert_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    return safety_service.acknowledge_alert(db, alert_id)
