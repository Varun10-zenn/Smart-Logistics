"""Batch and picking-optimization schemas."""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict


class BatchOptimizeRequest(BaseModel):
    warehouse_id: int
    order_ids: List[int] = Field(..., min_length=1)
    max_orders_per_batch: int = Field(5, ge=1, le=20)
    deadline_weight: float = Field(0.4, ge=0.0, le=1.0)
    distance_weight: float = Field(0.4, ge=0.0, le=1.0)
    capacity_weight: float = Field(0.2, ge=0.0, le=1.0)


class BatchPlan(BaseModel):
    batch_id: Optional[int] = None  # null if not yet persisted
    order_ids: List[int]
    estimated_distance: float
    estimated_time_minutes: float


class BatchOptimizeResponse(BaseModel):
    task_id: str
    warehouse_id: int
    batches: List[BatchPlan]
    explanation: str
    algorithm: str
    fallback_used: bool


class BatchRead(BaseModel):
    id: int
    batch_code: str
    warehouse_id: int
    status: str
    created_at: datetime
    order_ids: List[int] = []

    model_config = ConfigDict(from_attributes=True)


BATCH_STATUSES = Literal["created", "assigned", "in_progress", "completed", "cancelled"]


class BatchStatusUpdate(BaseModel):
    status: BATCH_STATUSES
