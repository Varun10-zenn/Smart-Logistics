"""Batch service — optimization is a stub for Phase 2."""
import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.batch import Batch, BatchOrder
from backend.app.schemas.common import make_page
from backend.app.schemas.batch import (
    BatchOptimizeRequest, BatchOptimizeResponse, BatchPlan,
    BatchRead, BatchStatusUpdate,
)


def _order_ids_for_batch(db: Session, batch: Batch):
    rows = db.query(BatchOrder.order_id).filter(BatchOrder.batch_id == batch.id).all()
    return [r[0] for r in rows]


def _to_read(batch: Batch, db: Session) -> BatchRead:
    return BatchRead(
        id=batch.id,
        batch_code=batch.batch_code,
        warehouse_id=batch.warehouse_id,
        status=batch.status,
        created_at=batch.created_at,
        order_ids=_order_ids_for_batch(db, batch),
    )


def list_batches(db: Session, page: int = 1, page_size: int = 20,
                 warehouse_id: int = None, status: str = None):
    q = db.query(Batch)
    if warehouse_id:
        q = q.filter(Batch.warehouse_id == warehouse_id)
    if status:
        q = q.filter(Batch.status == status)
    total = q.count()
    batches = q.order_by(Batch.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_to_read(b, db) for b in batches], total, page, page_size)


def optimize_batches(db: Session, data: BatchOptimizeRequest) -> BatchOptimizeResponse:
    """
    Groups orders into batches of max_orders_per_batch size after layout validation.
    """
    from backend.app.services.warehouse_service import validate_warehouse_layout
    val_res = validate_warehouse_layout(db, data.warehouse_id)
    if not val_res.valid:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "Warehouse layout validation failed.", "details": {"errors": val_res.errors}}
        )

    order_ids = list(data.order_ids)

    max_b = data.max_orders_per_batch
    plans = []
    created_batches = []

    for i in range(0, len(order_ids), max_b):
        chunk = order_ids[i:i + max_b]
        batch_code = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
        batch = Batch(
            batch_code=batch_code,
            warehouse_id=data.warehouse_id,
            max_orders=max_b,
            status="created",
        )
        db.add(batch)
        db.flush()
        for oid in chunk:
            db.add(BatchOrder(batch_id=batch.id, order_id=oid))
        created_batches.append(batch)
        plans.append(BatchPlan(
            batch_id=batch.id,
            order_ids=chunk,
            estimated_distance=0.0,
            estimated_time_minutes=0.0,
        ))

    db.commit()
    return BatchOptimizeResponse(
        task_id=str(uuid.uuid4()),
        warehouse_id=data.warehouse_id,
        batches=plans,
        explanation="Orders grouped by FIFO. Full optimization available in Phase 3.",
        algorithm="fifo_stub",
        fallback_used=True,
    )


def get_batch(db: Session, batch_id: int) -> BatchRead:
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if batch is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Batch not found.", "details": {}})
    return _to_read(batch, db)


def update_batch_status(db: Session, batch_id: int, data: BatchStatusUpdate) -> BatchRead:
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if batch is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Batch not found.", "details": {}})
    batch.status = data.status
    db.commit()
    db.refresh(batch)
    return _to_read(batch, db)
