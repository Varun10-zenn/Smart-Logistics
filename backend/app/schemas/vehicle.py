"""Vehicle schemas."""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class VehicleCreate(BaseModel):
    registration_no: str = Field(..., max_length=64)
    vehicle_type_id: int
    is_ev: bool = False
    battery_capacity_kwh: Optional[float] = Field(None, gt=0)
    consumption_kwh_per_km: Optional[float] = Field(None, gt=0)


class VehicleRead(BaseModel):
    id: int
    registration_number: str
    is_ev: bool
    battery_capacity_kwh: Optional[float] = None
    soc_percent: Optional[float] = None
    consumption_kwh_per_km: Optional[float] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class SoCUpdate(BaseModel):
    soc_percent: float = Field(..., ge=0.0, le=100.0)
