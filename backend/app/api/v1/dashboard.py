"""Dashboard router."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import require_role, get_current_user
from backend.app.schemas.dashboard import (
    WarehouseDashboard, DeliveryDashboard, ChargingDashboard, OverviewDashboard
)
from backend.app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=OverviewDashboard)
def get_overview(
    current_user=Depends(get_current_user),  # Any authenticated user
    db: Session = Depends(get_db),
):
    return dashboard_service.get_overview_dashboard(db)


@router.get("/warehouse", response_model=WarehouseDashboard)
def get_warehouse_dashboard(
    current_user=Depends(require_role("admin", "warehouse_operator", "fleet_manager")),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_warehouse_dashboard(db)


@router.get("/delivery", response_model=DeliveryDashboard)
def get_delivery_dashboard(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import fastapi
    role = current_user.role.code
    if role not in ("admin", "fleet_manager", "driver"):
        raise fastapi.HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    return dashboard_service.get_delivery_dashboard(db)


@router.get("/charging", response_model=ChargingDashboard)
def get_charging_dashboard(
    current_user=Depends(require_role("admin", "fleet_manager", "driver", "station_admin")),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_charging_dashboard(db)
