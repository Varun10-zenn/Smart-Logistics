"""Picking router."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import require_role
from backend.app.schemas.picking import PickOptimizeRequest, PickRouteRead
from backend.app.services import picking_service

router = APIRouter(prefix="/picking", tags=["Picking"])


@router.post("/optimize", response_model=PickRouteRead)
def optimize_pick_route(
    data: PickOptimizeRequest,
    current_user=Depends(require_role("admin", "warehouse_operator")),
    db: Session = Depends(get_db),
):
    return picking_service.optimize_pick_route(db, data)


@router.get("/routes/{route_id}", response_model=PickRouteRead)
def get_pick_route(
    route_id: int,
    current_user=Depends(require_role("admin", "warehouse_operator", "fleet_manager")),
    db: Session = Depends(get_db),
):
    return picking_service.get_pick_route(db, route_id)


steps_router = APIRouter(prefix="/pick-route-steps", tags=["Picking Steps"])


@steps_router.post("/{step_id}/complete", summary="Mark pick route step completed and deduct stock")
def complete_pick_route_step(
    step_id: int,
    current_user=Depends(require_role("admin", "warehouse_operator")),
    db: Session = Depends(get_db),
):
    if current_user.role.code == "warehouse_operator":
        from fastapi import HTTPException
        from backend.app.models.batch import PickRouteStep, PickRoute, Batch
        step = db.query(PickRouteStep).filter(PickRouteStep.id == step_id).first()
        if not step:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"Pick route step {step_id} not found.", "details": {}})
        pick_route = db.query(PickRoute).filter(PickRoute.id == step.pick_route_id).first()
        batch = db.query(Batch).filter(Batch.id == pick_route.batch_id).first() if pick_route else None
        if not batch or batch.warehouse_id != current_user.warehouse_id:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "Access forbidden: step belongs to another warehouse.", "details": {}}
            )
    return picking_service.complete_pick_route_step(db, step_id)

