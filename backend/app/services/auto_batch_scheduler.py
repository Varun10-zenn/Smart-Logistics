"""
Auto-batching background scheduler service.
Periodically checks active warehouses for pending orders and runs batch optimization.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Set, Dict

from backend.app.core.config import settings
from backend.app.core import database as database_module
from backend.app.models.warehouse import Warehouse
from backend.app.models.order import Order
from backend.app.services.warehouse_service import validate_warehouse_layout
from backend.app.services.warehouse_optimization_service import WarehouseOptimizationService
from backend.app.services.order_batcher import BatchingConstraints

logger = logging.getLogger(__name__)

# Per-warehouse locks to prevent overlapping optimization runs
_warehouse_locks: Dict[int, asyncio.Lock] = {}
# Track invalid layout warnings to log once per warehouse
_warned_invalid_warehouses: Set[int] = set()


def get_warehouse_lock(warehouse_id: int) -> asyncio.Lock:
    """Return or create an asyncio.Lock for a specific warehouse ID."""
    if warehouse_id not in _warehouse_locks:
        _warehouse_locks[warehouse_id] = asyncio.Lock()
    return _warehouse_locks[warehouse_id]


async def run_auto_batch_cycle():
    """Execute a single pass of auto-batching over all active warehouses."""
    if getattr(settings, "APP_ENV", "").lower() == "test":
        return

    if not getattr(settings, "AUTO_BATCH_ENABLED", True):
        return

    db = database_module.SessionLocal()
    try:
        # Query ONLY active warehouses that have pending orders in one query
        active_warehouses = db.query(Warehouse).filter(
            Warehouse.status == "active",
            Warehouse.id.in_(db.query(Order.warehouse_id).filter(Order.status == "pending"))
        ).all()
        for wh in active_warehouses:
            wh_id = wh.id
            lock = get_warehouse_lock(wh_id)

            # Non-blocking lock check
            if lock.locked():
                continue

            async with lock:
                try:
                    # 1. Validate layout graph first
                    val = validate_warehouse_layout(db, wh_id)
                    if not val.valid:
                        if wh_id not in _warned_invalid_warehouses:
                            logger.warning(
                                f"Auto-batching skipped warehouse ID {wh_id} ('{wh.code}'): "
                                f"Invalid layout graph ({'; '.join(val.errors)})."
                            )
                            _warned_invalid_warehouses.add(wh_id)
                        continue
                    else:
                        # Clear warning if layout is now valid
                        _warned_invalid_warehouses.discard(wh_id)

                    # 2. Check pending orders
                    pending_orders = db.query(Order).filter(
                        Order.warehouse_id == wh_id,
                        Order.status == "pending"
                    ).order_by(Order.created_at.asc()).all()

                    if not pending_orders:
                        continue

                    min_orders = getattr(settings, "AUTO_BATCH_MIN_ORDERS", 1)
                    max_wait_secs = getattr(settings, "AUTO_BATCH_MAX_WAIT_SECONDS", 120)

                    should_batch = False
                    pending_count = len(pending_orders)

                    if pending_count >= min_orders:
                        should_batch = True
                    else:
                        oldest_created = pending_orders[0].created_at
                        if oldest_created:
                            if oldest_created.tzinfo is None:
                                oldest_created = oldest_created.replace(tzinfo=timezone.utc)
                            age_secs = (datetime.now(timezone.utc) - oldest_created).total_seconds()
                            if age_secs >= max_wait_secs:
                                should_batch = True

                    if should_batch:
                        constraints = BatchingConstraints(
                            max_orders_per_batch=getattr(settings, "AUTO_BATCH_MAX_ORDERS", 5),
                            max_weight_kg=getattr(settings, "AUTO_BATCH_MAX_WEIGHT_KG", 50.0),
                            max_volume_cbm=getattr(settings, "AUTO_BATCH_MAX_VOLUME_CBM", 2.0)
                        )
                        res = WarehouseOptimizationService.optimize_warehouse(
                            db=db,
                            warehouse_id=wh_id,
                            batch_constraints=constraints,
                            use_2opt_routing=True
                        )

                        unassigned_count = res.total_pending_orders - res.eligible_orders_count
                        logger.info(
                            f"Auto-batching executed for warehouse ID {wh_id} ('{wh.code}'): "
                            f"Batches created={res.generated_batches_count}, "
                            f"Eligible orders={res.eligible_orders_count}, "
                            f"Unassigned orders={unassigned_count}."
                        )
                except Exception as exc:
                    logger.error(f"Error during auto-batching cycle for warehouse ID {wh_id}: {exc}", exc_info=True)
    except Exception as exc:
        logger.error(f"Global error in auto-batching cycle: {exc}", exc_info=True)
    finally:
        db.close()


async def auto_batch_scheduler_loop():
    """Background loop that executes run_auto_batch_cycle at interval."""
    logger.info("Starting Auto-Batching Background Scheduler...")
    while True:
        try:
            interval = getattr(settings, "AUTO_BATCH_INTERVAL_SECONDS", 30)
            await asyncio.sleep(interval)
            await run_auto_batch_cycle()
        except asyncio.CancelledError:
            logger.info("Auto-Batching Background Scheduler stopped.")
            break
        except Exception as exc:
            logger.error(f"Unhandled exception in auto-batching loop: {exc}", exc_info=True)
