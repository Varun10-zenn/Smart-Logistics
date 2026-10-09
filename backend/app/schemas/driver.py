"""Driver schemas."""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class DriverCreate(BaseModel):
    user_id: int
    license_number: str = Field(..., max_length=64)
    vehicle_type_id: Optional[int] = None


class DriverRead(BaseModel):
    id: int
    user_id: int
    full_name: str = ""  # populated from joined user in service
    license_number: str
    status: str
    rating: float

    model_config = ConfigDict(from_attributes=True)


class DriverUpdate(BaseModel):
    license_number: Optional[str] = Field(None, max_length=64)
    status: Optional[Literal["available", "on_delivery", "off_duty"]] = None
