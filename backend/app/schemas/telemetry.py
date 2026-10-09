"""Telemetry schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class TelemetryEventCreate(BaseModel):
    vehicle_id: int
    delivery_id: Optional[int] = None
    timestamp: datetime
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    speed_kmh: float = Field(..., ge=0)
    acceleration_ms2: Optional[float] = None
    braking_ms2: Optional[float] = None
    heading_degrees: Optional[float] = Field(None, ge=0, le=360)
    soc_percent: Optional[float] = Field(None, ge=0, le=100)


class TelemetryBatchCreate(BaseModel):
    events: List[TelemetryEventCreate] = Field(..., max_length=500)


class TelemetryEventRead(BaseModel):
    id: int
    vehicle_id: int
    delivery_id: Optional[int] = None
    timestamp: datetime
    latitude: float
    longitude: float
    speed_kmh: float
    soc_percent: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
