"""
Unit tests for Phase 3.3 Pick Route Optimization Engine.
Tests baseline input order, Nearest-Neighbor heuristic, 2-Opt local search improvement, duplicate target handling, unreachable nodes, and metric improvement calculation.
"""
import pytest
from backend.app.services.warehouse_graph import WarehouseGraph, GraphNode, GraphEdge
from backend.app.services.pick_routing_engine import (
    PickRouteOptimizationEngine, PickTargetDTO, PickRouteResult
)


@pytest.fixture
def grid_warehouse_graph() -> WarehouseGraph:
    """
    Creates a 4x4 grid dark-store graph (16 nodes, node_id 1..16).
    Node 1 (0,0) is entrance/start.
    Distance between adjacent grid nodes = 5.0 meters.
    """
    g = WarehouseGraph(warehouse_id=1)
    # Add 16 nodes
    for y in range(4):
        for x in range(4):
            nid = y * 4 + x + 1
            g.add_node(GraphNode(
                id=nid, warehouse_id=1, node_code=f"N{nid}",
                x_coord=float(x * 5), y_coord=float(y * 5), z_coord=0.0,
                zone_id=1, is_blocked=False
            ))

    # Add grid horizontal and vertical edges
    edge_id = 1
    for y in range(4):
        for x in range(4):
            curr = y * 4 + x + 1
            if x + 1 < 4:
                right = y * 4 + (x + 1) + 1
                g.add_edge(GraphEdge(id=edge_id, warehouse_id=1, from_node_id=curr, to_node_id=right, distance_meters=5.0, is_bidirectional=True, is_blocked=False))
                edge_id += 1
            if y + 1 < 4:
                down = (y + 1) * 4 + x + 1
                g.add_edge(GraphEdge(id=edge_id, warehouse_id=1, from_node_id=curr, to_node_id=down, distance_meters=5.0, is_bidirectional=True, is_blocked=False))
                edge_id += 1

    return g


def test_empty_targets(grid_warehouse_graph):
    res = PickRouteOptimizationEngine.calculate_baseline_input_order(grid_warehouse_graph, [], start_node_id=1)
    assert res.success is True
    assert res.ordered_location_ids == []
    assert res.total_distance_meters == 0.0


def test_single_location_route(grid_warehouse_graph):
    targets = [PickTargetDTO(location_id=101, node_id=16, product_id=1, quantity_to_pick=2)]
    res = PickRouteOptimizationEngine.calculate_baseline_input_order(grid_warehouse_graph, targets, start_node_id=1)
    
    assert res.success is True
    assert res.ordered_location_ids == [101]
    # Path (0,0) -> (15,15) distance = 30.0m
    assert res.total_distance_meters == 30.0


def test_duplicate_target_locations(grid_warehouse_graph):
    # Two order items at the same location_id 101 (node 6)
    targets = [
        PickTargetDTO(location_id=101, node_id=6, product_id=1, quantity_to_pick=2),
        PickTargetDTO(location_id=101, node_id=6, product_id=2, quantity_to_pick=3),
    ]
    res = PickRouteOptimizationEngine.calculate_baseline_input_order(grid_warehouse_graph, targets, start_node_id=1)
    
    assert res.success is True
    assert res.ordered_location_ids == [101]
    # Total pick quantity consolidated


def test_baseline_vs_2opt_heuristic_improvement(grid_warehouse_graph):
    """
    Suboptimal input order payload: Start(1) -> Target A(node 16 [15,15]) -> Target B(node 2 [5,0]) -> Target C(node 15 [10,15])
    Input order distance will backtrack back and forth.
    2-Opt heuristic will re-order locations to minimize walking.
    """
    targets = [
        PickTargetDTO(location_id=101, node_id=16, product_id=1, quantity_to_pick=1), # (15,15)
        PickTargetDTO(location_id=102, node_id=2, product_id=2, quantity_to_pick=1),  # (5,0)
        PickTargetDTO(location_id=103, node_id=15, product_id=3, quantity_to_pick=1), # (10,15)
    ]
    
    res_base = PickRouteOptimizationEngine.calculate_baseline_input_order(grid_warehouse_graph, targets, start_node_id=1)
    res_opt = PickRouteOptimizationEngine.optimize_route_heuristic(grid_warehouse_graph, targets, start_node_id=1, use_2opt=True)
    
    assert res_base.success is True
    assert res_opt.success is True
    assert res_opt.algorithm_used == "nearest_neighbor_2opt"
    assert res_opt.total_distance_meters < res_base.total_distance_meters
    assert res_opt.improvement_percentage is not None
    assert res_opt.improvement_percentage > 0.0


def test_unreachable_target_location(grid_warehouse_graph):
    # Add disconnected isolated node 99
    grid_warehouse_graph.add_node(GraphNode(id=99, warehouse_id=1, node_code="N99", x_coord=50.0, y_coord=50.0, z_coord=0.0, zone_id=1, is_blocked=False))
    
    targets = [
        PickTargetDTO(location_id=101, node_id=2, product_id=1, quantity_to_pick=1),
        PickTargetDTO(location_id=999, node_id=99, product_id=2, quantity_to_pick=1) # Isolated node
    ]
    
    res = PickRouteOptimizationEngine.optimize_route_heuristic(grid_warehouse_graph, targets, start_node_id=1)
    assert res.success is False
    assert 999 in res.unreachable_location_ids


def test_invalid_start_node(grid_warehouse_graph):
    targets = [PickTargetDTO(location_id=101, node_id=2, product_id=1, quantity_to_pick=1)]
    res = PickRouteOptimizationEngine.calculate_baseline_input_order(grid_warehouse_graph, targets, start_node_id=9999)
    assert res.success is False
    assert "not in graph" in res.failure_reason


def test_determinism(grid_warehouse_graph):
    targets = [
        PickTargetDTO(location_id=101, node_id=16, product_id=1, quantity_to_pick=1),
        PickTargetDTO(location_id=102, node_id=2, product_id=2, quantity_to_pick=1),
        PickTargetDTO(location_id=103, node_id=15, product_id=3, quantity_to_pick=1),
    ]
    res1 = PickRouteOptimizationEngine.optimize_route_heuristic(grid_warehouse_graph, targets, start_node_id=1)
    res2 = PickRouteOptimizationEngine.optimize_route_heuristic(grid_warehouse_graph, targets, start_node_id=1)
    
    assert res1.ordered_location_ids == res2.ordered_location_ids
    assert res1.total_distance_meters == res2.total_distance_meters
    assert res1.improvement_percentage == res2.improvement_percentage
