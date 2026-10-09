"""Intelligence router — allowlisted operations only."""
from typing import Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.schemas.common import Page
from backend.app.schemas.intelligence import (
    IntelligenceRunRequest, IntelligenceRunResponse,
    RecommendationRead, ForecastRead,
)
from backend.app.services import intelligence_service, audit_service

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


@router.post("/run", response_model=IntelligenceRunResponse)
def run_intelligence(
    data: IntelligenceRunRequest, request: Request,
    current_user=Depends(get_current_user),  # Any authenticated user
    db: Session = Depends(get_db),
):
    """
    Execute an allowlisted intelligence operation.
    The 'operation' field is validated by Pydantic — only the 3 allowlisted
    operations are accepted; everything else returns 422 VALIDATION_ERROR.
    """
    result = intelligence_service.run_operation(db, data, current_user.id)
    audit_service.log_action(
        db, user_id=current_user.id, action="INTELLIGENCE_RUN",
        resource_type="ai_recommendations",
        details={"operation": data.operation},
        ip_address=request.client.host if request.client else None,
    )
    return result


@router.get("/recommendations", response_model=Page[RecommendationRead])
def list_recommendations(
    page: int = 1, page_size: int = 20,
    operation_type: Optional[str] = None,
    current_user=Depends(get_current_user),  # Any authenticated user
    db: Session = Depends(get_db),
):
    return intelligence_service.list_recommendations(db, page, page_size, operation_type)


@router.get("/forecasts", response_model=Page[ForecastRead])
def list_forecasts(
    page: int = 1, page_size: int = 20,
    forecast_type: Optional[str] = None,
    current_user=Depends(require_role("admin", "warehouse_operator", "fleet_manager", "station_admin")),
    db: Session = Depends(get_db),
):
    return intelligence_service.list_forecasts(db, page, page_size, forecast_type)
