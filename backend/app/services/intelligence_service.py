"""
Intelligence service — allowlisted operation routing only.

SECURITY: Only explicitly mapped operations are executed.
No arbitrary SQL, arbitrary Python, or arbitrary tool names are permitted.
"""
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.intelligence import AIRecommendation, Forecast
from backend.app.schemas.common import make_page
from backend.app.schemas.intelligence import (
    IntelligenceRunRequest, IntelligenceRunResponse,
    RecommendationRead, ForecastRead,
)

# ---------------------------------------------------------------------------
# Allowlisted operation stub handlers
# ---------------------------------------------------------------------------

def _warehouse_batch_recommendation(context: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """
    Stub: warehouse_batch_recommendation
    Returns a placeholder batch grouping suggestion.
    Real optimization (OR-Tools) implemented in Phase 3.
    """
    warehouse_id = context.get("warehouse_id")
    order_count = context.get("order_count", 0)
    return {
        "warehouse_id": warehouse_id,
        "recommended_batch_size": 5,
        "estimated_batches": max(1, order_count // 5),
        "algorithm": "fifo_stub",
        "note": "Optimization algorithm will be integrated in Phase 3.",
    }


def _delivery_safety_analysis(context: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """
    Executes delivery safety analysis using DeliverySafetyAgent.
    """
    from backend.app.services.delivery_safety_agent import DeliverySafetyAgent, AgentSafetyRequest
    from backend.app.models.user import User
    
    delivery_id = context.get("delivery_id")
    user_id = context.get("_internal_user_id")
    
    user = db.query(User).filter(User.id == user_id).first()
    user_role = user.role.code if user and user.role else "driver"
    
    agent = DeliverySafetyAgent()
    req = AgentSafetyRequest(
        delivery_id=delivery_id,
        operation="calculate_safety_score",
        payload={}
    )
    
    resp = agent.execute_request(db, req, user_role)
    if not resp.success:
        raise ValueError(resp.explanation)
        
    return {
        "delivery_id": delivery_id,
        "safety_score": resp.tool_result.get("safety_score"),
        "events_count": resp.tool_result.get("events_count"),
        "algorithm": "deterministic_agent",
        "note": resp.explanation,
    }


def _ev_charging_recommendation(context: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """
    Stub: ev_charging_recommendation
    Returns a placeholder charging recommendation.
    Real multi-objective optimization implemented in Phase 3.
    """
    vehicle_id = context.get("vehicle_id")
    current_soc = context.get("current_soc_percent", 50)
    return {
        "vehicle_id": vehicle_id,
        "current_soc_percent": current_soc,
        "recommendation": "Find nearest operational charging station.",
        "algorithm": "nearest_stub",
        "note": "Multi-objective optimization will be integrated in Phase 3.",
    }


# Registry maps allowed operation names to their handlers
_OPERATION_REGISTRY = {
    "warehouse_batch_recommendation": _warehouse_batch_recommendation,
    "delivery_safety_analysis": _delivery_safety_analysis,
    "ev_charging_recommendation": _ev_charging_recommendation,
}


def run_operation(db: Session, data: IntelligenceRunRequest, user_id: int) -> IntelligenceRunResponse:
    """
    Route an allowlisted intelligence operation to its approved service handler.

    The operation string is validated by Pydantic before this function is called,
    so only allowlisted operations ever reach this point.
    """
    handler = _OPERATION_REGISTRY.get(data.operation)
    if handler is None:
        # Should never reach here due to Pydantic Literal validation, but defensive check
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": f"Operation '{data.operation}' is not supported.", "details": {}},
        )

    task_id = str(uuid.uuid4())
    start = time.perf_counter()

    try:
        data.context["_internal_user_id"] = user_id
        result = handler(data.context, db)
        status = "fallback"  # All Phase 2 operations are stubs
        explanation = f"Operation '{data.operation}' executed via Phase 2 service stub. Full implementation in Phase 3."
        fallback_used = True
    except HTTPException:
        raise
    except Exception as exc:
        result = {}
        status = "failed"
        explanation = "Operation failed. Fallback unavailable."
        fallback_used = True

    latency_ms = int((time.perf_counter() - start) * 1000)

    # Record in ai_recommendations for audit trail
    rec = AIRecommendation(
        agent_name=f"{data.operation}_agent",
        recommendation_type=data.operation,
        input_snapshot=data.context,
        output_payload=result,
        explanation=explanation,
        confidence_score=None,
        fallback_used=fallback_used,
        model_version="stub-v0.1",
    )
    db.add(rec)
    db.commit()

    return IntelligenceRunResponse(
        task_id=task_id,
        operation=data.operation,
        status=status,
        result=result,
        explanation=explanation,
        confidence=None,
        fallback_used=fallback_used,
        model_version="stub-v0.1",
        latency_ms=latency_ms,
    )


def list_recommendations(db: Session, page: int = 1, page_size: int = 20,
                          operation_type: str = None):
    q = db.query(AIRecommendation)
    if operation_type:
        q = q.filter(AIRecommendation.recommendation_type == operation_type)
    total = q.count()
    recs = q.order_by(AIRecommendation.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [RecommendationRead(
        id=r.id,
        agent_name=r.agent_name,
        recommendation_type=r.recommendation_type,
        input_snapshot=r.input_snapshot or {},
        output=r.output_payload or {},
        explanation=r.explanation,
        confidence=float(r.confidence_score) if r.confidence_score is not None else None,
        model_version=r.model_version,
        created_at=r.created_at,
    ) for r in recs]
    return make_page(items, total, page, page_size)


def list_forecasts(db: Session, page: int = 1, page_size: int = 20,
                   forecast_type: str = None):
    q = db.query(Forecast)
    if forecast_type:
        q = q.filter(Forecast.forecast_type == forecast_type)
    total = q.count()
    forecasts = q.order_by(Forecast.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [ForecastRead(
        id=f.id,
        forecast_type=f.forecast_type,
        entity_id=f.warehouse_id or f.station_id,
        forecast_time=f.target_timestamp,
        predicted_value=float(f.predicted_value),
        lower_bound=float(f.lower_bound),
        upper_bound=float(f.upper_bound),
        model_name=f.model_name,
        model_version=f.model_version,
        created_at=f.created_at,
    ) for f in forecasts]
    return make_page(items, total, page, page_size)
