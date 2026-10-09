"""Audit router — admin only."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import require_role
from backend.app.schemas.common import Page
from backend.app.schemas.audit import AuditLogRead
from backend.app.services import audit_service

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/logs", response_model=Page[AuditLogRead])
def list_audit_logs(
    page: int = 1, page_size: int = 20,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return audit_service.list_logs(db, page, page_size, user_id, action, resource_type, from_date, to_date)
