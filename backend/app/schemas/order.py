"""Order schemas."""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)


class OrderCreate(BaseModel):
    order_number: Optional[str] = Field(None, max_length=64)
    warehouse_id: int
    customer_name: Optional[str] = Field(None, max_length=128)
    destination_address: Optional[str] = None
    customer_lat: float = Field(..., ge=-90, le=90)
    customer_lon: float = Field(..., ge=-180, le=180)
    promised_at: datetime
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    items: List[OrderItemCreate] = Field(..., min_length=1)



class OrderItemRead(BaseModel):
    id: int
    product_id: int
    quantity: int

    model_config = ConfigDict(from_attributes=True)


class OrderRead(BaseModel):
    id: int
    order_number: str
    warehouse_id: int
    customer_name: Optional[str] = None
    customer_lat: float
    customer_lon: float
    created_at: datetime
    promised_at: datetime
    priority: str
    status: str
    items: List[OrderItemRead] = []

    model_config = ConfigDict(from_attributes=True)


ORDER_STATUSES = Literal[
    "pending", "batched", "picking", "picked",
    "in_transit", "delivered", "cancelled"
]


class OrderStatusUpdate(BaseModel):
    status: ORDER_STATUSES
