"""
Pick Route Optimization Engine Module.
Phase 3.3 — Indoor pick route optimization using Nearest-Neighbor & 2-Opt local search heuristics over WarehouseGraph.
"""
import math
import time
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field

from backend.app.services.warehouse_graph import WarehouseGraph, GraphEngine


@dataclass
class PickTargetDTO:
    location_id: int
    node_id: int
    product_id: int
    quantity_to_pick: int


@dataclass
class PickRouteResult:
    success: bool
    algorithm_used: str
    ordered_location_ids: List[int]
    traversed_node_ids: List[int]
    total_distance_meters: float
    estimated_duration_minutes: float
    unreachable_location_ids: List[int]
    baseline_distance_meters: Optional[float]
    optimized_distance_meters: Optional[float]
    improvement_percentage: Optional[float]
    execution_time_ms: float
    failure_reason: Optional[str] = None


class PickRouteOptimizationEngine:
    """
    Pick Route Optimization Engine.
    Computes baseline input-order routes, Nearest-Neighbor routes, and 2-Opt heuristic routes over WarehouseGraph.
    """

    AVERAGE_PICKER_SPEED_MPS = 1.2    # ~4.3 km/h
    ITEM_PICK_TIME_SECONDS = 15.0     # 15 seconds per location

    @staticmethod
    def _deduplicate_targets(targets: List[PickTargetDTO]) -> List[PickTargetDTO]:
        """Deduplicates pick targets by location_id while accumulating quantities."""
        seen: Dict[int, PickTargetDTO] = {}
        for t in targets:
            if t.location_id in seen:
                existing = seen[t.location_id]
                seen[t.location_id] = PickTargetDTO(
                    location_id=t.location_id,
                    node_id=t.node_id,
                    product_id=t.product_id,
                    quantity_to_pick=existing.quantity_to_pick + t.quantity_to_pick
                )
            else:
                seen[t.location_id] = PickTargetDTO(
                    location_id=t.location_id,
                    node_id=t.node_id,
                    product_id=t.product_id,
                    quantity_to_pick=t.quantity_to_pick
                )
        return list(seen.values())

    @staticmethod
    def _build_pairwise_distance_matrix(
        graph: WarehouseGraph,
        nodes: List[int]
    ) -> Dict[Tuple[int, int], Tuple[float, List[int]]]:
        """Precomputes pairwise shortest path distance and node paths between all distinct nodes."""
        matrix: Dict[Tuple[int, int], Tuple[float, List[int]]] = {}
        unique_nodes = list(set(nodes))

        for src in unique_nodes:
            for dst in unique_nodes:
                if src == dst:
                    matrix[(src, dst)] = (0.0, [src])
                elif (src, dst) not in matrix:
                    res = GraphEngine.find_shortest_path_a_star(graph, src, dst)
                    if res.success:
                        matrix[(src, dst)] = (res.total_distance, res.path)
                        matrix[(dst, src)] = (res.total_distance, list(reversed(res.path)))
                    else:
                        matrix[(src, dst)] = (float("inf"), [])
                        matrix[(dst, src)] = (float("inf"), [])
        return matrix

    @staticmethod
    def calculate_baseline_input_order(
        graph: WarehouseGraph,
        targets: List[PickTargetDTO],
        start_node_id: int,
        end_node_id: Optional[int] = None
    ) -> PickRouteResult:
        """
        Baseline strategy: Visits pick locations in the exact order provided in the input payload.
        """
        start_time = time.perf_counter()

        if not graph.nodes:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
            return PickRouteResult(
                success=False, algorithm_used="baseline_input_order", ordered_location_ids=[],
                traversed_node_ids=[], total_distance_meters=0.0, estimated_duration_minutes=0.0,
                unreachable_location_ids=[], baseline_distance_meters=None, optimized_distance_meters=None,
                improvement_percentage=None, execution_time_ms=elapsed_ms, failure_reason="Empty graph."
            )

        if start_node_id not in graph.nodes:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
            return PickRouteResult(
                success=False, algorithm_used="baseline_input_order", ordered_location_ids=[],
                traversed_node_ids=[], total_distance_meters=0.0, estimated_duration_minutes=0.0,
                unreachable_location_ids=[], baseline_distance_meters=None, optimized_distance_meters=None,
                improvement_percentage=None, execution_time_ms=elapsed_ms, failure_reason=f"Start node {start_node_id} not in graph."
            )

        if not targets:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
            return PickRouteResult(
                success=True, algorithm_used="baseline_input_order", ordered_location_ids=[],
                traversed_node_ids=[start_node_id], total_distance_meters=0.0, estimated_duration_minutes=0.0,
                unreachable_location_ids=[], baseline_distance_meters=0.0, optimized_distance_meters=0.0,
                improvement_percentage=0.0, execution_time_ms=elapsed_ms
            )

        unique_targets = PickRouteOptimizationEngine._deduplicate_targets(targets)
        target_nodes = [t.node_id for t in unique_targets]
        all_nodes = [start_node_id] + target_nodes + ([end_node_id] if end_node_id else [])

        matrix = PickRouteOptimizationEngine._build_pairwise_distance_matrix(graph, all_nodes)

        current_node = start_node_id
        total_dist = 0.0
        traversed: List[int] = [start_node_id]
        ordered_locations: List[int] = []
        unreachable: List[int] = []

        for target in unique_targets:
            dist, path = matrix.get((current_node, target.node_id), (float("inf"), []))
            if math.isinf(dist) or not path:
                unreachable.append(target.location_id)
            else:
                total_dist += dist
                if len(path) > 1:
                    traversed.extend(path[1:])
                ordered_locations.append(target.location_id)
                current_node = target.node_id

        if end_node_id and current_node != end_node_id:
            dist, path = matrix.get((current_node, end_node_id), (float("inf"), []))
            if not math.isinf(dist) and path:
                total_dist += dist
                if len(path) > 1:
                    traversed.extend(path[1:])

        total_picks = len(ordered_locations)
        travel_time_sec = total_dist / PickRouteOptimizationEngine.AVERAGE_PICKER_SPEED_MPS
        pick_time_sec = total_picks * PickRouteOptimizationEngine.ITEM_PICK_TIME_SECONDS
        duration_min = round((travel_time_sec + pick_time_sec) / 60.0, 2)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)

        return PickRouteResult(
            success=len(unreachable) == 0,
            algorithm_used="baseline_input_order",
            ordered_location_ids=ordered_locations,
            traversed_node_ids=traversed,
            total_distance_meters=round(total_dist, 2),
            estimated_duration_minutes=duration_min,
            unreachable_location_ids=unreachable,
            baseline_distance_meters=round(total_dist, 2),
            optimized_distance_meters=round(total_dist, 2),
            improvement_percentage=0.0,
            execution_time_ms=elapsed_ms,
            failure_reason=f"Unreachable locations: {unreachable}" if unreachable else None
        )

    @staticmethod
    def optimize_route_heuristic(
        graph: WarehouseGraph,
        targets: List[PickTargetDTO],
        start_node_id: int,
        end_node_id: Optional[int] = None,
        use_2opt: bool = True
    ) -> PickRouteResult:
        """
        Heuristic Pick Route Optimizer.
        1. Computes baseline input order route distance.
        2. Applies Nearest-Neighbor greedy routing.
        3. Applies 2-Opt local search heuristic swaps (if use_2opt=True).
        4. Calculates distance improvement percentage over baseline.
        """
        start_time = time.perf_counter()

        # Compute baseline first for comparison
        baseline_res = PickRouteOptimizationEngine.calculate_baseline_input_order(
            graph, targets, start_node_id, end_node_id
        )

        if not baseline_res.success and baseline_res.failure_reason in ("Empty graph.", f"Start node {start_node_id} not in graph."):
            return baseline_res

        if not targets:
            return baseline_res

        unique_targets = PickRouteOptimizationEngine._deduplicate_targets(targets)
        target_nodes = [t.node_id for t in unique_targets]
        all_nodes = [start_node_id] + target_nodes + ([end_node_id] if end_node_id else [])

        matrix = PickRouteOptimizationEngine._build_pairwise_distance_matrix(graph, all_nodes)

        # Check unreachable targets upfront
        unreachable: List[int] = []
        reachable_targets: List[PickTargetDTO] = []
        for t in unique_targets:
            dist, _ = matrix.get((start_node_id, t.node_id), (float("inf"), []))
            if math.isinf(dist):
                unreachable.append(t.location_id)
            else:
                reachable_targets.append(t)

        if not reachable_targets:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
            return PickRouteResult(
                success=False, algorithm_used="nearest_neighbor_2opt" if use_2opt else "nearest_neighbor",
                ordered_location_ids=[], traversed_node_ids=[], total_distance_meters=0.0,
                estimated_duration_minutes=0.0, unreachable_location_ids=unreachable,
                baseline_distance_meters=baseline_res.baseline_distance_meters,
                optimized_distance_meters=None, improvement_percentage=None,
                execution_time_ms=elapsed_ms, failure_reason="All target locations unreachable."
            )

        # Step 2: Nearest-Neighbor Heuristic Sequence
        current_node = start_node_id
        unvisited = list(reachable_targets)
        nn_sequence: List[PickTargetDTO] = []

        while unvisited:
            nearest_target = min(
                unvisited,
                key=lambda t: matrix.get((current_node, t.node_id), (float("inf"), []))[0]
            )
            dist, _ = matrix.get((current_node, nearest_target.node_id), (float("inf"), []))
            if math.isinf(dist):
                # Remaining unvisited are unreachable from current
                for u in unvisited:
                    unreachable.append(u.location_id)
                break
            nn_sequence.append(nearest_target)
            unvisited.remove(nearest_target)
            current_node = nearest_target.node_id

        # Step 3: 2-Opt Local Search Improvement Heuristic
        optimized_sequence = list(nn_sequence)
        algorithm_name = "nearest_neighbor"

        if use_2opt and len(optimized_sequence) >= 3:
            algorithm_name = "nearest_neighbor_2opt"
            improved = True
            max_iterations = 100
            iteration = 0

            def calc_seq_distance(seq: List[PickTargetDTO]) -> float:
                d = 0.0
                curr = start_node_id
                for item in seq:
                    d += matrix.get((curr, item.node_id), (float("inf"), []))[0]
                    curr = item.node_id
                if end_node_id:
                    d += matrix.get((curr, end_node_id), (float("inf"), []))[0]
                return d

            best_dist = calc_seq_distance(optimized_sequence)

            while improved and iteration < max_iterations:
                improved = False
                iteration += 1
                for i in range(len(optimized_sequence) - 1):
                    for j in range(i + 1, len(optimized_sequence)):
                        # Swap subsegment i:j+1
                        new_seq = optimized_sequence[:i] + list(reversed(optimized_sequence[i:j + 1])) + optimized_sequence[j + 1:]
                        new_dist = calc_seq_distance(new_seq)
                        if new_dist < best_dist - 0.001:  # Threshold for floating point precision
                            best_dist = new_dist
                            optimized_sequence = new_seq
                            improved = True
                            break
                    if improved:
                        break

        # Reconstruct final traversed path and distance
        current_node = start_node_id
        final_distance = 0.0
        traversed: List[int] = [start_node_id]
        ordered_locations: List[int] = []

        for item in optimized_sequence:
            dist, path = matrix.get((current_node, item.node_id), (float("inf"), []))
            if not math.isinf(dist) and path:
                final_distance += dist
                if len(path) > 1:
                    traversed.extend(path[1:])
                ordered_locations.append(item.location_id)
                current_node = item.node_id

        if end_node_id and current_node != end_node_id:
            dist, path = matrix.get((current_node, end_node_id), (float("inf"), []))
            if not math.isinf(dist) and path:
                final_distance += dist
                if len(path) > 1:
                    traversed.extend(path[1:])

        total_picks = len(ordered_locations)
        travel_time_sec = final_distance / PickRouteOptimizationEngine.AVERAGE_PICKER_SPEED_MPS
        pick_time_sec = total_picks * PickRouteOptimizationEngine.ITEM_PICK_TIME_SECONDS
        duration_min = round((travel_time_sec + pick_time_sec) / 60.0, 2)

        # Calculate improvement percentage vs baseline
        baseline_dist = baseline_res.total_distance_meters
        improvement_pct: Optional[float] = None
        if baseline_res.success and baseline_dist > 0:
            improvement_pct = round(((baseline_dist - final_distance) / baseline_dist) * 100.0, 2)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)

        return PickRouteResult(
            success=len(unreachable) == 0,
            algorithm_used=algorithm_name,
            ordered_location_ids=ordered_locations,
            traversed_node_ids=traversed,
            total_distance_meters=round(final_distance, 2),
            estimated_duration_minutes=duration_min,
            unreachable_location_ids=unreachable,
            baseline_distance_meters=round(baseline_dist, 2) if baseline_res.success else None,
            optimized_distance_meters=round(final_distance, 2),
            improvement_percentage=improvement_pct,
            execution_time_ms=elapsed_ms,
            failure_reason=f"Unreachable locations: {unreachable}" if unreachable else None
        )
