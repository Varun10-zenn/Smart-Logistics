"""Stock service — handles stock availability calculations."""
from typing import Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.warehouse import Inventory
from backend.app.models.order import Order, OrderItem


def get_available_stock_map(db: Session, warehouse_id: int) -> Dict[int, int]:
    """
    Calculate available stock per product for a given warehouse.
    Available stock = Physical Inventory SUM(quantity) - Reserved Order Items SUM(quantity for status in ('pending', 'batched')).
    """
    # Physical stock across storage locations in warehouse
    phys_query = (
        db.query(Inventory.product_id, func.coalesce(func.sum(Inventory.quantity), 0))
        .filter(Inventory.warehouse_id == warehouse_id)
        .group_by(Inventory.product_id)
        .all()
    )
    phys_map = {int(p_id): int(qty) for p_id, qty in phys_query}

    # Reserved stock for pending or batched orders
    res_query = (
        db.query(OrderItem.product_id, func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            Order.warehouse_id == warehouse_id,
            Order.status.in_(["pending", "batched"])
        )
        .group_by(OrderItem.product_id)
        .all()
    )
    res_map = {int(p_id): int(qty) for p_id, qty in res_query}

    avail_map = {}
    for p_id, phys_qty in phys_map.items():
        reserved = res_map.get(p_id, 0)
        avail_map[p_id] = max(0, phys_qty - reserved)

    return avail_map


def get_available_stock_for_product(db: Session, warehouse_id: int, product_id: int) -> int:
    """Return available stock for a single product in a warehouse."""
    avail_map = get_available_stock_map(db, warehouse_id)
    return avail_map.get(product_id, 0)
