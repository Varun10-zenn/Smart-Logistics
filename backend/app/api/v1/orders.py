"""Orders router."""
from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import require_role
from backend.app.schemas.common import Page
from backend.app.schemas.order import OrderCreate, OrderRead, OrderStatusUpdate
from backend.app.services import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])

_READ_ROLES = ("admin", "warehouse_operator", "fleet_manager")
_WRITE_ROLES = ("admin", "warehouse_operator")


@router.get("", response_model=Page[OrderRead])
def list_orders(
    page: int = 1, page_size: int = 20,
    warehouse_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return order_service.list_orders(db, page, page_size, warehouse_id, status, priority)


@router.post("", response_model=OrderRead, status_code=201)
def create_order(
    data: OrderCreate,
    current_user=Depends(require_role(*_WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    return order_service.create_order(db, data)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: int,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return order_service.get_order(db, order_id)


@router.patch("/{order_id}/status", response_model=OrderRead)
def update_order_status(
    order_id: int, data: OrderStatusUpdate,
    current_user=Depends(require_role(*_WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    return order_service.update_order_status(db, order_id, data)


@router.delete("/{order_id}", status_code=204)
def delete_order(
    order_id: int,
    current_user=Depends(require_role(*_WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    order_service.delete_order(db, order_id)
