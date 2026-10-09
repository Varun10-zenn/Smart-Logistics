from fastapi import APIRouter, status
from backend.app.core.config import settings
from backend.app.core.database import check_db_connectivity
from backend.app.schemas.health import HealthCheckResponse, DatabaseHealthResponse

router = APIRouter(tags=["Health Check"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Get application and database health status"
)
def get_health():
    """
    Returns general system operational status and performs database connectivity check.
    """
    db_health_data = check_db_connectivity()
    db_response = DatabaseHealthResponse(**db_health_data)
    
    overall_status = "healthy" if db_health_data["status"] in ["connected", "connected_fallback"] else "degraded"

    return HealthCheckResponse(
        status=overall_status,
        environment=settings.APP_ENV,
        version="1.0.0",
        database=db_response
    )


@router.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Dedicated database connectivity check"
)
def get_db_health():
    """
    Direct endpoint for checking PostgreSQL / database connectivity status and latency.
    """
    db_health_data = check_db_connectivity()
    return DatabaseHealthResponse(**db_health_data)
