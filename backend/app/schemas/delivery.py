"""Delivery schemas."""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class DeliveryCreate(BaseModel):
    batch_id: int
    driver_id: int
    vehicle_id: int
    scheduled_dispatch_time: Optional[datetime] = None


class DeliveryStatusUpdate(BaseModel):
    status: Literal["assigned", "dispatched", "in_transit", "charging_stop", "completed", "failed"]
    traffic_factor: Optional[float] = Field(None, ge=1.0, le=5.0)
    weather_factor: Optional[float] = Field(None, ge=1.0, le=3.0)


class ETAResponse(BaseModel):
    delivery_id: int
    eta: datetime
    base_route_minutes: float
    traffic_factor: float
    weather_factor: float
    algorithm: str
    confidence: Optional[float] = None


class DeliveryRead(BaseModel):
    id: int
    delivery_code: str
    batch_id: int
    driver_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    status: str
    scheduled_dispatch_time: datetime
    estimated_eta: Optional[datetime] = None
    created_at: datetime

    driver_name: Optional[str] = None
    vehicle_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DeliveryStopRead(BaseModel):
    id: int
    delivery_id: int
    order_id: int
    stop_sequence: int
    status: str
    estimated_arrival: datetime
    actual_arrival: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DeliveryRouteRead(BaseModel):
    id: int
    delivery_id: int
    total_distance_km: float
    estimated_travel_minutes: float
    traffic_factor: float
    weather_factor: float
    route_geometry: Optional[str] = None
    route_source: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
