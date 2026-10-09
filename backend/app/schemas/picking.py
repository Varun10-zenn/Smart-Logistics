"""Picking route schemas."""
from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict


class PickOptimizeRequest(BaseModel):
    batch_id: int


class PickRouteStepRead(BaseModel):
    id: int
    step_number: int
    location_id: int
    location_code: str
    node_id: int
    product_id: int
    product_sku: str
    product_name: str
    quantity_to_pick: int
    is_completed: bool
    x_coord: float
    y_coord: float

    model_config = ConfigDict(from_attributes=True)


class PickRouteRead(BaseModel):
    id: int
    batch_id: int
    total_distance_meters: float
    estimated_minutes: float
    algorithm: str
    created_at: datetime
    steps: List[PickRouteStepRead] = []

    model_config = ConfigDict(from_attributes=True)

