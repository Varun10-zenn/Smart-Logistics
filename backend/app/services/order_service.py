"""Order service."""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.models.order import Order, OrderItem
from backend.app.models.warehouse import Product
from backend.app.models.batch import BatchOrder
from backend.app.schemas.common import make_page
from backend.app.schemas.order import OrderCreate, OrderRead, OrderStatusUpdate, OrderItemRead

PRIORITY_MAP = {"low": 1, "normal": 1, "high": 2, "urgent": 3}
PRIORITY_REVERSE = {1: "normal", 2: "high", 3: "urgent", 0: "low"}


def _to_read(order: Order) -> OrderRead:
    items = [
        OrderItemRead(id=i.id, product_id=i.product_id, quantity=i.quantity)
        for i in order.items
    ]
    return OrderRead(
        id=order.id,
        order_number=order.order_number,
        warehouse_id=order.warehouse_id,
        customer_name=order.customer_name,
        customer_lat=float(order.destination_lat),
        customer_lon=float(order.destination_lon),
        created_at=order.created_at,
        promised_at=order.promised_at,
        priority=PRIORITY_REVERSE.get(order.priority, "normal"),
        status=order.status,
        items=items,
    )


def list_orders(db: Session, page: int = 1, page_size: int = 20,
                warehouse_id: int = None, status: str = None, priority: str = None):
    q = db.query(Order)
    if warehouse_id:
        q = q.filter(Order.warehouse_id == warehouse_id)
    if status:
        q = q.filter(Order.status == status)
    if priority:
        # Convert string priority to int if needed
        p_val = PRIORITY_MAP.get(priority) if isinstance(priority, str) else priority
        if p_val:
            q = q.filter(Order.priority == p_val)
    total = q.count()
    orders = q.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_to_read(o) for o in orders], total, page, page_size)


def create_order(db: Session, data: OrderCreate) -> OrderRead:
    order_number = data.order_number or f"ORD-{uuid.uuid4().hex[:10].upper()}"

    existing = db.query(Order).filter(Order.order_number == order_number).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"code": "DUPLICATE_RESOURCE", "message": f"Order number '{order_number}' already exists.", "details": {}}
        )

    order = Order(
        order_number=order_number,
        warehouse_id=data.warehouse_id,
        customer_name=data.customer_name,
        destination_address=data.destination_address or "",
        destination_lat=data.customer_lat,
        destination_lon=data.customer_lon,
        promised_at=data.promised_at,
        priority=PRIORITY_MAP.get(data.priority, 1),
        status="pending",
    )
    db.add(order)
    db.flush()  # get order.id

    for item_data in data.items:
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        if product is None:
            db.rollback()
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"Product {item_data.product_id} not found.", "details": {}})
        item = OrderItem(
            order_id=order.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit_price=float(product.price),
        )
        db.add(item)

    db.commit()
    db.refresh(order)
    return _to_read(order)


def get_order(db: Session, order_id: int) -> OrderRead:
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Order not found.", "details": {}})
    return _to_read(order)


def update_order_status(db: Session, order_id: int, data: OrderStatusUpdate) -> OrderRead:
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Order not found.", "details": {}})
    order.status = data.status
    db.commit()
    db.refresh(order)
    return _to_read(order)


def delete_order(db: Session, order_id: int) -> None:
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Order not found.", "details": {}})

    if order.status != "pending":
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete order ID {order_id}: status is '{order.status}'. Only pending orders can be deleted.", "details": {}}
        )

    bo_count = db.query(BatchOrder).filter(BatchOrder.order_id == order_id).count()
    if bo_count > 0:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete order ID {order_id}: referenced by {bo_count} batch order associations.", "details": {}}
        )

    try:
        db.delete(order)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete order: {str(err)}", "details": {}}
        )
