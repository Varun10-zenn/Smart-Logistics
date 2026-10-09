"""
Order Batching Engine Module.
Phase 3.2 — Deterministic order eligibility evaluation and batching (FIFO baseline & Priority-Heuristic strategy).
"""
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class OrderItemDTO:
    product_id: int
    quantity: int
    unit_weight_kg: float
    unit_volume_cbm: float


@dataclass
class OrderDTO:
    id: int
    order_number: str
    warehouse_id: int
    priority: int  # 1=normal, 2=high, 3=urgent
    status: str    # "pending", "batched", etc.
    created_at: datetime
    promised_at: datetime
    items: List[OrderItemDTO] = field(default_factory=list)

    @property
    def total_weight_kg(self) -> float:
        return sum(item.quantity * item.unit_weight_kg for item in self.items)

    @property
    def total_volume_cbm(self) -> float:
        return sum(item.quantity * item.unit_volume_cbm for item in self.items)


@dataclass
class BatchingConstraints:
    max_orders_per_batch: int = 5
    max_weight_kg: float = 25.0       # Configurable development default
    max_volume_cbm: float = 0.12      # Configurable development default
    require_status_pending: bool = True
    enforce_inventory_check: bool = True


@dataclass
class BatchingConfig:
    w_distance: float = 1.0
    w_priority: float = 15.0
    w_deadline: float = 20.0


@dataclass
class BatchCandidate:
    batch_index: int
    order_ids: List[int]
    total_weight_kg: float
    total_volume_cbm: float
    priority_score: float


@dataclass
class BatchingResult:
    strategy_name: str
    total_orders_evaluated: int
    eligible_orders_count: int
    generated_batches: List[BatchCandidate]
    batch_count: int
    unassigned_orders: List[int]
    unassigned_reasons: Dict[int, str]
    objective_value: float
    execution_time_ms: float


class OrderBatchingEngine:
    """Deterministic Order Batching Engine implementing FIFO baseline and Priority-Heuristic optimization."""

    @staticmethod
    def evaluate_eligibility(
        orders: List[OrderDTO],
        inventory_stock_map: Optional[Dict[int, int]] = None,
        target_warehouse_id: Optional[int] = None,
        constraints: Optional[BatchingConstraints] = None
    ) -> Tuple[List[OrderDTO], Dict[int, str]]:
        """
        Determines eligible orders based on actual model fields:
        - status == 'pending'
        - warehouse_id matching target (if specified)
        - inventory availability (stock >= required)
        """
        if constraints is None:
            constraints = BatchingConstraints()

        eligible: List[OrderDTO] = []
        unassigned_reasons: Dict[int, str] = {}

        for order in orders:
            # 1. Status Check
            if constraints.require_status_pending and order.status != "pending":
                unassigned_reasons[order.id] = f"Status '{order.status}' is not 'pending'."
                continue

            # 2. Warehouse Relationship Check
            if target_warehouse_id is not None and order.warehouse_id != target_warehouse_id:
                unassigned_reasons[order.id] = f"Warehouse ID {order.warehouse_id} does not match target {target_warehouse_id}."
                continue

            # 3. Item Count Check
            if not order.items:
                unassigned_reasons[order.id] = "Order contains no line items."
                continue

            # 4. Single-order Capacity Overlap Check
            if order.total_weight_kg > constraints.max_weight_kg:
                unassigned_reasons[order.id] = f"Single order weight {order.total_weight_kg:.2f}kg exceeds batch max weight {constraints.max_weight_kg:.2f}kg."
                continue

            if order.total_volume_cbm > constraints.max_volume_cbm:
                unassigned_reasons[order.id] = f"Single order volume {order.total_volume_cbm:.4f}cbm exceeds batch max volume {constraints.max_volume_cbm:.4f}cbm."
                continue

            # 5. Inventory Availability Check
            if constraints.enforce_inventory_check and inventory_stock_map is not None:
                insufficient = False
                for item in order.items:
                    available = inventory_stock_map.get(item.product_id, 0)
                    if available < item.quantity:
                        unassigned_reasons[order.id] = f"Insufficient stock for product ID {item.product_id}: required {item.quantity}, available {available}."
                        insufficient = True
                        break
                if insufficient:
                    continue

            eligible.append(order)

        return eligible, unassigned_reasons

    @staticmethod
    def batch_fifo(
        orders: List[OrderDTO],
        inventory_stock_map: Optional[Dict[int, int]] = None,
        target_warehouse_id: Optional[int] = None,
        constraints: Optional[BatchingConstraints] = None,
        config: Optional[BatchingConfig] = None
    ) -> BatchingResult:
        """
        Deterministic FIFO Baseline Strategy.
        Processes eligible orders strictly by created_at timestamp.
        """
        start_time = time.perf_counter()
        if constraints is None:
            constraints = BatchingConstraints()
        if config is None:
            config = BatchingConfig()

        eligible_orders, unassigned_reasons = OrderBatchingEngine.evaluate_eligibility(
            orders, inventory_stock_map, target_warehouse_id, constraints
        )

        # Sort strictly by created_at for FIFO baseline
        sorted_orders = sorted(eligible_orders, key=lambda o: o.created_at)

        batches: List[BatchCandidate] = []
        current_batch_orders: List[OrderDTO] = []
        current_weight = 0.0
        current_volume = 0.0

        for order in sorted_orders:
            # Check capacity constraints for current batch
            if (len(current_batch_orders) + 1 > constraints.max_orders_per_batch or
                current_weight + order.total_weight_kg > constraints.max_weight_kg or
                current_volume + order.total_volume_cbm > constraints.max_volume_cbm):
                
                # Finalize current batch
                if current_batch_orders:
                    batch_idx = len(batches) + 1
                    p_score = sum(o.priority for o in current_batch_orders) / len(current_batch_orders)
                    batches.append(BatchCandidate(
                        batch_index=batch_idx,
                        order_ids=[o.id for o in current_batch_orders],
                        total_weight_kg=round(current_weight, 2),
                        total_volume_cbm=round(current_volume, 4),
                        priority_score=round(p_score, 2)
                    ))
                current_batch_orders = [order]
                current_weight = order.total_weight_kg
                current_volume = order.total_volume_cbm
            else:
                current_batch_orders.append(order)
                current_weight += order.total_weight_kg
                current_volume += order.total_volume_cbm

        # Finalize last batch
        if current_batch_orders:
            batch_idx = len(batches) + 1
            p_score = sum(o.priority for o in current_batch_orders) / len(current_batch_orders)
            batches.append(BatchCandidate(
                batch_index=batch_idx,
                order_ids=[o.id for o in current_batch_orders],
                total_weight_kg=round(current_weight, 2),
                total_volume_cbm=round(current_volume, 4),
                priority_score=round(p_score, 2)
            ))

        # Calculate FIFO objective cost
        # Objective = w_distance * batch_count + w_priority * penalty
        objective_val = OrderBatchingEngine._calculate_objective(batches, len(orders) - len(eligible_orders), config)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)

        return BatchingResult(
            strategy_name="fifo_baseline",
            total_orders_evaluated=len(orders),
            eligible_orders_count=len(eligible_orders),
            generated_batches=batches,
            batch_count=len(batches),
            unassigned_orders=list(unassigned_reasons.keys()),
            unassigned_reasons=unassigned_reasons,
            objective_value=round(objective_val, 2),
            execution_time_ms=elapsed_ms
        )

    @staticmethod
    def batch_priority_heuristic(
        orders: List[OrderDTO],
        inventory_stock_map: Optional[Dict[int, int]] = None,
        target_warehouse_id: Optional[int] = None,
        constraints: Optional[BatchingConstraints] = None,
        config: Optional[BatchingConfig] = None
    ) -> BatchingResult:
        """
        Deterministic Priority-Heuristic Optimized Strategy.
        Sorts eligible orders by priority DESC, then promised_at ASC (deadline), then created_at ASC.
        Greedily packs highest-priority urgent orders together to minimize priority SLA penalties.
        """
        start_time = time.perf_counter()
        if constraints is None:
            constraints = BatchingConstraints()
        if config is None:
            config = BatchingConfig()

        eligible_orders, unassigned_reasons = OrderBatchingEngine.evaluate_eligibility(
            orders, inventory_stock_map, target_warehouse_id, constraints
        )

        # Priority-aware sorting: priority DESC (3=urgent > 2=high > 1=normal), then promised_at ASC
        sorted_orders = sorted(eligible_orders, key=lambda o: (-o.priority, o.promised_at, o.created_at))

        batches: List[BatchCandidate] = []
        
        # Greedy packing into active batches
        for order in sorted_orders:
            placed = False
            for batch in batches:
                if (len(batch.order_ids) + 1 <= constraints.max_orders_per_batch and
                    batch.total_weight_kg + order.total_weight_kg <= constraints.max_weight_kg and
                    batch.total_volume_cbm + order.total_volume_cbm <= constraints.max_volume_cbm):
                    
                    batch.order_ids.append(order.id)
                    batch.total_weight_kg = round(batch.total_weight_kg + order.total_weight_kg, 2)
                    batch.total_volume_cbm = round(batch.total_volume_cbm + order.total_volume_cbm, 4)
                    placed = True
                    break
            
            if not placed:
                # Open a new batch
                batches.append(BatchCandidate(
                    batch_index=len(batches) + 1,
                    order_ids=[order.id],
                    total_weight_kg=round(order.total_weight_kg, 2),
                    total_volume_cbm=round(order.total_volume_cbm, 4),
                    priority_score=float(order.priority)
                ))

        # Re-compute priority_score per batch
        order_map = {o.id: o for o in eligible_orders}
        for batch in batches:
            p_score = sum(order_map[oid].priority for oid in batch.order_ids) / len(batch.order_ids)
            batch.priority_score = round(p_score, 2)

        objective_val = OrderBatchingEngine._calculate_objective(batches, len(orders) - len(eligible_orders), config)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)

        return BatchingResult(
            strategy_name="priority_heuristic",
            total_orders_evaluated=len(orders),
            eligible_orders_count=len(eligible_orders),
            generated_batches=batches,
            batch_count=len(batches),
            unassigned_orders=list(unassigned_reasons.keys()),
            unassigned_reasons=unassigned_reasons,
            objective_value=round(objective_val, 2),
            execution_time_ms=elapsed_ms
        )

    @staticmethod
    def _calculate_objective(batches: List[BatchCandidate], unassigned_count: int, config: BatchingConfig) -> float:
        """
        Configurable Objective Function:
        total_cost = w_distance * batch_count + w_priority * unassigned_penalty
        """
        return (config.w_distance * len(batches)) + (config.w_priority * unassigned_count)
