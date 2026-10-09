"""Intelligence schemas — strictly allowlisted operations only."""
from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


# Approved operations enum — Pydantic rejects anything outside this list at validation time
AllowedOperation = Literal[
    "warehouse_batch_recommendation",
    "delivery_safety_analysis",
    "ev_charging_recommendation",
]


class IntelligenceRunRequest(BaseModel):
    operation: AllowedOperation = Field(
        ...,
        description=(
            "The intelligence operation to execute. Must be one of: "
            "warehouse_batch_recommendation, delivery_safety_analysis, ev_charging_recommendation"
        ),
    )
    context: Dict[str, Any] = Field(default_factory=dict)


class IntelligenceRunResponse(BaseModel):
    task_id: str
    operation: str
    status: Literal["completed", "failed", "fallback"]
    result: Dict[str, Any]
    explanation: str
    confidence: Optional[float] = None
    fallback_used: bool
    model_version: str
    latency_ms: int


class RecommendationRead(BaseModel):
    id: int
    agent_name: str
    recommendation_type: str
    input_snapshot: Dict
    output: Dict
    explanation: str
    confidence: Optional[float] = None
    model_version: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ForecastRead(BaseModel):
    id: int
    forecast_type: str
    entity_id: Optional[int] = None
    forecast_time: datetime
    predicted_value: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    model_name: str
    model_version: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
