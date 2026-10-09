"""
Unit tests for Phase 3.1 Warehouse Graph Engine & Pathfinding Algorithms.
Tests Dijkstra and A* algorithms across simple, complex, blocked, and edge-case graphs.
"""
import pytest
from backend.app.services.warehouse_graph import (
    WarehouseGraph, GraphNode, GraphEdge, GraphEngine, GraphPathResult
)


@pytest.fixture
def sample_graph() -> WarehouseGraph:
    """
    Creates a sample 5-node warehouse graph:
    (1) --10.0-- (2) --5.0-- (3)
     |            |           |
    15.0         8.0        12.0
     |            |           |
    (4) ---------3.0-------- (5)
    """
    g = WarehouseGraph(warehouse_id=1)
    g.add_node(GraphNode(id=1, warehouse_id=1, node_code="N1", x_coord=0.0, y_coord=0.0, z_coord=0.0, zone_id=1, is_blocked=False))
    g.add_node(GraphNode(id=2, warehouse_id=1, node_code="N2", x_coord=10.0, y_coord=0.0, z_coord=0.0, zone_id=1, is_blocked=False))
    g.add_node(GraphNode(id=3, warehouse_id=1, node_code="N3", x_coord=15.0, y_coord=0.0, z_coord=0.0, zone_id=1, is_blocked=False))
    g.add_node(GraphNode(id=4, warehouse_id=1, node_code="N4", x_coord=0.0, y_coord=10.0, z_coord=0.0, zone_id=2, is_blocked=False))
    g.add_node(GraphNode(id=5, warehouse_id=1, node_code="N5", x_coord=15.0, y_coord=10.0, z_coord=0.0, zone_id=2, is_blocked=False))

    g.add_edge(GraphEdge(id=101, warehouse_id=1, from_node_id=1, to_node_id=2, distance_meters=10.0, is_bidirectional=True, is_blocked=False))
    g.add_edge(GraphEdge(id=102, warehouse_id=1, from_node_id=2, to_node_id=3, distance_meters=5.0, is_bidirectional=True, is_blocked=False))
    g.add_edge(GraphEdge(id=103, warehouse_id=1, from_node_id=1, to_node_id=4, distance_meters=15.0, is_bidirectional=True, is_blocked=False))
    g.add_edge(GraphEdge(id=104, warehouse_id=1, from_node_id=2, to_node_id=5, distance_meters=8.0, is_bidirectional=True, is_blocked=False))
    g.add_edge(GraphEdge(id=105, warehouse_id=1, from_node_id=3, to_node_id=5, distance_meters=12.0, is_bidirectional=True, is_blocked=False))
    g.add_edge(GraphEdge(id=106, warehouse_id=1, from_node_id=4, to_node_id=5, distance_meters=3.0, is_bidirectional=True, is_blocked=False))
    return g


def test_simple_path(sample_graph):
    # Path from N1 to N2 -> direct edge distance 10.0
    res = GraphEngine.find_shortest_path_dijkstra(sample_graph, 1, 2)
    assert res.success is True
    assert res.path == [1, 2]
    assert res.total_distance == 10.0
    assert res.algorithm == "dijkstra"


def test_multiple_paths_shortest_selection(sample_graph):
    # From N1 to N5:
    # Route A: N1 -> N2 -> N5 (10.0 + 8.0 = 18.0)
    # Route B: N1 -> N4 -> N5 (15.0 + 3.0 = 18.0)
    # Route C: N1 -> N2 -> N3 -> N5 (10.0 + 5.0 + 12.0 = 27.0)
    res_d = GraphEngine.find_shortest_path_dijkstra(sample_graph, 1, 5)
    res_a = GraphEngine.find_shortest_path_a_star(sample_graph, 1, 5)

    assert res_d.success is True
    assert res_a.success is True
    assert res_d.total_distance == 18.0
    assert res_a.total_distance == 18.0
    assert res_d.total_distance == res_a.total_distance


def test_same_start_and_destination(sample_graph):
    res = GraphEngine.find_shortest_path_dijkstra(sample_graph, 3, 3)
    assert res.success is True
    assert res.path == [3]
    assert res.total_distance == 0.0


def test_unreachable_destination():
    g = WarehouseGraph(warehouse_id=1)
    g.add_node(GraphNode(id=1, warehouse_id=1, node_code="N1", x_coord=0.0, y_coord=0.0, z_coord=0.0, zone_id=1, is_blocked=False))
    g.add_node(GraphNode(id=2, warehouse_id=1, node_code="N2", x_coord=5.0, y_coord=5.0, z_coord=0.0, zone_id=1, is_blocked=False))
    # No edge added between N1 and N2

    res = GraphEngine.find_shortest_path_dijkstra(g, 1, 2)
    assert res.success is False
    assert res.path == []
    assert "unreachable" in res.failure_reason.lower()


def test_invalid_start_node(sample_graph):
    res = GraphEngine.find_shortest_path_dijkstra(sample_graph, 999, 2)
    assert res.success is False
    assert "not in graph" in res.failure_reason


def test_invalid_destination_node(sample_graph):
    res = GraphEngine.find_shortest_path_dijkstra(sample_graph, 1, 999)
    assert res.success is False
    assert "not in graph" in res.failure_reason


def test_empty_graph():
    g = WarehouseGraph(warehouse_id=1)
    res = GraphEngine.find_shortest_path_dijkstra(g, 1, 2)
    assert res.success is False
    assert "empty graph" in res.failure_reason.lower()


def test_blocked_node_avoidance():
    g = WarehouseGraph(warehouse_id=1)
    g.add_node(GraphNode(id=1, warehouse_id=1, node_code="N1", x_coord=0.0, y_coord=0.0, z_coord=0.0, zone_id=1, is_blocked=False))
    g.add_node(GraphNode(id=2, warehouse_id=1, node_code="N2", x_coord=5.0, y_coord=0.0, z_coord=0.0, zone_id=1, is_blocked=True)) # BLOCKED
    g.add_node(GraphNode(id=3, warehouse_id=1, node_code="N3", x_coord=10.0, y_coord=0.0, z_coord=0.0, zone_id=1, is_blocked=False))
    g.add_node(GraphNode(id=4, warehouse_id=1, node_code="N4", x_coord=5.0, y_coord=5.0, z_coord=0.0, zone_id=1, is_blocked=False))

    g.add_edge(GraphEdge(id=1, warehouse_id=1, from_node_id=1, to_node_id=2, distance_meters=5.0, is_bidirectional=True, is_blocked=False))
    g.add_edge(GraphEdge(id=2, warehouse_id=1, from_node_id=2, to_node_id=3, distance_meters=5.0, is_bidirectional=True, is_blocked=False))
    g.add_edge(GraphEdge(id=3, warehouse_id=1, from_node_id=1, to_node_id=4, distance_meters=4.0, is_bidirectional=True, is_blocked=False))
    g.add_edge(GraphEdge(id=4, warehouse_id=1, from_node_id=4, to_node_id=3, distance_meters=4.0, is_bidirectional=True, is_blocked=False))

    # Path 1 -> 2 -> 3 is blocked at N2, so algorithm must choose 1 -> 4 -> 3
    res = GraphEngine.find_shortest_path_dijkstra(g, 1, 3)
    assert res.success is True
    assert res.path == [1, 4, 3]
    assert res.total_distance == 8.0


def test_dijkstra_vs_a_star_equivalence(sample_graph):
    for start in [1, 2, 3, 4, 5]:
        for dest in [1, 2, 3, 4, 5]:
            res_d = GraphEngine.find_shortest_path_dijkstra(sample_graph, start, dest)
            res_a = GraphEngine.find_shortest_path_a_star(sample_graph, start, dest)
            assert res_d.success == res_a.success
            assert res_d.total_distance == res_a.total_distance
