"""Audit service."""
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.models.user import AuditLog
from backend.app.schemas.common import make_page
from backend.app.schemas.audit import AuditLogRead


def log_action(
    db: Session,
    user_id: Optional[int],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Record an audit log entry. Does NOT log passwords, tokens, or secrets."""
    # Sanitize details to avoid logging sensitive fields
    safe_details = {}
    if details:
        BLOCKED_KEYS = {"password", "password_hash", "access_token", "refresh_token", "token", "secret"}
        safe_details = {k: v for k, v in details.items() if k.lower() not in BLOCKED_KEYS}

    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=safe_details or None,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()


def list_logs(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    user_id: int = None,
    action: str = None,
    resource_type: str = None,
    from_date=None,
    to_date=None,
):
    q = db.query(AuditLog)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        q = q.filter(AuditLog.resource_type == resource_type)
    if from_date:
        q = q.filter(AuditLog.created_at >= from_date)
    if to_date:
        q = q.filter(AuditLog.created_at <= to_date)

    total = q.count()
    logs = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [AuditLogRead(
        id=log.id,
        user_id=log.user_id,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        details=log.details,
        ip_address=log.ip_address,
        created_at=log.created_at,
    ) for log in logs]
    return make_page(items, total, page, page_size)
