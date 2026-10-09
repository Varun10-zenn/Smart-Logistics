"""Product schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ProductCreate(BaseModel):
    sku: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    category: str = Field(..., max_length=64)
    unit_weight_kg: float = Field(..., gt=0)
    unit_volume_cbm: float = Field(..., gt=0)
    price: float = Field(..., ge=0)


class ProductRead(BaseModel):
    id: int
    sku: str
    name: str
    category: str
    unit_weight_kg: float
    unit_volume_cbm: float
    price: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=64)
    unit_weight_kg: Optional[float] = Field(None, gt=0)
    unit_volume_cbm: Optional[float] = Field(None, gt=0)
    price: Optional[float] = Field(None, ge=0)
