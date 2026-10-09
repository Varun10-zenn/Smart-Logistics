"""
Benchmark script for Phase 3.8 Warehouse Optimization.
Runs benchmarks across Graph Navigation, Order Batching, and Pick Route TSP optimization.
"""

import time
import random
from typing import List, Dict, Any

from backend.app.services.warehouse_graph import GraphEngine, WarehouseGraph, GraphNode, GraphEdge
from backend.app.services.order_batcher import OrderBatchingEngine, OrderDTO, BatchingConstraints
from backend.app.services.pick_routing_engine import PickRouteOptimizationEngine, PickTargetDTO


def benchmark_graph(node_count: int, num_runs: int = 10) -> Dict[str, Any]:
    # Build synthetic grid graph
    graph = WarehouseGraph(warehouse_id=1)
    side = int(node_count ** 0.5)
    node_id = 1
    for r in range(side):
        for c in range(side):
            graph.add_node(GraphNode(
                id=node_id, warehouse_id=1, node_code=f"N{node_id}", x_coord=float(c * 2), y_coord=float(r * 2),
                z_coord=0.0, zone_id=None, is_blocked=False
            ))
            node_id += 1

    # Connect grid neighbors
    for nid, n in graph.nodes.items():
        for other_id, other in graph.nodes.items():
            if nid < other_id:
                dist = ((n.x_coord - other.x_coord)**2 + (n.y_coord - other.y_coord)**2)**0.5
                if dist <= 2.1:
                    graph.add_edge(GraphEdge(
                        id=len(graph.edges)+1, warehouse_id=1, from_node_id=nid, to_node_id=other_id, distance_meters=dist,
                        is_bidirectional=True, is_blocked=False
                    ))

    start_id = 1
    dest_id = len(graph.nodes)

    # Dijkstra Benchmark
    dijkstra_times = []
    for _ in range(num_runs):
        t0 = time.perf_counter()
        res_d = GraphEngine.find_shortest_path_dijkstra(graph, start_id, dest_id)
        dijkstra_times.append((time.perf_counter() - t0) * 1000)

    # A* Benchmark
    astar_times = []
    for _ in range(num_runs):
        t0 = time.perf_counter()
        res_a = GraphEngine.find_shortest_path_a_star(graph, start_id, dest_id)
        astar_times.append((time.perf_counter() - t0) * 1000)

    return {
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
        "dijkstra_ms": sum(dijkstra_times) / len(dijkstra_times),
        "astar_ms": sum(astar_times) / len(astar_times),
        "distance": res_a.total_distance,
        "dijkstra_visited": res_d.nodes_visited,
        "astar_visited": res_a.nodes_visited,
    }


def benchmark_batching(order_count: int, num_runs: int = 10) -> Dict[str, Any]:
    from datetime import datetime, timezone
    from backend.app.services.order_batcher import OrderItemDTO
    orders = []
    stock_map = {p: 1000 for p in range(1, 20)}
    now = datetime.now(timezone.utc)
    for i in range(1, order_count + 1):
        item = OrderItemDTO(
            (i % 15) + 1, 1, random.uniform(1.0, 5.0), random.uniform(0.01, 0.03)
        )
        orders.append(OrderDTO(
            id=i,
            order_number=f"ORD-{i}",
            warehouse_id=1,
            priority=1,
            status="pending",
            created_at=now,
            promised_at=now,
            items=[item],
        ))

    constraints = BatchingConstraints(max_orders_per_batch=5, max_weight_kg=25.0, max_volume_cbm=0.12)

    fifo_times, priority_times = [], []
    for _ in range(num_runs):
        t0 = time.perf_counter()
        res_fifo = OrderBatchingEngine.batch_fifo(orders, stock_map, 1, constraints)
        fifo_times.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        res_prio = OrderBatchingEngine.batch_priority_heuristic(orders, stock_map, 1, constraints)
        priority_times.append((time.perf_counter() - t0) * 1000)

    return {
        "orders": order_count,
        "fifo_batches": res_fifo.batch_count,
        "fifo_ms": sum(fifo_times) / len(fifo_times),
        "priority_batches": res_prio.batch_count,
        "priority_ms": sum(priority_times) / len(priority_times),
        "priority_obj": res_prio.objective_value,
    }


def benchmark_picking(location_count: int, num_runs: int = 10) -> Dict[str, Any]:
    # Synthetic line/grid graph
    graph = WarehouseGraph(warehouse_id=1)
    for i in range(1, location_count + 2):
        graph.add_node(GraphNode(id=i, warehouse_id=1, node_code=f"N{i}", x_coord=float((i-1)*2), y_coord=0.0, z_coord=0.0, zone_id=None, is_blocked=False))
        if i > 1:
            graph.add_edge(GraphEdge(id=i-1, warehouse_id=1, from_node_id=i-1, to_node_id=i, distance_meters=2.0, is_bidirectional=True, is_blocked=False))

    # Shuffle targets for pick route optimization
    node_ids = list(range(2, location_count + 2))
    random.shuffle(node_ids)

    targets = [PickTargetDTO(location_id=i, node_id=node_ids[i-1], product_id=1, quantity_to_pick=1) for i in range(1, location_count + 1)]

    nn_times, opt2_times = [], []
    for _ in range(num_runs):
        t0 = time.perf_counter()
        res_baseline = PickRouteOptimizationEngine.optimize_route_heuristic(graph, targets, start_node_id=1, use_2opt=False)
        nn_times.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        res_2opt = PickRouteOptimizationEngine.optimize_route_heuristic(graph, targets, start_node_id=1, use_2opt=True)
        opt2_times.append((time.perf_counter() - t0) * 1000)

    baseline_dist = res_baseline.total_distance_meters
    opt_dist = res_2opt.total_distance_meters
    improvement = ((baseline_dist - opt_dist) / baseline_dist * 100) if baseline_dist > 0 else 0.0

    return {
        "locations": location_count,
        "baseline_dist_m": baseline_dist,
        "baseline_ms": sum(nn_times) / len(nn_times),
        "opt2_dist_m": opt_dist,
        "opt2_ms": sum(opt2_times) / len(opt2_times),
        "improvement_pct": round(improvement, 2),
    }


if __name__ == "__main__":
    print("=== GRAPH NAVIGATION BENCHMARKS ===")
    for n in [10, 100, 1000]:
        print(benchmark_graph(n))

    print("\n=== ORDER BATCHING BENCHMARKS ===")
    for o in [10, 50, 100]:
        print(benchmark_batching(o))

    print("\n=== PICK ROUTING BENCHMARKS ===")
    for l in [5, 20, 50]:
        print(benchmark_picking(l))
