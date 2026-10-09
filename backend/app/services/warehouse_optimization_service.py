"""
Warehouse Optimization Domain Service.
Phase 3.4 — Orchestrates warehouse validation, inventory stock checking, graph loading,
batch generation, pick route optimization, validation, transaction safety, and persistence.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.models.warehouse import Warehouse, WarehouseNode, StorageLocation, Inventory, Product
from backend.app.models.order import Order, OrderItem
from backend.app.models.batch import Batch, BatchOrder, PickRoute, PickRouteStep
from backend.app.models.intelligence import AIRecommendation

from backend.app.services.warehouse_graph import WarehouseGraph, GraphEngine
from backend.app.services.order_batcher import (
    OrderBatchingEngine, OrderDTO, OrderItemDTO, BatchingConstraints, BatchingConfig, BatchCandidate, BatchingResult
)
from backend.app.services.pick_routing_engine import (
    PickRouteOptimizationEngine, PickTargetDTO, PickRouteResult
)


class BatchSummaryDTO(BaseModel):
    batch_id: int
    batch_code: str
    order_ids: List[int]
    total_weight_kg: float
    total_volume_cbm: float
    pick_route_id: int
    total_distance_meters: float
    estimated_duration_minutes: float
    algorithm_used: str
    steps_count: int


class WarehouseOptimizationResultDTO(BaseModel):
    success: bool
    warehouse_id: int
    total_pending_orders: int
    eligible_orders_count: int
    generated_batches_count: int
    batches: List[BatchSummaryDTO]
    unassigned_order_ids: List[int]
    unassigned_reasons: Dict[int, str]
    overall_distance_reduction_pct: Optional[float]
    execution_time_ms: float
    recommendation_id: Optional[int] = None
    failure_reason: Optional[str] = None


class WarehouseOptimizationService:
    """Application Domain Service orchestrating end-to-end warehouse optimization."""

    @staticmethod
    def _fetch_pending_orders(db: Session, warehouse_id: int) -> List[OrderDTO]:
        """Retrieves pending orders and converts them to OrderDTO objects."""
        db_orders = db.query(Order).filter(
            Order.warehouse_id == warehouse_id,
            Order.status == "pending"
        ).all()

        dtos: List[OrderDTO] = []
        for o in db_orders:
            items_dto = [
                OrderItemDTO(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_weight_kg=float(item.product.unit_weight_kg) if item.product else 0.0,
                    unit_volume_cbm=float(item.product.unit_volume_cbm) if item.product else 0.0,
                )
                for item in o.items
            ]
            dtos.append(OrderDTO(
                id=o.id,
                order_number=o.order_number,
                warehouse_id=o.warehouse_id,
                priority=o.priority,
                status=o.status,
                created_at=o.created_at,
                promised_at=o.promised_at,
                items=items_dto
            ))
        return dtos

    @staticmethod
    def _fetch_inventory_map(db: Session, warehouse_id: int) -> Dict[int, int]:
        """Fetches total available stock per product ID for a warehouse."""
        stock = db.query(
            Inventory.product_id,
            Inventory.quantity
        ).filter(Inventory.warehouse_id == warehouse_id).all()

        stock_map: Dict[int, int] = {}
        for pid, qty in stock:
            stock_map[pid] = stock_map.get(pid, 0) + qty
        return stock_map

    @staticmethod
    def _fetch_product_primary_location(db: Session, warehouse_id: int, product_id: int) -> Optional[Tuple[int, int]]:
        """Finds primary (location_id, node_id) for a product in the warehouse."""
        inv = db.query(Inventory).filter(
            Inventory.warehouse_id == warehouse_id,
            Inventory.product_id == product_id,
            Inventory.quantity > 0
        ).first()

        if inv and inv.location:
            return inv.location_id, inv.location.node_id
        return None

    @staticmethod
    def optimize_warehouse(
        db: Session,
        warehouse_id: int,
        batch_constraints: Optional[BatchingConstraints] = None,
        use_2opt_routing: bool = True
    ) -> WarehouseOptimizationResultDTO:
        """
        Full transactional optimization flow:
        1. Validate warehouse existence.
        2. Load dark-store graph.
        3. Retrieve pending orders & stock map.
        4. Execute OrderBatchingEngine.
        5. For each batch, resolve pick locations & execute PickRouteOptimizationEngine.
        6. Validate optimization completeness.
        7. Persist Batches, BatchOrders, PickRoutes, PickRouteSteps, and AIRecommendation atomically.
        """
        import time
        start_time = time.perf_counter()

        # 1. Warehouse Validation
        wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
        if not wh:
            elapsed = round((time.perf_counter() - start_time) * 1000, 3)
            return WarehouseOptimizationResultDTO(
                success=False, warehouse_id=warehouse_id, total_pending_orders=0,
                eligible_orders_count=0, generated_batches_count=0, batches=[],
                unassigned_order_ids=[], unassigned_reasons={}, overall_distance_reduction_pct=None,
                execution_time_ms=elapsed, failure_reason=f"Warehouse ID {warehouse_id} not found."
            )

        # 2. Layout Validation & Graph Loading
        from backend.app.services.warehouse_service import validate_warehouse_layout
        val_res = validate_warehouse_layout(db, warehouse_id)
        if not val_res.valid:
            elapsed = round((time.perf_counter() - start_time) * 1000, 3)
            return WarehouseOptimizationResultDTO(
                success=False, warehouse_id=warehouse_id, total_pending_orders=0,
                eligible_orders_count=0, generated_batches_count=0, batches=[],
                unassigned_order_ids=[], unassigned_reasons={}, overall_distance_reduction_pct=None,
                execution_time_ms=elapsed, failure_reason="Warehouse layout validation failed: " + "; ".join(val_res.errors)
            )

        try:
            graph = GraphEngine.load_warehouse_graph(db, warehouse_id)
        except Exception as err:
            elapsed = round((time.perf_counter() - start_time) * 1000, 3)
            return WarehouseOptimizationResultDTO(
                success=False, warehouse_id=warehouse_id, total_pending_orders=0,
                eligible_orders_count=0, generated_batches_count=0, batches=[],
                unassigned_order_ids=[], unassigned_reasons={}, overall_distance_reduction_pct=None,
                execution_time_ms=elapsed, failure_reason=f"Failed to load graph: {err}"
            )

        # 3. Resolve Depot Start Node
        depot_node = next((n for n in graph.nodes.values() if n.is_depot and not n.is_blocked), None)
        if not depot_node:
            elapsed = round((time.perf_counter() - start_time) * 1000, 3)
            return WarehouseOptimizationResultDTO(
                success=False, warehouse_id=warehouse_id, total_pending_orders=0,
                eligible_orders_count=0, generated_batches_count=0, batches=[],
                unassigned_order_ids=[], unassigned_reasons={}, overall_distance_reduction_pct=None,
                execution_time_ms=elapsed, failure_reason="No active depot node configured for warehouse."
            )
        start_node_id = depot_node.id


        # 3. Retrieve Pending Orders & Stock Map
        pending_orders = WarehouseOptimizationService._fetch_pending_orders(db, warehouse_id)
        if not pending_orders:
            elapsed = round((time.perf_counter() - start_time) * 1000, 3)
            return WarehouseOptimizationResultDTO(
                success=True, warehouse_id=warehouse_id, total_pending_orders=0,
                eligible_orders_count=0, generated_batches_count=0, batches=[],
                unassigned_order_ids=[], unassigned_reasons={}, overall_distance_reduction_pct=0.0,
                execution_time_ms=elapsed, failure_reason=None
            )

        stock_map = WarehouseOptimizationService._fetch_inventory_map(db, warehouse_id)

        # 4. Batching Execution
        batching_res: BatchingResult = OrderBatchingEngine.batch_priority_heuristic(
            orders=pending_orders,
            inventory_stock_map=stock_map,
            target_warehouse_id=warehouse_id,
            constraints=batch_constraints
        )

        if not batching_res.generated_batches:
            elapsed = round((time.perf_counter() - start_time) * 1000, 3)
            return WarehouseOptimizationResultDTO(
                success=True, warehouse_id=warehouse_id, total_pending_orders=len(pending_orders),
                eligible_orders_count=batching_res.eligible_orders_count, generated_batches_count=0,
                batches=[], unassigned_order_ids=batching_res.unassigned_orders,
                unassigned_reasons=batching_res.unassigned_reasons, overall_distance_reduction_pct=0.0,
                execution_time_ms=elapsed, failure_reason=None
            )

        # Map Order DTOs for quick lookup
        order_dto_map = {o.id: o for o in pending_orders}

        # 5. Routing Execution for Each Batch
        batch_routing_results: List[Tuple[BatchCandidate, PickRouteResult, List[Tuple[int, int, int, int]]]] = []
        total_baseline_dist = 0.0
        total_opt_dist = 0.0

        for b_cand in batching_res.generated_batches:
            # Map batch items to storage locations & nodes
            pick_targets: List[PickTargetDTO] = []
            location_step_info: List[Tuple[int, int, int, int]] = []  # (loc_id, node_id, prod_id, qty)

            for order_id in b_cand.order_ids:
                o_dto = order_dto_map[order_id]
                for item in o_dto.items:
                    loc_info = WarehouseOptimizationService._fetch_product_primary_location(db, warehouse_id, item.product_id)
                    if not loc_info:
                        elapsed = round((time.perf_counter() - start_time) * 1000, 3)
                        return WarehouseOptimizationResultDTO(
                            success=False, warehouse_id=warehouse_id, total_pending_orders=len(pending_orders),
                            eligible_orders_count=batching_res.eligible_orders_count, generated_batches_count=0,
                            batches=[], unassigned_order_ids=batching_res.unassigned_orders,
                            unassigned_reasons=batching_res.unassigned_reasons, overall_distance_reduction_pct=None,
                            execution_time_ms=elapsed, failure_reason=f"No storage location found for product ID {item.product_id}."
                        )
                    loc_id, node_id = loc_info
                    pick_targets.append(PickTargetDTO(location_id=loc_id, node_id=node_id, product_id=item.product_id, quantity_to_pick=item.quantity))
                    location_step_info.append((loc_id, node_id, item.product_id, item.quantity))

            # Compute route
            route_res: PickRouteResult = PickRouteOptimizationEngine.optimize_route_heuristic(
                graph=graph,
                targets=pick_targets,
                start_node_id=start_node_id,
                use_2opt=use_2opt_routing
            )

            if not route_res.success:
                elapsed = round((time.perf_counter() - start_time) * 1000, 3)
                return WarehouseOptimizationResultDTO(
                    success=False, warehouse_id=warehouse_id, total_pending_orders=len(pending_orders),
                    eligible_orders_count=batching_res.eligible_orders_count, generated_batches_count=0,
                    batches=[], unassigned_order_ids=batching_res.unassigned_orders,
                    unassigned_reasons=batching_res.unassigned_reasons, overall_distance_reduction_pct=None,
                    execution_time_ms=elapsed, failure_reason=f"Route generation failed for batch: {route_res.failure_reason}"
                )

            total_baseline_dist += (route_res.baseline_distance_meters or 0.0)
            total_opt_dist += route_res.total_distance_meters
            batch_routing_results.append((b_cand, route_res, location_step_info))

        # 6. Atomic Persistence Block
        batch_summaries: List[BatchSummaryDTO] = []
        try:
            for b_cand, r_res, step_info in batch_routing_results:
                b_code = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
                db_batch = Batch(
                    batch_code=b_code,
                    warehouse_id=warehouse_id,
                    max_orders=batch_constraints.max_orders_per_batch if batch_constraints else 5,
                    total_weight_kg=b_cand.total_weight_kg,
                    status="created"
                )
                db.add(db_batch)
                db.flush()  # Generate db_batch.id

                # BatchOrders & Order status update
                for o_id in b_cand.order_ids:
                    db.add(BatchOrder(batch_id=db_batch.id, order_id=o_id))
                    db_order = db.query(Order).filter(Order.id == o_id).first()
                    if db_order:
                        db_order.status = "batched"

                # PickRoute
                db_route = PickRoute(
                    batch_id=db_batch.id,
                    total_distance_meters=r_res.total_distance_meters,
                    estimated_duration_minutes=r_res.estimated_duration_minutes,
                    algorithm_used=r_res.algorithm_used
                )
                db.add(db_route)
                db.flush()  # Generate db_route.id

                # PickRouteSteps
                # Map location_id -> step info
                step_map = {loc_id: (prod_id, qty) for loc_id, _, prod_id, qty in step_info}
                for idx, loc_id in enumerate(r_res.ordered_location_ids, start=1):
                    prod_id, qty = step_map[loc_id]
                    db.add(PickRouteStep(
                        pick_route_id=db_route.id,
                        step_number=idx,
                        location_id=loc_id,
                        product_id=prod_id,
                        quantity_to_pick=qty
                    ))

                batch_summaries.append(BatchSummaryDTO(
                    batch_id=db_batch.id,
                    batch_code=b_code,
                    order_ids=b_cand.order_ids,
                    total_weight_kg=b_cand.total_weight_kg,
                    total_volume_cbm=b_cand.total_volume_cbm,
                    pick_route_id=db_route.id,
                    total_distance_meters=r_res.total_distance_meters,
                    estimated_duration_minutes=r_res.estimated_duration_minutes,
                    algorithm_used=r_res.algorithm_used,
                    steps_count=len(r_res.ordered_location_ids)
                ))

            # AIRecommendation Log Record
            overall_improvement: Optional[float] = None
            if total_baseline_dist > 0:
                overall_improvement = round(((total_baseline_dist - total_opt_dist) / total_baseline_dist) * 100.0, 2)

            rec = AIRecommendation(
                agent_name="warehouse_agent",
                recommendation_type="warehouse_batch_picking_optimization",
                input_snapshot={
                    "warehouse_id": warehouse_id,
                    "pending_orders_count": len(pending_orders),
                },
                output_payload={
                    "batches_created": len(batch_summaries),
                    "total_distance_meters": total_opt_dist,
                    "unassigned_orders_count": len(batching_res.unassigned_orders),
                },
                explanation=f"Generated {len(batch_summaries)} picking batches optimizing walk distance by {overall_improvement or 0.0}%.",
                confidence_score=0.950,
                fallback_used=False,
                model_version="phase-3-v1"
            )
            db.add(rec)
            db.flush()

            db.commit()  # Commit transaction safely

        except Exception as err:
            db.rollback()
            elapsed = round((time.perf_counter() - start_time) * 1000, 3)
            return WarehouseOptimizationResultDTO(
                success=False, warehouse_id=warehouse_id, total_pending_orders=len(pending_orders),
                eligible_orders_count=batching_res.eligible_orders_count, generated_batches_count=0,
                batches=[], unassigned_order_ids=batching_res.unassigned_orders,
                unassigned_reasons=batching_res.unassigned_reasons, overall_distance_reduction_pct=None,
                execution_time_ms=elapsed, failure_reason=f"Transaction rolled back due to error: {err}"
            )

        elapsed = round((time.perf_counter() - start_time) * 1000, 3)
        return WarehouseOptimizationResultDTO(
            success=True,
            warehouse_id=warehouse_id,
            total_pending_orders=len(pending_orders),
            eligible_orders_count=batching_res.eligible_orders_count,
            generated_batches_count=len(batch_summaries),
            batches=batch_summaries,
            unassigned_order_ids=batching_res.unassigned_orders,
            unassigned_reasons=batching_res.unassigned_reasons,
            overall_distance_reduction_pct=overall_improvement,
            execution_time_ms=elapsed,
            recommendation_id=rec.id
        )
