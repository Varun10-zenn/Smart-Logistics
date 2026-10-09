"""
Warehouse Graph Engine Module.
Phase 3.1 — Deterministic indoor warehouse graph loading and pathfinding (Dijkstra & A*).
"""
import math
import time
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
import heapq

from sqlalchemy.orm import Session
from backend.app.models.warehouse import Warehouse, WarehouseNode, WarehouseEdge


@dataclass
class GraphNode:
    id: int
    warehouse_id: int
    node_code: str
    x_coord: float
    y_coord: float
    z_coord: float
    zone_id: Optional[int]
    is_blocked: bool
    is_depot: bool = False



@dataclass
class GraphEdge:
    id: int
    warehouse_id: int
    from_node_id: int
    to_node_id: int
    distance_meters: float
    is_bidirectional: bool
    is_blocked: bool


@dataclass
class GraphPathResult:
    success: bool
    path: List[int]
    total_distance: float
    nodes_visited: int
    algorithm: str
    execution_time_ms: float
    failure_reason: Optional[str] = None


class WarehouseGraph:
    """In-memory weighted directed/bidirectional graph representation of a dark store layout."""

    def __init__(self, warehouse_id: int):
        self.warehouse_id: int = warehouse_id
        self.nodes: Dict[int, GraphNode] = {}
        self.edges: Dict[int, GraphEdge] = {}
        # Adjacency list: node_id -> List[Tuple[neighbor_id, distance_meters, edge_id]]
        self.adjacency: Dict[int, List[Tuple[int, float, int]]] = {}

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node
        if node.id not in self.adjacency:
            self.adjacency[node.id] = []

    def add_edge(self, edge: GraphEdge) -> None:
        if edge.from_node_id not in self.nodes:
            raise ValueError(f"Invalid from_node_id {edge.from_node_id} for edge {edge.id}")
        if edge.to_node_id not in self.nodes:
            raise ValueError(f"Invalid to_node_id {edge.to_node_id} for edge {edge.id}")
        if edge.distance_meters < 0:
            raise ValueError(f"Negative edge distance {edge.distance_meters} unsupported for edge {edge.id}")

        self.edges[edge.id] = edge

        # Add forward edge if not blocked
        if not edge.is_blocked and not self.nodes[edge.from_node_id].is_blocked and not self.nodes[edge.to_node_id].is_blocked:
            self.adjacency[edge.from_node_id].append((edge.to_node_id, float(edge.distance_meters), edge.id))
            if edge.is_bidirectional:
                self.adjacency[edge.to_node_id].append((edge.from_node_id, float(edge.distance_meters), edge.id))

    def get_neighbors(self, node_id: int) -> List[Tuple[int, float, int]]:
        return self.adjacency.get(node_id, [])


class GraphEngine:
    """Deterministic pathfinding engine supporting Dijkstra and A* algorithms."""

    @staticmethod
    def load_warehouse_graph(db: Session, warehouse_id: int) -> WarehouseGraph:
        """
        Retrieves warehouse, nodes, and edges from database and constructs an in-memory WarehouseGraph.
        Validates references and handles empty/malformed graph state safely.
        """
        warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
        if not warehouse:
            raise ValueError(f"Warehouse with ID {warehouse_id} not found.")

        graph = WarehouseGraph(warehouse_id=warehouse_id)

        db_nodes = db.query(WarehouseNode).filter(WarehouseNode.warehouse_id == warehouse_id).all()
        for dn in db_nodes:
            node = GraphNode(
                id=dn.id,
                warehouse_id=dn.warehouse_id,
                node_code=dn.node_code,
                x_coord=float(dn.x_coord),
                y_coord=float(dn.y_coord),
                z_coord=float(dn.z_coord),
                zone_id=dn.zone_id,
                is_blocked=dn.is_blocked,
                is_depot=getattr(dn, "is_depot", False),
            )

            graph.add_node(node)

        db_edges = db.query(WarehouseEdge).filter(WarehouseEdge.warehouse_id == warehouse_id).all()
        for de in db_edges:
            # Skip edge if it references nodes outside this warehouse graph
            if de.from_node_id not in graph.nodes or de.to_node_id not in graph.nodes:
                continue
            edge = GraphEdge(
                id=de.id,
                warehouse_id=de.warehouse_id,
                from_node_id=de.from_node_id,
                to_node_id=de.to_node_id,
                distance_meters=float(de.distance_meters),
                is_bidirectional=de.is_bidirectional,
                is_blocked=de.is_blocked,
            )
            graph.add_edge(edge)

        return graph

    @staticmethod
    def find_shortest_path_dijkstra(
        graph: WarehouseGraph,
        start_node_id: int,
        destination_node_id: int
    ) -> GraphPathResult:
        """Calculates deterministic shortest path using Dijkstra's algorithm."""
        return GraphEngine._search(graph, start_node_id, destination_node_id, algorithm="dijkstra")

    @staticmethod
    def find_shortest_path_a_star(
        graph: WarehouseGraph,
        start_node_id: int,
        destination_node_id: int
    ) -> GraphPathResult:
        """
        Calculates deterministic shortest path using A* search algorithm with Euclidean 3D heuristic.
        Admissible heuristic: h(n) = sqrt((x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2).
        """
        return GraphEngine._search(graph, start_node_id, destination_node_id, algorithm="a_star")

    @staticmethod
    def _search(
        graph: WarehouseGraph,
        start_node_id: int,
        destination_node_id: int,
        algorithm: str
    ) -> GraphPathResult:
        start_time = time.perf_counter()

        # Validation checks
        if not graph.nodes:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
            return GraphPathResult(
                success=False, path=[], total_distance=0.0, nodes_visited=0,
                algorithm=algorithm, execution_time_ms=elapsed_ms, failure_reason="Empty graph."
            )

        if start_node_id not in graph.nodes:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
            return GraphPathResult(
                success=False, path=[], total_distance=0.0, nodes_visited=0,
                algorithm=algorithm, execution_time_ms=elapsed_ms,
                failure_reason=f"Start node ID {start_node_id} not in graph."
            )

        if destination_node_id not in graph.nodes:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
            return GraphPathResult(
                success=False, path=[], total_distance=0.0, nodes_visited=0,
                algorithm=algorithm, execution_time_ms=elapsed_ms,
                failure_reason=f"Destination node ID {destination_node_id} not in graph."
            )

        if graph.nodes[start_node_id].is_blocked:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
            return GraphPathResult(
                success=False, path=[], total_distance=0.0, nodes_visited=0,
                algorithm=algorithm, execution_time_ms=elapsed_ms,
                failure_reason=f"Start node ID {start_node_id} is blocked."
            )

        if graph.nodes[destination_node_id].is_blocked:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
            return GraphPathResult(
                success=False, path=[], total_distance=0.0, nodes_visited=0,
                algorithm=algorithm, execution_time_ms=elapsed_ms,
                failure_reason=f"Destination node ID {destination_node_id} is blocked."
            )

        # Same start and destination
        if start_node_id == destination_node_id:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
            return GraphPathResult(
                success=True, path=[start_node_id], total_distance=0.0, nodes_visited=1,
                algorithm=algorithm, execution_time_ms=elapsed_ms, failure_reason=None
            )

        dest_node = graph.nodes[destination_node_id]

        def heuristic(node_id: int) -> float:
            if algorithm == "dijkstra":
                return 0.0
            n = graph.nodes[node_id]
            dx = n.x_coord - dest_node.x_coord
            dy = n.y_coord - dest_node.y_coord
            dz = n.z_coord - dest_node.z_coord
            return math.sqrt(dx * dx + dy * dy + dz * dz)

        # Priority queue stores tuples of (f_score, g_score, node_id)
        open_set: List[Tuple[float, float, int]] = []
        heapq.heappush(open_set, (heuristic(start_node_id), 0.0, start_node_id))

        g_score: Dict[int, float] = {start_node_id: 0.0}
        came_from: Dict[int, int] = {}
        visited: Set[int] = set()

        while open_set:
            _, current_g, current = heapq.heappop(open_set)

            if current in visited:
                continue
            visited.add(current)

            if current == destination_node_id:
                # Reconstruct path
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
                return GraphPathResult(
                    success=True,
                    path=path,
                    total_distance=round(current_g, 2),
                    nodes_visited=len(visited),
                    algorithm=algorithm,
                    execution_time_ms=elapsed_ms,
                    failure_reason=None,
                )

            for neighbor, weight, _ in graph.get_neighbors(current):
                if neighbor in visited:
                    continue

                tentative_g = current_g + weight
                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + heuristic(neighbor)
                    heapq.heappush(open_set, (f_score, tentative_g, neighbor))

        # Unreachable destination
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
        return GraphPathResult(
            success=False,
            path=[],
            total_distance=0.0,
            nodes_visited=len(visited),
            algorithm=algorithm,
            execution_time_ms=elapsed_ms,
            failure_reason=f"Destination node {destination_node_id} is unreachable from start node {start_node_id}.",
        )
