"""Warehouse schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class WarehouseCreate(BaseModel):
    code: str = Field(..., max_length=32)
    name: str = Field(..., max_length=128)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = None


class WarehouseRead(BaseModel):
    id: int
    code: str
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    status: str
    external_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    address: Optional[str] = None
    status: Optional[str] = None


# --- Zones ---
class WarehouseZoneCreate(BaseModel):
    zone_code: str = Field(..., max_length=32)
    name: str = Field(..., max_length=64)
    zone_type: str = Field("standard", max_length=32)


class WarehouseZoneRead(BaseModel):
    id: int
    warehouse_id: int
    zone_code: str
    name: str
    zone_type: str

    model_config = ConfigDict(from_attributes=True)


class WarehouseZoneUpdate(BaseModel):
    zone_code: Optional[str] = Field(None, max_length=32)
    name: Optional[str] = Field(None, max_length=64)
    zone_type: Optional[str] = Field(None, max_length=32)


# --- Nodes ---
class WarehouseNodeCreate(BaseModel):
    node_code: str = Field(..., max_length=32)
    x_coord: float
    y_coord: float
    z_coord: float = 0.0
    zone_id: Optional[int] = None
    is_blocked: bool = False
    is_depot: bool = False


class NodeRead(BaseModel):
    id: int
    warehouse_id: int
    node_code: str
    x_coord: float
    y_coord: float
    z_coord: float
    is_blocked: bool
    is_depot: bool
    zone_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class WarehouseNodeUpdate(BaseModel):
    node_code: Optional[str] = Field(None, max_length=32)
    x_coord: Optional[float] = None
    y_coord: Optional[float] = None
    z_coord: Optional[float] = None
    zone_id: Optional[int] = None
    is_blocked: Optional[bool] = None
    is_depot: Optional[bool] = None


# --- Edges ---
class WarehouseEdgeCreate(BaseModel):
    from_node_id: int
    to_node_id: int
    distance_meters: Optional[float] = Field(None, gt=0)
    is_bidirectional: bool = True
    is_blocked: bool = False


class EdgeRead(BaseModel):
    id: int
    warehouse_id: int
    from_node_id: int
    to_node_id: int
    distance_meters: float
    is_bidirectional: bool
    is_blocked: bool

    model_config = ConfigDict(from_attributes=True)


class WarehouseEdgeUpdate(BaseModel):
    distance_meters: Optional[float] = Field(None, gt=0)
    is_bidirectional: Optional[bool] = None
    is_blocked: Optional[bool] = None


# --- Storage Locations ---
class StorageLocationCreate(BaseModel):
    node_id: int
    location_code: str = Field(..., max_length=32)
    aisle: str = Field(..., max_length=16)
    shelf: str = Field(..., max_length=16)
    bin: str = Field(..., max_length=16)
    max_weight_kg: float = Field(100.0, gt=0)


class StorageLocationRead(BaseModel):
    id: int
    node_id: int
    location_code: str
    aisle: str
    shelf: str
    bin: str
    max_weight_kg: float

    model_config = ConfigDict(from_attributes=True)


class StorageLocationUpdate(BaseModel):
    location_code: Optional[str] = Field(None, max_length=32)
    aisle: Optional[str] = Field(None, max_length=16)
    shelf: Optional[str] = Field(None, max_length=16)
    bin: Optional[str] = Field(None, max_length=16)
    max_weight_kg: Optional[float] = Field(None, gt=0)


# --- Graph & Validation ---
class WarehouseGraphRead(BaseModel):
    warehouse_id: int
    nodes: List[NodeRead]
    edges: List[EdgeRead]
    locations: List[StorageLocationRead] = []


class WarehouseValidationRead(BaseModel):
    valid: bool
    errors: List[str]


class LayoutGenerateRequest(BaseModel):
    aisles: int = Field(..., ge=1, le=20)
    shelves_per_aisle: int = Field(..., ge=1, le=30)
    aisle_spacing_m: float = Field(..., gt=0)
    shelf_spacing_m: float = Field(..., gt=0)
    replace_existing: bool = False

