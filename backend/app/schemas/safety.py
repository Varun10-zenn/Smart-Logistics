"""Safety schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SafetyScoreRead(BaseModel):
    id: int
    delivery_id: int
    score: float
    speed_score: float
    braking_score: float
    acceleration_score: float
    route_score: float
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SafetyEventRead(BaseModel):
    id: int
    delivery_id: int
    event_type: str
    severity: str
    timestamp: datetime
    latitude: float
    longitude: float
    value: float
    threshold: float

    model_config = ConfigDict(from_attributes=True)


class SafetyAlertRead(BaseModel):
    id: int
    delivery_id: int
    alert_type: str
    severity: str
    message: str
    acknowledged: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
