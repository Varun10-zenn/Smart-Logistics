"""Delivery Safety Agent implementation."""
import time
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.app.models.intelligence import AIRecommendation
from backend.app.services.delivery_safety_agent_tools import (
    dispatch_safety_tool,
    SAFETY_TOOL_REGISTRY,
    ALLOWED_SAFETY_ROLES,
)

logger = logging.getLogger(__name__)

class AgentSafetyRequest(BaseModel):
    delivery_id: int
    operation: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    user_prompt: Optional[str] = None

class AgentSafetyResponse(BaseModel):
    success: bool
    operation: str
    tool_result: Dict[str, Any]
    explanation: str
    recommendation_summary: Dict[str, Any]
    fallback_used: bool
    llm_used: bool
    latency_ms: int
    confidence_score: float

class DeliverySafetyAgent:
    name = "delivery_safety_agent"
    version = "1.0.0"
    supported_tasks = list(SAFETY_TOOL_REGISTRY.keys())
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def execute_request(self, db: Session, request: AgentSafetyRequest, user_role: str) -> AgentSafetyResponse:
        start_time = time.perf_counter()

        if user_role not in ALLOWED_SAFETY_ROLES:
            return self._fail_response(request.operation, "Unauthorized role", start_time)

        if request.operation not in SAFETY_TOOL_REGISTRY:
            return self._fail_response(request.operation, "Unknown tool", start_time)

        payload = dict(request.payload)
        payload["delivery_id"] = request.delivery_id

        tool_result = dispatch_safety_tool(db, request.operation, payload, user_role)
        tool_success = tool_result.get("success", False)

        if not tool_success:
            return self._fail_response(request.operation, tool_result.get("error", "Unknown error"), start_time)

        explanation = f"Successfully executed {request.operation} for delivery {request.delivery_id}."
        if request.operation == "calculate_safety_score":
            explanation = f"Delivery {request.delivery_id} has a safety score of {tool_result.get('safety_score')}."

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Audit
        try:
            rec = AIRecommendation(
                agent_name=self.name,
                recommendation_type=request.operation,
                input_snapshot=request.model_dump(),
                output_payload={"tool_result": tool_result},
                explanation=explanation,
                confidence_score=0.95,
                fallback_used=True,
                model_version=self.version,
            )
            db.add(rec)
            db.commit()
        except Exception as exc:
            logger.error(f"Audit fail: {exc}")
            db.rollback()

        return AgentSafetyResponse(
            success=True,
            operation=request.operation,
            tool_result=tool_result,
            explanation=explanation,
            recommendation_summary=tool_result,
            fallback_used=True,
            llm_used=False,
            latency_ms=latency_ms,
            confidence_score=0.95,
        )

    def _fail_response(self, operation: str, error: str, start_time: float) -> AgentSafetyResponse:
        return AgentSafetyResponse(
            success=False,
            operation=operation,
            tool_result={"error": error},
            explanation=error,
            recommendation_summary={},
            fallback_used=True,
            llm_used=False,
            latency_ms=int((time.perf_counter() - start_time) * 1000),
            confidence_score=0.0
        )
