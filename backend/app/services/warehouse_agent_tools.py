"""
Controlled Tool Interface Layer for Warehouse Optimization Agent.
Phase 3.5 — Strict, typed tools wrapping application domain services.
No direct PostgreSQL or SQLAlchemy queries permitted within this module.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.models.warehouse import StorageLocation
from backend.app.services.warehouse_graph import GraphEngine, WarehouseGraph
from backend.app.services.order_batcher import OrderBatchingEngine, OrderDTO, BatchingConstraints, BatchingConfig
from backend.app.services.pick_routing_engine import PickRouteOptimizationEngine, PickTargetDTO
from backend.app.services.warehouse_optimization_service import WarehouseOptimizationService


# ---------------------------------------------------------------------------
# Authorization Helper & Role Matrix
# ---------------------------------------------------------------------------
ALLOWED_WAREHOUSE_ROLES = {"admin", "warehouse_operator", "fleet_manager"}


def _check_authorization(user_role: str, tool_name: str) -> None:
    """Verifies that user_role has privilege to invoke tool_name."""
    if user_role not in ALLOWED_WAREHOUSE_ROLES:
        raise PermissionError(
            f"Unauthorized: Role '{user_role}' is not permitted to execute tool '{tool_name}'."
        )


# ---------------------------------------------------------------------------
# Tool 1: get_warehouse_graph
# ---------------------------------------------------------------------------
class GetWarehouseGraphInput(BaseModel):
    warehouse_id: int = Field(..., gt=0)


class GetWarehouseGraphOutput(BaseModel):
    success: bool
    warehouse_id: int
    total_nodes: int
    total_edges: int
    node_ids: List[int]
    error: Optional[str] = None


def tool_get_warehouse_graph(db: Session, user_role: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieves dark-store layout node and edge count for a warehouse."""
    _check_authorization(user_role, "get_warehouse_graph")
    try:
        inp = GetWarehouseGraphInput(**payload)
        graph = GraphEngine.load_warehouse_graph(db, inp.warehouse_id)
        out = GetWarehouseGraphOutput(
            success=True,
            warehouse_id=inp.warehouse_id,
            total_nodes=len(graph.nodes),
            total_edges=len(graph.edges),
            node_ids=list(graph.nodes.keys())
        )
        return out.model_dump()
    except Exception as err:
        return GetWarehouseGraphOutput(
            success=False, warehouse_id=payload.get("warehouse_id", 0), total_nodes=0, total_edges=0, node_ids=[], error=str(err)
        ).model_dump()



# ---------------------------------------------------------------------------
# Tool 2: get_eligible_orders
# ---------------------------------------------------------------------------
class GetEligibleOrdersInput(BaseModel):
    warehouse_id: int = Field(..., gt=0)


class GetEligibleOrdersOutput(BaseModel):
    success: bool
    warehouse_id: int
    total_pending_orders: int
    eligible_order_ids: List[int]
    unassigned_reasons: Dict[int, str]
    error: Optional[str] = None


def tool_get_eligible_orders(db: Session, user_role: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieves eligible pending order IDs for a warehouse."""
    _check_authorization(user_role, "get_eligible_orders")
    inp = GetEligibleOrdersInput(**payload)
    try:
        pending = WarehouseOptimizationService._fetch_pending_orders(db, inp.warehouse_id)
        stock_map = WarehouseOptimizationService._fetch_inventory_map(db, inp.warehouse_id)
        eligible, unassigned = OrderBatchingEngine.evaluate_eligibility(
            orders=pending, inventory_stock_map=stock_map, target_warehouse_id=inp.warehouse_id
        )
        out = GetEligibleOrdersOutput(
            success=True,
            warehouse_id=inp.warehouse_id,
            total_pending_orders=len(pending),
            eligible_order_ids=[o.id for o in eligible],
            unassigned_reasons=unassigned
        )
        return out.model_dump()
    except Exception as err:
        return GetEligibleOrdersOutput(
            success=False, warehouse_id=inp.warehouse_id, total_pending_orders=0,
            eligible_order_ids=[], unassigned_reasons={}, error=str(err)
        ).model_dump()


# ---------------------------------------------------------------------------
# Tool 3: get_inventory_state
# ---------------------------------------------------------------------------
class GetInventoryStateInput(BaseModel):
    warehouse_id: int = Field(..., gt=0)
    product_ids: Optional[List[int]] = None


class GetInventoryStateOutput(BaseModel):
    success: bool
    warehouse_id: int
    stock_map: Dict[int, int]
    error: Optional[str] = None


def tool_get_inventory_state(db: Session, user_role: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieves available stock counts per product ID for a warehouse."""
    _check_authorization(user_role, "get_inventory_state")
    inp = GetInventoryStateInput(**payload)
    try:
        full_map = WarehouseOptimizationService._fetch_inventory_map(db, inp.warehouse_id)
        if inp.product_ids:
            filtered = {pid: full_map.get(pid, 0) for pid in inp.product_ids}
        else:
            filtered = full_map
        out = GetInventoryStateOutput(
            success=True, warehouse_id=inp.warehouse_id, stock_map=filtered
        )
        return out.model_dump()
    except Exception as err:
        return GetInventoryStateOutput(
            success=False, warehouse_id=inp.warehouse_id, stock_map={}, error=str(err)
        ).model_dump()


# ---------------------------------------------------------------------------
# Tool 4: calculate_shortest_path
# ---------------------------------------------------------------------------
class CalculateShortestPathInput(BaseModel):
    warehouse_id: int = Field(..., gt=0)
    start_node_id: int = Field(..., gt=0)
    destination_node_id: int = Field(..., gt=0)
    algorithm: str = "a_star"  # "dijkstra" or "a_star"


class CalculateShortestPathOutput(BaseModel):
    success: bool
    algorithm: str
    path: List[int]
    total_distance_meters: float
    nodes_visited: int
    execution_time_ms: float
    error: Optional[str] = None


def tool_calculate_shortest_path(db: Session, user_role: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Calculates shortest indoor path between two nodes using Dijkstra or A*."""
    _check_authorization(user_role, "calculate_shortest_path")
    inp = CalculateShortestPathInput(**payload)
    try:
        graph = GraphEngine.load_warehouse_graph(db, inp.warehouse_id)
        if inp.algorithm.lower() == "dijkstra":
            res = GraphEngine.find_shortest_path_dijkstra(graph, inp.start_node_id, inp.destination_node_id)
        else:
            res = GraphEngine.find_shortest_path_a_star(graph, inp.start_node_id, inp.destination_node_id)

        out = CalculateShortestPathOutput(
            success=res.success,
            algorithm=res.algorithm,
            path=res.path,
            total_distance_meters=res.total_distance,
            nodes_visited=res.nodes_visited,
            execution_time_ms=res.execution_time_ms,
            error=res.failure_reason
        )
        return out.model_dump()
    except Exception as err:
        return CalculateShortestPathOutput(
            success=False, algorithm=inp.algorithm, path=[], total_distance_meters=0.0,
            nodes_visited=0, execution_time_ms=0.0, error=str(err)
        ).model_dump()


# ---------------------------------------------------------------------------
# Tool 5: generate_order_batches
# ---------------------------------------------------------------------------
class GenerateOrderBatchesInput(BaseModel):
    warehouse_id: int = Field(..., gt=0)
    max_orders_per_batch: int = Field(5, gt=0, le=20)
    max_weight_kg: float = Field(25.0, gt=0.0)
    max_volume_cbm: float = Field(0.12, gt=0.0)
    strategy: str = "priority_heuristic"  # "fifo_baseline" or "priority_heuristic"


class GenerateOrderBatchesOutput(BaseModel):
    success: bool
    strategy_name: str
    batch_count: int
    batches: List[Dict[str, Any]]
    unassigned_orders: List[int]
    unassigned_reasons: Dict[int, str]
    objective_value: float
    execution_time_ms: float
    error: Optional[str] = None


def tool_generate_order_batches(db: Session, user_role: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generates candidate order batches using FIFO or Priority-Heuristic strategy."""
    _check_authorization(user_role, "generate_order_batches")
    inp = GenerateOrderBatchesInput(**payload)
    try:
        pending = WarehouseOptimizationService._fetch_pending_orders(db, inp.warehouse_id)
        stock_map = WarehouseOptimizationService._fetch_inventory_map(db, inp.warehouse_id)
        constraints = BatchingConstraints(
            max_orders_per_batch=inp.max_orders_per_batch,
            max_weight_kg=inp.max_weight_kg,
            max_volume_cbm=inp.max_volume_cbm
        )

        if inp.strategy == "fifo_baseline":
            res = OrderBatchingEngine.batch_fifo(pending, stock_map, inp.warehouse_id, constraints)
        else:
            res = OrderBatchingEngine.batch_priority_heuristic(pending, stock_map, inp.warehouse_id, constraints)

        batches_list = [
            {
                "batch_index": b.batch_index,
                "order_ids": b.order_ids,
                "total_weight_kg": b.total_weight_kg,
                "total_volume_cbm": b.total_volume_cbm,
                "priority_score": b.priority_score,
            }
            for b in res.generated_batches
        ]

        out = GenerateOrderBatchesOutput(
            success=True,
            strategy_name=res.strategy_name,
            batch_count=res.batch_count,
            batches=batches_list,
            unassigned_orders=res.unassigned_orders,
            unassigned_reasons=res.unassigned_reasons,
            objective_value=res.objective_value,
            execution_time_ms=res.execution_time_ms
        )
        return out.model_dump()
    except Exception as err:
        return GenerateOrderBatchesOutput(
            success=False, strategy_name=inp.strategy, batch_count=0, batches=[],
            unassigned_orders=[], unassigned_reasons={}, objective_value=0.0,
            execution_time_ms=0.0, error=str(err)
        ).model_dump()


# ---------------------------------------------------------------------------
# Tool 6: generate_pick_route
# ---------------------------------------------------------------------------
class GeneratePickRouteInput(BaseModel):
    warehouse_id: int = Field(..., gt=0)
    target_location_ids: List[int] = Field(..., min_items=1)
    start_node_id: Optional[int] = None
    use_2opt: bool = True


class GeneratePickRouteOutput(BaseModel):
    success: bool
    algorithm_used: str
    ordered_location_ids: List[int]
    total_distance_meters: float
    estimated_duration_minutes: float
    unreachable_location_ids: List[int]
    improvement_percentage: Optional[float]
    execution_time_ms: float
    error: Optional[str] = None


def tool_generate_pick_route(db: Session, user_role: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generates pick route for target locations using 2-Opt local search TSP heuristic."""
    _check_authorization(user_role, "generate_pick_route")
    inp = GeneratePickRouteInput(**payload)
    try:
        graph = GraphEngine.load_warehouse_graph(db, inp.warehouse_id)
        start_node = inp.start_node_id if inp.start_node_id else min(graph.nodes.keys())

        # Resolve location_id -> node_id
        targets: List[PickTargetDTO] = []
        for loc_id in inp.target_location_ids:
            loc = db.query(StorageLocation).filter(StorageLocation.id == loc_id).first()
            if loc:
                targets.append(PickTargetDTO(location_id=loc.id, node_id=loc.node_id, product_id=1, quantity_to_pick=1))

        res = PickRouteOptimizationEngine.optimize_route_heuristic(
            graph=graph, targets=targets, start_node_id=start_node, use_2opt=inp.use_2opt
        )

        out = GeneratePickRouteOutput(
            success=res.success,
            algorithm_used=res.algorithm_used,
            ordered_location_ids=res.ordered_location_ids,
            total_distance_meters=res.total_distance_meters,
            estimated_duration_minutes=res.estimated_duration_minutes,
            unreachable_location_ids=res.unreachable_location_ids,
            improvement_percentage=res.improvement_percentage,
            execution_time_ms=res.execution_time_ms,
            error=res.failure_reason
        )
        return out.model_dump()
    except Exception as err:
        return GeneratePickRouteOutput(
            success=False, algorithm_used="nearest_neighbor", ordered_location_ids=[],
            total_distance_meters=0.0, estimated_duration_minutes=0.0, unreachable_location_ids=[],
            improvement_percentage=None, execution_time_ms=0.0, error=str(err)
        ).model_dump()


# ---------------------------------------------------------------------------
# Tool 7: validate_batch
# ---------------------------------------------------------------------------
class ValidateBatchInput(BaseModel):
    warehouse_id: int = Field(..., gt=0)
    order_ids: List[int] = Field(..., min_items=1)
    max_orders: int = Field(5, gt=0)
    max_weight_kg: float = Field(25.0, gt=0.0)
    max_volume_cbm: float = Field(0.12, gt=0.0)


class ValidateBatchOutput(BaseModel):
    is_valid: bool
    violations: List[str]
    total_orders: int
    total_weight_kg: float
    total_volume_cbm: float


def tool_validate_batch(db: Session, user_role: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validates candidate batch against capacity limits and stock availability."""
    _check_authorization(user_role, "validate_batch")
    inp = ValidateBatchInput(**payload)
    violations: List[str] = []

    if len(inp.order_ids) > inp.max_orders:
        violations.append(f"Order count {len(inp.order_ids)} exceeds max allowed {inp.max_orders}.")

    pending = WarehouseOptimizationService._fetch_pending_orders(db, inp.warehouse_id)
    order_map = {o.id: o for o in pending}

    total_weight = 0.0
    total_volume = 0.0

    for oid in inp.order_ids:
        if oid not in order_map:
            violations.append(f"Order ID {oid} is invalid or not in 'pending' status for warehouse {inp.warehouse_id}.")
            continue
        o = order_map[oid]
        total_weight += o.total_weight_kg
        total_volume += o.total_volume_cbm

    if total_weight > inp.max_weight_kg:
        violations.append(f"Total weight {total_weight:.2f}kg exceeds limit {inp.max_weight_kg:.2f}kg.")
    if total_volume > inp.max_volume_cbm:
        violations.append(f"Total volume {total_volume:.4f}cbm exceeds limit {inp.max_volume_cbm:.4f}cbm.")

    out = ValidateBatchOutput(
        is_valid=len(violations) == 0,
        violations=violations,
        total_orders=len(inp.order_ids),
        total_weight_kg=round(total_weight, 2),
        total_volume_cbm=round(total_volume, 4)
    )
    return out.model_dump()


# ---------------------------------------------------------------------------
# Tool 8: validate_pick_route
# ---------------------------------------------------------------------------
class ValidatePickRouteInput(BaseModel):
    warehouse_id: int = Field(..., gt=0)
    start_node_id: int = Field(..., gt=0)
    target_node_ids: List[int] = Field(..., min_items=1)


class ValidatePickRouteOutput(BaseModel):
    is_valid: bool
    unreachable_nodes: List[int]
    total_distance_meters: float


def tool_validate_pick_route(db: Session, user_role: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validates reachability of target nodes from start_node_id."""
    _check_authorization(user_role, "validate_pick_route")
    inp = ValidatePickRouteInput(**payload)
    try:
        graph = GraphEngine.load_warehouse_graph(db, inp.warehouse_id)
        unreachable: List[int] = []
        total_dist = 0.0
        curr = inp.start_node_id

        for target in inp.target_node_ids:
            res = GraphEngine.find_shortest_path_a_star(graph, curr, target)
            if not res.success:
                unreachable.append(target)
            else:
                total_dist += res.total_distance
                curr = target

        out = ValidatePickRouteOutput(
            is_valid=len(unreachable) == 0,
            unreachable_nodes=unreachable,
            total_distance_meters=round(total_dist, 2)
        )
        return out.model_dump()
    except Exception as err:
        return ValidatePickRouteOutput(
            is_valid=False, unreachable_nodes=inp.target_node_ids, total_distance_meters=0.0
        ).model_dump()


# ---------------------------------------------------------------------------
# Tool 9: calculate_warehouse_metrics
# ---------------------------------------------------------------------------
class CalculateWarehouseMetricsInput(BaseModel):
    warehouse_id: int = Field(..., gt=0)


class CalculateWarehouseMetricsOutput(BaseModel):
    success: bool
    warehouse_id: int
    total_nodes: int
    pending_orders_count: int
    total_stock_units: int
    error: Optional[str] = None


def tool_calculate_warehouse_metrics(db: Session, user_role: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Calculates operational status metrics for a warehouse."""
    _check_authorization(user_role, "calculate_warehouse_metrics")
    inp = CalculateWarehouseMetricsInput(**payload)
    try:
        graph = GraphEngine.load_warehouse_graph(db, inp.warehouse_id)
        pending = WarehouseOptimizationService._fetch_pending_orders(db, inp.warehouse_id)
        stock_map = WarehouseOptimizationService._fetch_inventory_map(db, inp.warehouse_id)
        total_units = sum(stock_map.values())

        out = CalculateWarehouseMetricsOutput(
            success=True,
            warehouse_id=inp.warehouse_id,
            total_nodes=len(graph.nodes),
            pending_orders_count=len(pending),
            total_stock_units=total_units
        )
        return out.model_dump()
    except Exception as err:
        return CalculateWarehouseMetricsOutput(
            success=False, warehouse_id=inp.warehouse_id, total_nodes=0,
            pending_orders_count=0, total_stock_units=0, error=str(err)
        ).model_dump()


# ---------------------------------------------------------------------------
# Central Tool Registry & Dispatcher
# ---------------------------------------------------------------------------
WAREHOUSE_TOOL_REGISTRY = {
    "get_warehouse_graph": tool_get_warehouse_graph,
    "get_eligible_orders": tool_get_eligible_orders,
    "get_inventory_state": tool_get_inventory_state,
    "calculate_shortest_path": tool_calculate_shortest_path,
    "generate_order_batches": tool_generate_order_batches,
    "generate_pick_route": tool_generate_pick_route,
    "validate_batch": tool_validate_batch,
    "validate_pick_route": tool_validate_pick_route,
    "calculate_warehouse_metrics": tool_calculate_warehouse_metrics,
}


def dispatch_warehouse_tool(db: Session, user_role: str, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Controlled Entry Point for Agent Tool Execution.
    Rejects unregistered tool names, arbitrary code execution, and unauthorized roles.
    """
    if tool_name not in WAREHOUSE_TOOL_REGISTRY:
        raise ValueError(
            f"Invalid tool '{tool_name}'. Allowed tools: {list(WAREHOUSE_TOOL_REGISTRY.keys())}"
        )

    tool_fn = WAREHOUSE_TOOL_REGISTRY[tool_name]
    return tool_fn(db, user_role, payload)
