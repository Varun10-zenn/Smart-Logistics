"""Batches router."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import require_role
from backend.app.schemas.common import Page
from backend.app.schemas.batch import (
    BatchOptimizeRequest, BatchOptimizeResponse, BatchRead, BatchStatusUpdate
)
from backend.app.services import batch_service

router = APIRouter(prefix="/batches", tags=["Batches"])

_READ_ROLES = ("admin", "warehouse_operator", "fleet_manager")
_WRITE_ROLES = ("admin", "warehouse_operator")


@router.get("", response_model=Page[BatchRead])
def list_batches(
    page: int = 1, page_size: int = 20,
    warehouse_id: Optional[int] = None, status: Optional[str] = None,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    if current_user.role.code == "warehouse_operator":
        if current_user.warehouse_id:
            warehouse_id = current_user.warehouse_id
        else:
            warehouse_id = -1
    return batch_service.list_batches(db, page, page_size, warehouse_id, status)


@router.post("/optimize", response_model=BatchOptimizeResponse)
def optimize_batches(
    data: BatchOptimizeRequest,
    current_user=Depends(require_role(*_WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    return batch_service.optimize_batches(db, data)


@router.get("/{batch_id}", response_model=BatchRead)
def get_batch(
    batch_id: int,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    batch = batch_service.get_batch(db, batch_id)
    if current_user.role.code == "warehouse_operator":
        if batch.warehouse_id != current_user.warehouse_id:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "Access forbidden: batch belongs to another warehouse.", "details": {}}
            )
    return batch


@router.patch("/{batch_id}/status", response_model=BatchRead)
def update_batch_status(
    batch_id: int, data: BatchStatusUpdate,
    current_user=Depends(require_role(*_WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    return batch_service.update_batch_status(db, batch_id, data)


@router.get("/{batch_id}/pick-route", summary="Get pick route for batch")
def get_batch_pick_route(
    batch_id: int,
    current_user=Depends(require_role("admin", "warehouse_operator")),
    db: Session = Depends(get_db),
):
    if current_user.role.code == "warehouse_operator":
        from fastapi import HTTPException
        from backend.app.models.batch import Batch
        b = db.query(Batch).filter(Batch.id == batch_id).first()
        if not b or b.warehouse_id != current_user.warehouse_id:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "Access forbidden: batch belongs to another warehouse.", "details": {}}
            )
    from backend.app.services import picking_service
    return picking_service.get_batch_pick_route(db, batch_id)

