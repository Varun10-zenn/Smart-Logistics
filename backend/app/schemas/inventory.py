"""Inventory schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class InventoryCreate(BaseModel):
    warehouse_id: int
    location_id: int
    product_id: int
    quantity: int = Field(..., ge=0)
    reorder_threshold: int = Field(10, ge=0)


class InventoryRead(BaseModel):
    id: int
    warehouse_id: int
    product_id: int
    location_id: int
    quantity: int
    reorder_threshold: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=0)
    reorder_threshold: Optional[int] = Field(None, ge=0)
