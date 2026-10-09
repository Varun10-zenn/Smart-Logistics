"""Customer shop router — browsing products, checkout, and order status tracking."""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import require_role
from backend.app.models.user import User
from backend.app.schemas.shop import ShopProductsResponse, CheckoutRequest, CustomerOrderRead
from backend.app.services import shop_service

router = APIRouter(prefix="/shop", tags=["Customer Shop"])


@router.get("/products", response_model=ShopProductsResponse, summary="Get products with available stock from nearest warehouse")
def get_products(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    current_user: User = Depends(require_role("customer", "admin")),
    db: Session = Depends(get_db),
):
    return shop_service.get_shop_products(db, lat, lon)


@router.post("/checkout", response_model=CustomerOrderRead, status_code=201, summary="Customer checkout")
def checkout(
    data: CheckoutRequest,
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    return shop_service.checkout(db, current_user, data)


@router.get("/orders", response_model=List[CustomerOrderRead], summary="List customer's own orders")
def list_orders(
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    return shop_service.list_customer_orders(db, current_user.id)


@router.get("/orders/{order_id}", response_model=CustomerOrderRead, summary="Get details for customer's own order")
def get_order(
    order_id: int,
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    return shop_service.get_customer_order(db, current_user.id, order_id)
