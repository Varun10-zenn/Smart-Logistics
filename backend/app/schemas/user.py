"""User schemas."""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict


ROLE_CODES = Literal["admin", "warehouse_operator", "driver", "fleet_manager", "station_admin", "customer"]


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=128)
    phone: Optional[str] = Field(None, max_length=32)
    password: str = Field(..., min_length=1)
    role_code: ROLE_CODES
    warehouse_id: Optional[int] = None


class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str
    warehouse_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=128)
    phone: Optional[str] = Field(None, max_length=32)
    password: Optional[str] = Field(None, min_length=8)
    warehouse_id: Optional[int] = None
    is_active: Optional[bool] = None
