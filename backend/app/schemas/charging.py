"""Charging schemas."""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class StationCreate(BaseModel):
    station_code: str = Field(..., max_length=32)
    name: str = Field(..., max_length=128)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    total_connectors: int = Field(..., ge=1)
    status: Literal["operational", "degraded", "offline"] = "operational"


class StationRead(BaseModel):
    id: int
    station_code: str
    name: str
    latitude: float
    longitude: float
    total_connectors: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class StationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    status: Optional[Literal["operational", "degraded", "offline"]] = None
    total_connectors: Optional[int] = Field(None, ge=1)


class ConnectorCreate(BaseModel):
    connector_type: str = Field(..., max_length=32)
    max_power_kw: float = Field(..., gt=0)
    connector_number: Optional[int] = Field(None, ge=1)
    status: Literal["available", "charging", "maintenance", "offline"] = "available"


class ConnectorUpdate(BaseModel):
    connector_type: Optional[str] = Field(None, max_length=32)
    max_power_kw: Optional[float] = Field(None, gt=0)
    status: Optional[Literal["available", "charging", "maintenance", "offline"]] = None


class ConnectorRead(BaseModel):
    id: int
    station_id: int
    connector_number: int
    connector_type: str
    max_power_kw: float
    status: str

    model_config = ConfigDict(from_attributes=True)


class SlotCreate(BaseModel):
    start_time: datetime
    end_time: datetime


class SlotGenerateRequest(BaseModel):
    slot_minutes: int = Field(60, ge=15, le=240)
    hours_ahead: int = Field(24, ge=1, le=168)


class SlotRead(BaseModel):
    id: int
    connector_id: int
    start_time: datetime
    end_time: datetime
    is_booked: bool

    model_config = ConfigDict(from_attributes=True)


class ChargingRecommendRequest(BaseModel):
    vehicle_id: int
    current_soc_percent: float = Field(..., ge=0, le=100)
    destination_lat: float = Field(..., ge=-90, le=90)
    destination_lon: float = Field(..., ge=-180, le=180)
    current_lat: float = Field(..., ge=-90, le=90)
    current_lon: float = Field(..., ge=-180, le=180)
    minimum_soc_after_charge: float = Field(80.0, ge=0, le=100)
    preferred_start: Optional[datetime] = None


class ChargingCandidate(BaseModel):
    station_id: int
    connector_id: int
    slot_id: Optional[int] = None
    estimated_wait_minutes: float
    estimated_charge_minutes: float
    route_detour_km: float
    station_score: float

class ChargingRecommendResponse(BaseModel):
    recommended_station_id: int
    recommended_connector_id: int
    recommended_slot_id: Optional[int] = None
    estimated_wait_minutes: float
    estimated_charge_minutes: float
    route_detour_km: float
    station_score: float
    explanation: str
    algorithm: str
    fallback_used: bool
    candidate_stations: list[ChargingCandidate] = Field(default_factory=list)
    optimization_metadata: dict = Field(default_factory=dict)


class ReservationCreate(BaseModel):
    slot_id: int
    vehicle_id: int
    driver_id: int
    delivery_id: Optional[int] = None


class ReservationRead(BaseModel):
    id: int
    reservation_code: str
    slot_id: int
    vehicle_id: int
    driver_id: int
    delivery_id: Optional[int] = None
    start_time: datetime
    end_time: datetime
    status: str
    created_at: datetime

    # Display / Identity fields
    driver_name: Optional[str] = None
    vehicle_code: Optional[str] = None
    station_name: Optional[str] = None
    connector_code: Optional[str] = None
    slot_time_range: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SessionRead(BaseModel):
    id: int
    reservation_id: Optional[int] = None
    connector_id: int
    vehicle_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    initial_soc_percent: float
    final_soc_percent: Optional[float] = None
    energy_kwh_delivered: float

    # Display / Identity fields
    driver_name: Optional[str] = None
    vehicle_code: Optional[str] = None
    station_name: Optional[str] = None
    connector_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
