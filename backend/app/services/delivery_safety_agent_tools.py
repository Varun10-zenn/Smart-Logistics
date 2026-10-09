"""Tools for Delivery Safety Agent."""
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.app.services.safety_service import get_score_by_delivery, list_events
from backend.app.services.delivery_service import get_delivery, get_eta
from backend.app.models.delivery import Delivery

ALLOWED_SAFETY_ROLES = {"admin", "fleet_manager", "driver"}

def calculate_safety_score(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    delivery_id = payload.get("delivery_id")
    if not delivery_id:
        return {"success": False, "error": "Missing delivery_id"}
    try:
        score = get_score_by_delivery(db, delivery_id)
        events = list_events(db, delivery_id=delivery_id)
        return {
            "success": True,
            "safety_score": score.score,
            "speed_score": score.speed_score,
            "braking_score": score.braking_score,
            "acceleration_score": score.acceleration_score,
            "route_score": score.route_score,
            "events_count": events.total,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def calculate_delivery_eta(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    delivery_id = payload.get("delivery_id")
    if not delivery_id:
        return {"success": False, "error": "Missing delivery_id"}
    try:
        eta_resp = get_eta(db, delivery_id)
        return {
            "success": True,
            "eta": eta_resp.eta.isoformat(),
            "traffic_factor": eta_resp.traffic_factor,
            "weather_factor": eta_resp.weather_factor,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

SAFETY_TOOL_REGISTRY = {
    "calculate_safety_score": calculate_safety_score,
    "calculate_delivery_eta": calculate_delivery_eta,
}

def dispatch_safety_tool(db: Session, tool_name: str, payload: Dict[str, Any], user_role: str) -> Dict[str, Any]:
    if user_role not in ALLOWED_SAFETY_ROLES:
        return {"success": False, "error": "Unauthorized role"}
    if tool_name not in SAFETY_TOOL_REGISTRY:
        return {"success": False, "error": "Tool not found"}
    return SAFETY_TOOL_REGISTRY[tool_name](db, payload)
