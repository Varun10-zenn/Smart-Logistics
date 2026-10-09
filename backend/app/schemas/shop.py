"""Shop schemas for customer ordering flow."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ShopProductItem(BaseModel):
    id: int
    sku: str
    name: str
    category: Optional[str] = None
    unit_weight_kg: float
    unit_volume_cbm: float
    price: float
    available_quantity: int

    model_config = ConfigDict(from_attributes=True)


class ShopProductsResponse(BaseModel):
    warehouse_id: int
    warehouse_name: str
    distance_km: float
    products: List[ShopProductItem]


class CheckoutItem(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)


class CheckoutRequest(BaseModel):
    items: List[CheckoutItem] = Field(..., min_length=1)
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    address: str = Field(..., min_length=1)


class TimelineStep(BaseModel):
    step: str
    completed: bool
    timestamp: Optional[datetime] = None


class CustomerOrderRead(BaseModel):
    id: int
    order_number: str
    warehouse_id: int
    warehouse_name: Optional[str] = None
    customer_name: Optional[str] = None
    destination_address: str
    customer_lat: float
    customer_lon: float
    status: str
    priority: str
    created_at: datetime
    promised_at: datetime
    timeline: List[TimelineStep] = []
    items: List[dict] = []

    # Delivery tracking extensions
    delivery_status: Optional[str] = None
    rider_first_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    stop_eta: Optional[datetime] = None
    stops_before: Optional[int] = None
    route_geometry: Optional[str] = None
    rider_last_lat: Optional[float] = None
    rider_last_lon: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
