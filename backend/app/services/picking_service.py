"""Picking service — handles route retrieval, optimization, and step completion with stock deduction."""
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.batch import PickRoute, PickRouteStep, Batch, BatchOrder
from backend.app.models.warehouse import Inventory, StorageLocation, WarehouseNode, Product
from backend.app.models.order import Order, OrderItem
from backend.app.schemas.picking import PickOptimizeRequest, PickRouteRead, PickRouteStepRead


def _to_step_read(s: PickRouteStep, db: Session) -> PickRouteStepRead:
    loc = db.query(StorageLocation).filter(StorageLocation.id == s.location_id).first()
    node = db.query(WarehouseNode).filter(WarehouseNode.id == loc.node_id).first() if loc else None
    product = db.query(Product).filter(Product.id == s.product_id).first()
    return PickRouteStepRead(
        id=s.id,
        step_number=s.step_number,
        location_id=s.location_id,
        location_code=loc.location_code if loc else "UNKNOWN",
        node_id=node.id if node else 0,
        product_id=s.product_id,
        product_sku=product.sku if product else "UNKNOWN",
        product_name=product.name if product else "UNKNOWN",
        quantity_to_pick=s.quantity_to_pick,
        is_completed=s.is_completed,
        x_coord=float(node.x_coord) if node else 0.0,
        y_coord=float(node.y_coord) if node else 0.0,
    )


def _to_route_read(route: PickRoute, db: Session) -> PickRouteRead:
    steps = db.query(PickRouteStep).filter(PickRouteStep.pick_route_id == route.id).order_by(PickRouteStep.step_number).all()
    step_reads = [_to_step_read(s, db) for s in steps]
    return PickRouteRead(
        id=route.id,
        batch_id=route.batch_id,
        total_distance_meters=float(route.total_distance_meters),
        estimated_minutes=float(route.estimated_duration_minutes),
        algorithm=route.algorithm_used,
        created_at=route.created_at,
        steps=step_reads,
    )


def optimize_pick_route(db: Session, data: PickOptimizeRequest) -> PickRouteRead:
    batch = db.query(Batch).filter(Batch.id == data.batch_id).first()
    if batch is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Batch not found.", "details": {}})

    # Gather all order items from this batch
    batch_order_ids = [r[0] for r in db.query(BatchOrder.order_id).filter(BatchOrder.batch_id == data.batch_id).all()]
    all_items = db.query(OrderItem).filter(OrderItem.order_id.in_(batch_order_ids)).all()

    # Build a simple ordered sequence from inventory locations
    steps = []
    step_num = 1
    for item in all_items:
        inv = db.query(Inventory).filter(
            Inventory.product_id == item.product_id,
            Inventory.warehouse_id == batch.warehouse_id
        ).first()
        if inv:
            steps.append((step_num, inv.location_id, item.product_id, item.quantity))
            step_num += 1

    route = PickRoute(
        batch_id=data.batch_id,
        total_distance_meters=0.0,
        estimated_duration_minutes=float(len(steps) * 2),
        algorithm_used="sequential_stub",
    )
    db.add(route)
    db.flush()

    for sn, loc_id, prod_id, qty in steps:
        db.add(PickRouteStep(
            pick_route_id=route.id,
            step_number=sn,
            location_id=loc_id,
            product_id=prod_id,
            quantity_to_pick=qty,
            is_completed=False,
        ))

    db.commit()
    db.refresh(route)
    return _to_route_read(route, db)


def get_pick_route(db: Session, route_id: int) -> PickRouteRead:
    route = db.query(PickRoute).filter(PickRoute.id == route_id).first()
    if route is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Pick route not found.", "details": {}})
    return _to_route_read(route, db)


def get_batch_pick_route(db: Session, batch_id: int) -> PickRouteRead:
    """Get the pick route associated with a specific batch."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if batch is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"Batch {batch_id} not found.", "details": {}})
    
    route = db.query(PickRoute).filter(PickRoute.batch_id == batch_id).first()
    if route is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"Pick route for batch {batch_id} not found.", "details": {}})
    return _to_route_read(route, db)


def complete_pick_route_step(db: Session, step_id: int) -> PickRouteStepRead:
    """
    Complete a pick route step and deduct inventory stock in a single transaction.
    If already completed, returns without double deduction.
    If all steps in the batch are completed, sets Batch.status = 'completed' and Orders.status = 'picked'.
    """
    step = db.query(PickRouteStep).filter(PickRouteStep.id == step_id).first()
    if step is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"Pick route step {step_id} not found.", "details": {}})

    # Idempotent check: if already completed, do not deduct stock again
    if step.is_completed:
        return _to_step_read(step, db)

    try:
        inv = db.query(Inventory).filter(
            Inventory.location_id == step.location_id,
            Inventory.product_id == step.product_id
        ).with_for_update().first()

        avail_qty = inv.quantity if inv else 0
        if inv is None or avail_qty < step.quantity_to_pick:
            loc = db.query(StorageLocation).filter(StorageLocation.id == step.location_id).first()
            loc_code = loc.location_code if loc else str(step.location_id)
            prod = db.query(Product).filter(Product.id == step.product_id).first()
            prod_sku = prod.sku if prod else str(step.product_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "INSUFFICIENT_STOCK",
                    "message": f"Insufficient stock at location '{loc_code}' for product '{prod_sku}'. Required: {step.quantity_to_pick}, Available: {avail_qty}.",
                    "details": {}
                }
            )

        # Deduct physical stock
        inv.quantity -= step.quantity_to_pick
        step.is_completed = True

        # Check if all steps in this pick route are completed
        all_steps = db.query(PickRouteStep).filter(PickRouteStep.pick_route_id == step.pick_route_id).all()
        if all(s.is_completed for s in all_steps):
            pick_route = step.pick_route
            if pick_route and pick_route.batch_id:
                batch = db.query(Batch).filter(Batch.id == pick_route.batch_id).first()
                if batch:
                    batch.status = "completed"
                    batch.completed_at = datetime.utcnow()
                    for bo in batch.batch_orders:
                        bo.order.status = "picked"

                    # Trigger auto-handoff to create delivery, assign rider/vehicle, and generate route
                    from backend.app.services.delivery_service import auto_handoff_batch_to_delivery
                    auto_handoff_batch_to_delivery(db, batch.id)

        db.commit()
        db.refresh(step)
        return _to_step_read(step, db)
    except Exception as exc:
        db.rollback()
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(
            status_code=500,
            detail={"code": "INTERNAL_ERROR", "message": str(exc), "details": {}}
        )
