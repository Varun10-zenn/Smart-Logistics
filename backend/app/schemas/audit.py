"""Audit log schemas."""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
