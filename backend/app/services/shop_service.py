"""Shop service — handles customer product browsing, checkout, and order status tracking."""
import math
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.user import User
from backend.app.models.warehouse import Warehouse, Product, Inventory
from backend.app.models.order import Order, OrderItem
from backend.app.models.delivery import Delivery
from backend.app.services.stock_service import get_available_stock_map
from backend.app.schemas.shop import (
    ShopProductItem, ShopProductsResponse, CheckoutRequest, CustomerOrderRead, TimelineStep
)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def get_shop_products(db: Session, lat: float, lon: float) -> ShopProductsResponse:
    """Return products with available stock from the nearest warehouse within SERVICE_RADIUS_KM."""
    warehouses = db.query(Warehouse).all()
    candidates = []
    for wh in warehouses:
        dist = haversine_km(lat, lon, float(wh.latitude), float(wh.longitude))
        if dist <= settings.SERVICE_RADIUS_KM:
            candidates.append((dist, wh))

    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"No warehouse found within service radius of {settings.SERVICE_RADIUS_KM} km.",
                "details": {}
            }
        )

    candidates.sort(key=lambda x: x[0])

    selected_wh = None
    selected_dist = 0.0
    stock_map = {}

    for dist, wh in candidates:
        avail_map = get_available_stock_map(db, wh.id)
        if sum(avail_map.values()) > 0:
            selected_wh = wh
            selected_dist = dist
            stock_map = avail_map
            break

    if selected_wh is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"No warehouse with available stock found within service radius of {settings.SERVICE_RADIUS_KM} km.",
                "details": {}
            }
        )

    all_products = db.query(Product).order_by(Product.name).all()
    product_items = []
    for p in all_products:
        product_items.append(ShopProductItem(
            id=p.id,
            sku=p.sku,
            name=p.name,
            category=p.category,
            unit_weight_kg=float(p.unit_weight_kg),
            unit_volume_cbm=float(p.unit_volume_cbm),
            price=float(p.price),
            available_quantity=stock_map.get(p.id, 0),
        ))

    return ShopProductsResponse(
        warehouse_id=selected_wh.id,
        warehouse_name=selected_wh.name,
        distance_km=round(selected_dist, 2),
        products=product_items,
    )


def checkout(db: Session, customer_user: User, data: CheckoutRequest) -> CustomerOrderRead:
    """Fulfill order from the nearest warehouse that has stock for ALL items in a single transaction."""
    warehouses = db.query(Warehouse).all()
    candidates = []
    for wh in warehouses:
        dist = haversine_km(data.lat, data.lon, float(wh.latitude), float(wh.longitude))
        if dist <= settings.SERVICE_RADIUS_KM:
            candidates.append((dist, wh))

    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "OUT_OF_SERVICE_AREA",
                "message": f"No warehouse found within service radius of {settings.SERVICE_RADIUS_KM} km.",
                "details": {}
            }
        )

    candidates.sort(key=lambda x: x[0])

    target_wh = None
    for dist, wh in candidates:
        avail_map = get_available_stock_map(db, wh.id)
        can_fulfill = True
        for item in data.items:
            if avail_map.get(item.product_id, 0) < item.quantity:
                can_fulfill = False
                break
        if can_fulfill:
            target_wh = wh
            break

    if target_wh is None:
        # Build list of short SKUs across nearest warehouse
        nearest_wh = candidates[0][1]
        avail_map = get_available_stock_map(db, nearest_wh.id)
        short_items = []
        for item in data.items:
            avail = avail_map.get(item.product_id, 0)
            if avail < item.quantity:
                p = db.query(Product).filter(Product.id == item.product_id).first()
                short_items.append({
                    "product_id": item.product_id,
                    "sku": p.sku if p else "UNKNOWN",
                    "requested": item.quantity,
                    "available": avail
                })
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INSUFFICIENT_STOCK",
                "message": "Insufficient stock to fulfill all requested items.",
                "details": {"short_items": short_items}
            }
        )

    # Perform creation with row locks
    try:
        # Lock inventory rows for this warehouse if using MySQL
        db.query(Inventory).filter(
            Inventory.warehouse_id == target_wh.id,
            Inventory.product_id.in_([i.product_id for i in data.items])
        ).with_for_update().all()

        # Re-verify stock inside transaction
        avail_map = get_available_stock_map(db, target_wh.id)
        for item in data.items:
            if avail_map.get(item.product_id, 0) < item.quantity:
                p = db.query(Product).filter(Product.id == item.product_id).first()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "INSUFFICIENT_STOCK",
                        "message": f"Stock conflict for product {p.sku if p else item.product_id}.",
                        "details": {}
                    }
                )

        order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"
        order = Order(
            order_number=order_number,
            warehouse_id=target_wh.id,
            customer_id=customer_user.id,
            customer_name=customer_user.full_name or customer_user.email,
            destination_address=data.address,
            destination_lat=data.lat,
            destination_lon=data.lon,
            priority=1,
            status="pending",
            promised_at=datetime.utcnow() + timedelta(hours=2),
        )
        db.add(order)
        db.flush()

        for item_data in data.items:
            prod = db.query(Product).filter(Product.id == item_data.product_id).first()
            if prod is None:
                db.rollback()
                raise HTTPException(
                    status_code=404,
                    detail={"code": "NOT_FOUND", "message": f"Product {item_data.product_id} not found.", "details": {}}
                )
            order_item = OrderItem(
                order_id=order.id,
                product_id=prod.id,
                quantity=item_data.quantity,
                unit_price=float(prod.price),
            )
            db.add(order_item)

        db.commit()
        db.refresh(order)
        return _to_customer_order_read(db, order)
    except Exception as exc:
        db.rollback()
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(
            status_code=500,
            detail={"code": "INTERNAL_ERROR", "message": str(exc), "details": {}}
        )


def _to_customer_order_read(db: Session, order: Order) -> CustomerOrderRead:
    # Build status timeline derived from order and delivery status
    delivery = db.query(Delivery).filter(Delivery.batch_id == (order.batch_association.batch_id if order.batch_association else None)).first() if order.batch_association else None
    
    st = order.status
    del_st = delivery.status if delivery else None

    placed = True
    packing = st in ["batched", "picking", "picked", "out_for_delivery", "in_transit", "delivered"]
    picked = st in ["picking", "picked", "out_for_delivery", "in_transit", "delivered"]
    out_for_delivery = del_st in ["in_transit", "delivered"] or st in ["out_for_delivery", "in_transit", "delivered"]
    delivered = st == "delivered" or del_st == "delivered"

    timeline = [
        TimelineStep(step="placed", completed=placed, timestamp=order.created_at),
        TimelineStep(step="packing", completed=packing),
        TimelineStep(step="picked", completed=picked),
        TimelineStep(step="out_for_delivery", completed=out_for_delivery),
        TimelineStep(step="delivered", completed=delivered),
    ]

    items_list = []
    for item in order.items:
        items_list.append({
            "product_id": item.product_id,
            "sku": item.product.sku if item.product else "UNKNOWN",
            "name": item.product.name if item.product else "UNKNOWN",
            "quantity": item.quantity,
            "unit_price": float(item.unit_price)
        })

    wh = order.warehouse

    # Extended Tracking Data
    rider_first_name = None
    vehicle_type_name = None
    stop_eta = None
    stops_before = None
    route_geometry = None
    rider_last_lat = None
    rider_last_lon = None

    if delivery:
        if delivery.driver and delivery.driver.user:
            rider_first_name = delivery.driver.user.full_name.split()[0]
        if delivery.vehicle and delivery.vehicle.vehicle_type:
            vehicle_type_name = delivery.vehicle.vehicle_type.type_name

        from backend.app.models.delivery import DeliveryStop, DeliveryRoute
        from backend.app.models.telemetry import TelemetryEvent

        stops = db.query(DeliveryStop).filter(DeliveryStop.delivery_id == delivery.id).order_by(DeliveryStop.stop_sequence).all()
        target_seq = None
        for i, s in enumerate(stops):
            if s.order_id == order.id:
                stop_eta = s.estimated_arrival
                target_seq = s.stop_sequence
                # Stops before this order that are not delivered yet
                stops_before = sum(1 for prev in stops[:i] if prev.status != "delivered")
                break

        route = db.query(DeliveryRoute).filter(DeliveryRoute.delivery_id == delivery.id).first()
        if route:
            route_geometry = route.route_geometry

        # Latest telemetry for rider position
        if delivery.vehicle_id:
            latest_telem = db.query(TelemetryEvent).filter(TelemetryEvent.vehicle_id == delivery.vehicle_id).order_by(TelemetryEvent.timestamp.desc()).first()
            if latest_telem:
                rider_last_lat = float(latest_telem.latitude)
                rider_last_lon = float(latest_telem.longitude)

    return CustomerOrderRead(
        id=order.id,
        order_number=order.order_number,
        warehouse_id=order.warehouse_id,
        warehouse_name=wh.name if wh else "UNKNOWN",
        customer_name=order.customer_name,
        destination_address=order.destination_address,
        customer_lat=float(order.destination_lat),
        customer_lon=float(order.destination_lon),
        status=order.status,
        priority="normal",
        created_at=order.created_at,
        promised_at=order.promised_at,
        timeline=timeline,
        items=items_list,
        delivery_status=del_st,
        rider_first_name=rider_first_name,
        vehicle_type=vehicle_type_name,
        stop_eta=stop_eta,
        stops_before=stops_before,
        route_geometry=route_geometry,
        rider_last_lat=rider_last_lat,
        rider_last_lon=rider_last_lon,
    )


def list_customer_orders(db: Session, customer_id: int) -> List[CustomerOrderRead]:
    orders = db.query(Order).filter(Order.customer_id == customer_id).order_by(Order.created_at.desc()).all()
    return [_to_customer_order_read(db, o) for o in orders]


def get_customer_order(db: Session, customer_id: int, order_id: int) -> CustomerOrderRead:
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None or order.customer_id != customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Order not found.", "details": {}}
        )
    return _to_customer_order_read(db, order)
