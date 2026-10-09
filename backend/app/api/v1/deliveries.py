"""Deliveries router — with own-record enforcement for drivers."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.schemas.common import Page, make_page
from backend.app.schemas.delivery import DeliveryCreate, DeliveryRead, DeliveryStatusUpdate, ETAResponse, DeliveryRouteRead
from backend.app.services import delivery_service, routing_service

router = APIRouter(prefix="/deliveries", tags=["Deliveries"])


def _get_driver_id_for_user(current_user, db: Session) -> Optional[int]:
    """Returns driver_id if user is a driver, else None."""
    if current_user.role.code == "driver":
        from backend.app.models.delivery import Driver
        driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
        return driver.id if driver else None
    return None


@router.get("", response_model=Page[DeliveryRead])
def list_deliveries(
    page: int = 1, page_size: int = 20,
    status: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    # Drivers see only own deliveries
    if role == "driver":
        driver_id = _get_driver_id_for_user(current_user, db)
        if driver_id is None:
            return make_page([], 0, page, page_size)
    else:
        driver_id = None
    return delivery_service.list_deliveries(db, page, page_size, driver_id, status)


@router.post("", response_model=DeliveryRead, status_code=201)
def create_delivery(
    data: DeliveryCreate,
    current_user=Depends(require_role("admin", "warehouse_operator", "fleet_manager")),
    db: Session = Depends(get_db),
):
    return delivery_service.create_delivery(db, data)


@router.get("/{delivery_id}", response_model=DeliveryRead)
def get_delivery(
    delivery_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "warehouse_operator", "fleet_manager", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    result = delivery_service.get_delivery(db, delivery_id)
    # Driver can only see own delivery
    if role == "driver":
        driver_id = _get_driver_id_for_user(current_user, db)
        if result.driver_id != driver_id:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "You can only view your own deliveries.", "details": {}})
    return result


@router.patch("/{delivery_id}/status", response_model=DeliveryRead)
def update_delivery_status(
    delivery_id: int, data: DeliveryStatusUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    # Driver can only update own delivery
    if role == "driver":
        existing = delivery_service.get_delivery(db, delivery_id)
        driver_id = _get_driver_id_for_user(current_user, db)
        if existing.driver_id != driver_id:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "You can only update your own deliveries.", "details": {}})
    return delivery_service.update_delivery_status(db, delivery_id, data)


@router.get("/{delivery_id}/eta", response_model=ETAResponse)
def get_eta(
    delivery_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    return delivery_service.get_eta(db, delivery_id)


@router.post("/{delivery_id}/route", response_model=DeliveryRouteRead, status_code=201)
def generate_route(
    delivery_id: int,
    current_user=Depends(require_role("admin", "fleet_manager")),
    db: Session = Depends(get_db),
):
    return routing_service.generate_route_for_delivery(db, delivery_id, overwrite=True)


@router.get("/{delivery_id}/route", response_model=DeliveryRouteRead)
def get_route(
    delivery_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    
    delivery = delivery_service.get_delivery(db, delivery_id)
    if role == "driver":
        driver_id = _get_driver_id_for_user(current_user, db)
        if delivery.driver_id != driver_id:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "You can only view your own deliveries.", "details": {}})
    
    from backend.app.models.delivery import DeliveryRoute
    route = db.query(DeliveryRoute).filter(DeliveryRoute.delivery_id == delivery_id).first()
    if not route:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Route not found.", "details": {}})
    return route


# ─── RIDER ENDPOINTS ──────────────────────────────────────────────────────────
@router.get("/rider/active", summary="Get active deliveries for the logged-in rider")
def get_rider_active_deliveries(
    current_user=Depends(require_role("driver", "admin")),
    db: Session = Depends(get_db),
):
    from backend.app.services import delivery_service
    return delivery_service.get_rider_deliveries(db, current_user)


@router.post("/{delivery_id}/start", summary="Start delivery (rider only)")
def start_rider_delivery(
    delivery_id: int,
    current_user=Depends(require_role("driver", "admin")),
    db: Session = Depends(get_db),
):
    from backend.app.services import delivery_service
    return delivery_service.start_delivery(db, delivery_id, current_user)


@router.post("/{delivery_id}/stops/{stop_id}/deliver", summary="Mark delivery stop as delivered (rider only)")
def deliver_rider_stop(
    delivery_id: int,
    stop_id: int,
    current_user=Depends(require_role("driver", "admin")),
    db: Session = Depends(get_db),
):
    from backend.app.services import delivery_service
    return delivery_service.deliver_stop(db, delivery_id, stop_id, current_user)


@router.get("/{delivery_id}/charging-recommendation", summary="Get low-battery charging recommendation for delivery")
def get_charging_recommendation(
    delivery_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})

    delivery = delivery_service.get_delivery(db, delivery_id)
    if role == "driver":
        driver_id = _get_driver_id_for_user(current_user, db)
        if delivery.driver_id != driver_id:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "You can only view your own deliveries.", "details": {}})

    from backend.app.models.delivery import Delivery
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not d or not d.charging_recommendation:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "No charging recommendation available for this delivery.", "details": {}})

    import json
    return json.loads(d.charging_recommendation)


# ─── SIMULATION ENDPOINTS ───────────────────────────────────────────────────
from pydantic import BaseModel

class SimulationStartRequest(BaseModel):
    profile: Optional[str] = "normal"


@router.post("/{delivery_id}/simulation/start", summary="Start rider delivery route simulation")
async def start_simulation(
    delivery_id: int,
    body: SimulationStartRequest = SimulationStartRequest(),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})

    delivery = delivery_service.get_delivery(db, delivery_id)
    if role == "driver":
        driver_id = _get_driver_id_for_user(current_user, db)
        if delivery.driver_id != driver_id:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Drivers can only simulate their own assigned deliveries.", "details": {}})

    from backend.app.services import simulator_service
    return simulator_service.start_simulation(db, delivery_id, profile=body.profile or "normal")


@router.post("/{delivery_id}/simulation/stop", summary="Stop rider delivery route simulation")
async def stop_simulation(
    delivery_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})

    from backend.app.services import simulator_service
    return simulator_service.stop_simulation(delivery_id)


@router.get("/{delivery_id}/simulation", summary="Get status of rider delivery route simulation")
async def get_simulation_status(
    delivery_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role not in ("admin", "fleet_manager", "driver"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})

    from backend.app.services import simulator_service
    return simulator_service.get_simulation_status(delivery_id)


