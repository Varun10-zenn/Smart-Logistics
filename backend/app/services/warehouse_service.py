"""Warehouse service."""
import math
from typing import List, Optional, Set, Dict, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.models.warehouse import (
    Warehouse, WarehouseZone, WarehouseNode, WarehouseEdge, StorageLocation, Inventory
)
from backend.app.models.order import Order
from backend.app.models.batch import Batch, PickRouteStep
from backend.app.schemas.common import make_page
from backend.app.schemas.warehouse import (
    WarehouseCreate, WarehouseRead, WarehouseUpdate,
    WarehouseGraphRead, NodeRead, EdgeRead, StorageLocationRead,
    WarehouseZoneCreate, WarehouseZoneRead, WarehouseZoneUpdate,
    WarehouseNodeCreate, WarehouseNodeUpdate,
    WarehouseEdgeCreate, WarehouseEdgeUpdate,
    StorageLocationCreate, StorageLocationUpdate,
    WarehouseValidationRead
)


def _to_read(w: Warehouse) -> WarehouseRead:
    return WarehouseRead(
        id=w.id,
        code=w.code,
        name=w.name,
        latitude=float(w.latitude),
        longitude=float(w.longitude),
        address=w.address,
        status=w.status,
        external_id=getattr(w, 'external_id', None),
        created_at=w.created_at,
    )


def list_warehouses(db: Session, page: int = 1, page_size: int = 20, status: str = None):
    q = db.query(Warehouse)
    if status:
        q = q.filter(Warehouse.status == status)
    total = q.count()
    warehouses = q.order_by(Warehouse.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_to_read(w) for w in warehouses], total, page, page_size)


def create_warehouse(db: Session, data: WarehouseCreate) -> WarehouseRead:
    existing = db.query(Warehouse).filter(Warehouse.code == data.code).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"code": "DUPLICATE_RESOURCE", "message": f"Warehouse code '{data.code}' already exists.", "details": {}},
        )
    wh = Warehouse(
        code=data.code, name=data.name,
        latitude=data.latitude, longitude=data.longitude,
        address=data.address, status="active",
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return _to_read(wh)


def get_warehouse(db: Session, warehouse_id: int) -> WarehouseRead:
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if wh is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Warehouse not found.", "details": {}})
    return _to_read(wh)


def update_warehouse(db: Session, warehouse_id: int, data: WarehouseUpdate) -> WarehouseRead:
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if wh is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Warehouse not found.", "details": {}})
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(wh, field, value)
    db.commit()
    db.refresh(wh)
    return _to_read(wh)


def delete_warehouse(db: Session, warehouse_id: int) -> None:
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if wh is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Warehouse not found.", "details": {}})

    # Check references
    orders_count = db.query(Order).filter(Order.warehouse_id == warehouse_id).count()
    if orders_count > 0:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete warehouse ID {warehouse_id}: referenced by {orders_count} existing orders.", "details": {}}
        )
    batches_count = db.query(Batch).filter(Batch.warehouse_id == warehouse_id).count()
    if batches_count > 0:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete warehouse ID {warehouse_id}: referenced by {batches_count} existing batches.", "details": {}}
        )
    inv_count = db.query(Inventory).filter(Inventory.warehouse_id == warehouse_id).count()
    if inv_count > 0:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete warehouse ID {warehouse_id}: referenced by {inv_count} inventory records.", "details": {}}
        )

    try:
        db.delete(wh)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete warehouse: {str(err)}", "details": {}}
        )


# --- Zones ---
def list_zones(db: Session, warehouse_id: int) -> List[WarehouseZoneRead]:
    get_warehouse(db, warehouse_id)
    zones = db.query(WarehouseZone).filter(WarehouseZone.warehouse_id == warehouse_id).all()
    return [WarehouseZoneRead.model_validate(z) for z in zones]


def create_zone(db: Session, warehouse_id: int, data: WarehouseZoneCreate) -> WarehouseZoneRead:
    get_warehouse(db, warehouse_id)
    existing = db.query(WarehouseZone).filter(
        WarehouseZone.warehouse_id == warehouse_id,
        WarehouseZone.zone_code == data.zone_code
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"code": "DUPLICATE_RESOURCE", "message": f"Zone code '{data.zone_code}' already exists in this warehouse.", "details": {}}
        )
    z = WarehouseZone(
        warehouse_id=warehouse_id,
        zone_code=data.zone_code,
        name=data.name,
        zone_type=data.zone_type,
    )
    db.add(z)
    db.commit()
    db.refresh(z)
    return WarehouseZoneRead.model_validate(z)


def update_zone(db: Session, warehouse_id: int, zone_id: int, data: WarehouseZoneUpdate) -> WarehouseZoneRead:
    z = db.query(WarehouseZone).filter(
        WarehouseZone.id == zone_id,
        WarehouseZone.warehouse_id == warehouse_id
    ).first()
    if not z:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Zone not found.", "details": {}})
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(z, f, v)
    db.commit()
    db.refresh(z)
    return WarehouseZoneRead.model_validate(z)


def delete_zone(db: Session, warehouse_id: int, zone_id: int) -> None:
    z = db.query(WarehouseZone).filter(
        WarehouseZone.id == zone_id,
        WarehouseZone.warehouse_id == warehouse_id
    ).first()
    if not z:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Zone not found.", "details": {}})
    try:
        db.delete(z)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete zone: {str(err)}", "details": {}}
        )


# --- Nodes ---
def _to_node_read(n: WarehouseNode) -> NodeRead:
    return NodeRead(
        id=n.id,
        warehouse_id=n.warehouse_id,
        node_code=n.node_code,
        x_coord=float(n.x_coord),
        y_coord=float(n.y_coord),
        z_coord=float(n.z_coord),
        is_blocked=n.is_blocked,
        is_depot=n.is_depot,
        zone_id=n.zone_id,
    )


def list_nodes(db: Session, warehouse_id: int) -> List[NodeRead]:
    get_warehouse(db, warehouse_id)
    nodes = db.query(WarehouseNode).filter(WarehouseNode.warehouse_id == warehouse_id).all()
    return [_to_node_read(n) for n in nodes]


def create_node(db: Session, warehouse_id: int, data: WarehouseNodeCreate) -> NodeRead:
    get_warehouse(db, warehouse_id)
    existing = db.query(WarehouseNode).filter(
        WarehouseNode.warehouse_id == warehouse_id,
        WarehouseNode.node_code == data.node_code
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"code": "DUPLICATE_RESOURCE", "message": f"Node code '{data.node_code}' already exists in this warehouse.", "details": {}}
        )

    if data.zone_id:
        z = db.query(WarehouseZone).filter(
            WarehouseZone.id == data.zone_id,
            WarehouseZone.warehouse_id == warehouse_id
        ).first()
        if not z:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"Zone ID {data.zone_id} not found in this warehouse.", "details": {}})

    # If setting is_depot=True, unset is_depot on other nodes of the same warehouse
    if data.is_depot:
        db.query(WarehouseNode).filter(
            WarehouseNode.warehouse_id == warehouse_id
        ).update({"is_depot": False})

    node = WarehouseNode(
        warehouse_id=warehouse_id,
        node_code=data.node_code,
        x_coord=data.x_coord,
        y_coord=data.y_coord,
        z_coord=data.z_coord,
        zone_id=data.zone_id,
        is_blocked=data.is_blocked,
        is_depot=data.is_depot,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return _to_node_read(node)


def update_node(db: Session, warehouse_id: int, node_id: int, data: WarehouseNodeUpdate) -> NodeRead:
    node = db.query(WarehouseNode).filter(
        WarehouseNode.id == node_id,
        WarehouseNode.warehouse_id == warehouse_id
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Node not found.", "details": {}})

    updates = data.model_dump(exclude_unset=True)

    if "node_code" in updates and updates["node_code"] != node.node_code:
        dup = db.query(WarehouseNode).filter(
            WarehouseNode.warehouse_id == warehouse_id,
            WarehouseNode.node_code == updates["node_code"]
        ).first()
        if dup:
            raise HTTPException(status_code=409, detail={"code": "DUPLICATE_RESOURCE", "message": f"Node code '{updates['node_code']}' already exists.", "details": {}})

    if updates.get("is_depot") is True:
        db.query(WarehouseNode).filter(
            WarehouseNode.warehouse_id == warehouse_id
        ).update({"is_depot": False})

    for f, v in updates.items():
        setattr(node, f, v)

    db.commit()
    db.refresh(node)
    return _to_node_read(node)


def delete_node(db: Session, warehouse_id: int, node_id: int) -> None:
    node = db.query(WarehouseNode).filter(
        WarehouseNode.id == node_id,
        WarehouseNode.warehouse_id == warehouse_id
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Node not found.", "details": {}})

    # Check references in StorageLocation and WarehouseEdge
    edges_count = db.query(WarehouseEdge).filter(
        (WarehouseEdge.from_node_id == node_id) | (WarehouseEdge.to_node_id == node_id)
    ).count()
    if edges_count > 0:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete node ID {node_id}: referenced by {edges_count} existing edges.", "details": {}}
        )

    loc_count = db.query(StorageLocation).filter(StorageLocation.node_id == node_id).count()
    if loc_count > 0:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete node ID {node_id}: referenced by {loc_count} storage locations.", "details": {}}
        )

    try:
        db.delete(node)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete node: {str(err)}", "details": {}}
        )


# --- Edges ---
def _to_edge_read(e: WarehouseEdge) -> EdgeRead:
    return EdgeRead(
        id=e.id,
        warehouse_id=e.warehouse_id,
        from_node_id=e.from_node_id,
        to_node_id=e.to_node_id,
        distance_meters=float(e.distance_meters),
        is_bidirectional=e.is_bidirectional,
        is_blocked=e.is_blocked,
    )


def list_edges(db: Session, warehouse_id: int) -> List[EdgeRead]:
    get_warehouse(db, warehouse_id)
    edges = db.query(WarehouseEdge).filter(WarehouseEdge.warehouse_id == warehouse_id).all()
    return [_to_edge_read(e) for e in edges]


def create_edge(db: Session, warehouse_id: int, data: WarehouseEdgeCreate) -> EdgeRead:
    get_warehouse(db, warehouse_id)

    if data.from_node_id == data.to_node_id:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_ARGUMENT", "message": "Self-loop edges (from_node == to_node) are not allowed.", "details": {}}
        )

    from_node = db.query(WarehouseNode).filter(WarehouseNode.id == data.from_node_id, WarehouseNode.warehouse_id == warehouse_id).first()
    to_node = db.query(WarehouseNode).filter(WarehouseNode.id == data.to_node_id, WarehouseNode.warehouse_id == warehouse_id).first()
    if not from_node or not to_node:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_ARGUMENT", "message": "From and To nodes must both belong to the target warehouse.", "details": {}}
        )

    # Check for duplicate edge
    dup = db.query(WarehouseEdge).filter(
        WarehouseEdge.warehouse_id == warehouse_id,
        (
            ((WarehouseEdge.from_node_id == data.from_node_id) & (WarehouseEdge.to_node_id == data.to_node_id)) |
            ((WarehouseEdge.from_node_id == data.to_node_id) & (WarehouseEdge.to_node_id == data.from_node_id))
        )
    ).first()
    if dup:
        raise HTTPException(
            status_code=409,
            detail={"code": "DUPLICATE_RESOURCE", "message": "An edge already exists between these two nodes.", "details": {}}
        )

    # Auto calculate distance if omitted
    dist = data.distance_meters
    if dist is None or dist <= 0:
        dx = float(from_node.x_coord) - float(to_node.x_coord)
        dy = float(from_node.y_coord) - float(to_node.y_coord)
        dz = float(from_node.z_coord) - float(to_node.z_coord)
        dist = round(math.sqrt(dx * dx + dy * dy + dz * dz), 2)
        if dist <= 0:
            dist = 1.0

    edge = WarehouseEdge(
        warehouse_id=warehouse_id,
        from_node_id=data.from_node_id,
        to_node_id=data.to_node_id,
        distance_meters=dist,
        is_bidirectional=data.is_bidirectional,
        is_blocked=data.is_blocked,
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return _to_edge_read(edge)


def update_edge(db: Session, warehouse_id: int, edge_id: int, data: WarehouseEdgeUpdate) -> EdgeRead:
    edge = db.query(WarehouseEdge).filter(
        WarehouseEdge.id == edge_id,
        WarehouseEdge.warehouse_id == warehouse_id
    ).first()
    if not edge:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Edge not found.", "details": {}})

    updates = data.model_dump(exclude_unset=True)
    if "distance_meters" in updates and updates["distance_meters"] <= 0:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ARGUMENT", "message": "Distance must be positive.", "details": {}})

    for f, v in updates.items():
        setattr(edge, f, v)

    db.commit()
    db.refresh(edge)
    return _to_edge_read(edge)


def delete_edge(db: Session, warehouse_id: int, edge_id: int) -> None:
    edge = db.query(WarehouseEdge).filter(
        WarehouseEdge.id == edge_id,
        WarehouseEdge.warehouse_id == warehouse_id
    ).first()
    if not edge:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Edge not found.", "details": {}})
    db.delete(edge)
    db.commit()


# --- Storage Locations ---
def _to_loc_read(loc: StorageLocation) -> StorageLocationRead:
    return StorageLocationRead(
        id=loc.id,
        node_id=loc.node_id,
        location_code=loc.location_code,
        aisle=loc.aisle,
        shelf=loc.shelf,
        bin=loc.bin,
        max_weight_kg=float(loc.max_weight_kg),
    )


def list_locations(db: Session, warehouse_id: int) -> List[StorageLocationRead]:
    get_warehouse(db, warehouse_id)
    locations = db.query(StorageLocation).join(WarehouseNode).filter(WarehouseNode.warehouse_id == warehouse_id).all()
    return [_to_loc_read(loc) for loc in locations]


def create_location(db: Session, warehouse_id: int, data: StorageLocationCreate) -> StorageLocationRead:
    node = db.query(WarehouseNode).filter(
        WarehouseNode.id == data.node_id,
        WarehouseNode.warehouse_id == warehouse_id
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Target node not found in this warehouse.", "details": {}})

    # Check location_code uniqueness per warehouse
    dup = db.query(StorageLocation).join(WarehouseNode).filter(
        WarehouseNode.warehouse_id == warehouse_id,
        StorageLocation.location_code == data.location_code
    ).first()
    if dup:
        raise HTTPException(
            status_code=409,
            detail={"code": "DUPLICATE_RESOURCE", "message": f"Storage location code '{data.location_code}' already exists in this warehouse.", "details": {}}
        )

    loc = StorageLocation(
        node_id=data.node_id,
        location_code=data.location_code,
        aisle=data.aisle,
        shelf=data.shelf,
        bin=data.bin,
        max_weight_kg=data.max_weight_kg,
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return _to_loc_read(loc)


def update_location(db: Session, warehouse_id: int, location_id: int, data: StorageLocationUpdate) -> StorageLocationRead:
    loc = db.query(StorageLocation).join(WarehouseNode).filter(
        StorageLocation.id == location_id,
        WarehouseNode.warehouse_id == warehouse_id
    ).first()
    if not loc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Storage location not found.", "details": {}})

    updates = data.model_dump(exclude_unset=True)

    if "location_code" in updates and updates["location_code"] != loc.location_code:
        dup = db.query(StorageLocation).join(WarehouseNode).filter(
            WarehouseNode.warehouse_id == warehouse_id,
            StorageLocation.location_code == updates["location_code"]
        ).first()
        if dup:
            raise HTTPException(status_code=409, detail={"code": "DUPLICATE_RESOURCE", "message": f"Location code '{updates['location_code']}' already exists.", "details": {}})

    for f, v in updates.items():
        setattr(loc, f, v)

    db.commit()
    db.refresh(loc)
    return _to_loc_read(loc)


def delete_location(db: Session, warehouse_id: int, location_id: int) -> None:
    loc = db.query(StorageLocation).join(WarehouseNode).filter(
        StorageLocation.id == location_id,
        WarehouseNode.warehouse_id == warehouse_id
    ).first()
    if not loc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Storage location not found.", "details": {}})

    # Check references in Inventory or PickRouteStep
    inv_count = db.query(Inventory).filter(Inventory.location_id == location_id).count()
    if inv_count > 0:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete location ID {location_id}: referenced by {inv_count} inventory records.", "details": {}}
        )

    step_count = db.query(PickRouteStep).filter(PickRouteStep.location_id == location_id).count()
    if step_count > 0:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete location ID {location_id}: referenced by {step_count} pick route steps.", "details": {}}
        )

    try:
        db.delete(loc)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete storage location: {str(err)}", "details": {}}
        )


# --- Graph & Graph Validation ---
def get_warehouse_graph(db: Session, warehouse_id: int) -> WarehouseGraphRead:
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if wh is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Warehouse not found.", "details": {}})
    nodes = db.query(WarehouseNode).filter(WarehouseNode.warehouse_id == warehouse_id).all()
    edges = db.query(WarehouseEdge).filter(WarehouseEdge.warehouse_id == warehouse_id).all()
    locations = db.query(StorageLocation).join(WarehouseNode).filter(WarehouseNode.warehouse_id == warehouse_id).all()

    return WarehouseGraphRead(
        warehouse_id=warehouse_id,
        nodes=[_to_node_read(n) for n in nodes],
        edges=[_to_edge_read(e) for e in edges],
        locations=[_to_loc_read(loc) for loc in locations],
    )


def validate_warehouse_layout(db: Session, warehouse_id: int) -> WarehouseValidationRead:
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if wh is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Warehouse not found.", "details": {}})

    errors: List[str] = []

    nodes = db.query(WarehouseNode).filter(WarehouseNode.warehouse_id == warehouse_id).all()
    edges = db.query(WarehouseEdge).filter(WarehouseEdge.warehouse_id == warehouse_id).all()
    locations = db.query(StorageLocation).join(WarehouseNode).filter(WarehouseNode.warehouse_id == warehouse_id).all()

    if not nodes:
        errors.append("Warehouse has no nodes configured.")
        return WarehouseValidationRead(valid=False, errors=errors)

    # 1. Exactly one depot node
    depot_nodes = [n for n in nodes if n.is_depot]
    if len(depot_nodes) == 0:
        errors.append("Warehouse must have exactly one depot node configured (currently 0).")
    elif len(depot_nodes) > 1:
        depot_codes = ", ".join(n.node_code for n in depot_nodes)
        errors.append(f"Warehouse must have exactly one depot node configured (currently {len(depot_nodes)}: {depot_codes}).")
    elif depot_nodes[0].is_blocked:
        errors.append(f"Depot node '{depot_nodes[0].node_code}' is marked as blocked.")

    # 2. Check edges for duplicate / non-positive distance
    seen_edges: Set[Tuple[int, int]] = set()
    for e in edges:
        if float(e.distance_meters) <= 0:
            errors.append(f"Edge ID {e.id} between nodes {e.from_node_id} and {e.to_node_id} has invalid non-positive distance {e.distance_meters}m.")
        pair1 = (e.from_node_id, e.to_node_id)
        pair2 = (e.to_node_id, e.from_node_id)
        if pair1 in seen_edges or pair2 in seen_edges:
            errors.append(f"Duplicate edge detected between node {e.from_node_id} and node {e.to_node_id}.")
        seen_edges.add(pair1)
        if e.is_bidirectional:
            seen_edges.add(pair2)

    # 3. Connectivity check from depot node
    if len(depot_nodes) == 1 and not depot_nodes[0].is_blocked:
        depot_id = depot_nodes[0].id
        active_nodes = {n.id for n in nodes if not n.is_blocked}
        
        # Build adjacency over active edges
        adj: Dict[int, Set[int]] = {n_id: set() for n_id in active_nodes}
        for e in edges:
            if not e.is_blocked and e.from_node_id in active_nodes and e.to_node_id in active_nodes:
                adj[e.from_node_id].add(e.to_node_id)
                if e.is_bidirectional:
                    adj[e.to_node_id].add(e.from_node_id)

        # BFS from depot
        visited: Set[int] = set()
        queue = [depot_id]
        if depot_id in active_nodes:
            visited.add(depot_id)

        while queue:
            curr = queue.pop(0)
            for nxt in adj.get(curr, []):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)

        # Check if all active unblocked nodes are reached
        unreachable_nodes = active_nodes - visited
        if unreachable_nodes:
            node_map = {n.id: n.node_code for n in nodes}
            unreachable_codes = ", ".join(node_map[nid] for nid in unreachable_nodes)
            errors.append(f"Warehouse layout graph is disconnected. Unreachable node(s) from depot '{depot_nodes[0].node_code}': {unreachable_codes}.")

        # Check storage locations reachability
        for loc in locations:
            loc_node = next((n for n in nodes if n.id == loc.node_id), None)
            if loc_node and loc_node.is_blocked:
                errors.append(f"Storage location '{loc.location_code}' is placed on a blocked node '{loc_node.node_code}'.")
            elif loc.node_id not in visited:
                errors.append(f"Storage location '{loc.location_code}' (node '{loc_node.node_code if loc_node else loc.node_id}') is unreachable from depot node.")

    valid = (len(errors) == 0)
    return WarehouseValidationRead(valid=valid, errors=errors)


def generate_warehouse_layout(
    db: Session,
    warehouse_id: int,
    aisles: int,
    shelves_per_aisle: int,
    aisle_spacing_m: float,
    shelf_spacing_m: float,
    replace_existing: bool = False
) -> WarehouseGraphRead:
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Warehouse not found.", "details": {}})

    existing_nodes = db.query(WarehouseNode).filter(WarehouseNode.warehouse_id == warehouse_id).all()
    if existing_nodes:
        if not replace_existing:
            raise HTTPException(
                status_code=409,
                detail={"code": "CONFLICT", "message": "Warehouse already has nodes configured and replace_existing is False.", "details": {}}
            )

        # Check references for existing locations/nodes
        node_ids = [n.id for n in existing_nodes]
        locations = db.query(StorageLocation).filter(StorageLocation.node_id.in_(node_ids)).all()
        loc_ids = [loc.id for loc in locations]

        referenced_loc_ids = set()
        if loc_ids:
            inv_locs = db.query(Inventory.location_id).filter(Inventory.location_id.in_(loc_ids)).all()
            for row in inv_locs:
                referenced_loc_ids.add(row[0])
            pick_locs = db.query(PickRouteStep.location_id).filter(PickRouteStep.location_id.in_(loc_ids)).all()
            for row in pick_locs:
                referenced_loc_ids.add(row[0])

        if referenced_loc_ids:
            raise HTTPException(
                status_code=409,
                detail={"code": "CONFLICT", "message": f"Cannot replace layout: {len(referenced_loc_ids)} storage location(s) are referenced by active inventory or pick steps.", "details": {}}
            )

        # Safe to delete layout rows
        db.query(WarehouseEdge).filter(WarehouseEdge.warehouse_id == warehouse_id).delete(synchronize_session=False)
        db.query(StorageLocation).filter(StorageLocation.node_id.in_(node_ids)).delete(synchronize_session=False)
        db.query(WarehouseNode).filter(WarehouseNode.warehouse_id == warehouse_id).delete(synchronize_session=False)
        db.flush()

    # Generate in ONE transaction
    # 1. Depot node at (0.0, 0.0)
    depot_node = WarehouseNode(
        warehouse_id=warehouse_id,
        node_code="N-DEPOT",
        x_coord=0.0,
        y_coord=0.0,
        z_coord=0.0,
        is_depot=True,
        is_blocked=False
    )
    db.add(depot_node)
    db.flush()

    def add_edge_helper(n1: WarehouseNode, n2: WarehouseNode):
        dx = float(n1.x_coord) - float(n2.x_coord)
        dy = float(n1.y_coord) - float(n2.y_coord)
        dz = float(n1.z_coord) - float(n2.z_coord)
        dist = round(math.sqrt(dx * dx + dy * dy + dz * dz), 2)
        if dist <= 0:
            dist = 1.0
        edge = WarehouseEdge(
            warehouse_id=warehouse_id,
            from_node_id=n1.id,
            to_node_id=n2.id,
            distance_meters=dist,
            is_bidirectional=True,
            is_blocked=False
        )
        db.add(edge)

    prev_junction = depot_node
    junction_nodes = []
    far_end_nodes = []

    for a in range(1, aisles + 1):
        x = round(a * aisle_spacing_m, 2)
        # Main corridor junction node at (x, 0.0)
        j_node = WarehouseNode(
            warehouse_id=warehouse_id,
            node_code=f"N-J-A{a}",
            x_coord=x,
            y_coord=0.0,
            z_coord=0.0,
            is_depot=False,
            is_blocked=False
        )
        db.add(j_node)
        db.flush()
        junction_nodes.append(j_node)

        # Edge from previous corridor junction to current junction
        add_edge_helper(prev_junction, j_node)
        prev_junction = j_node

        # Chain of shelf nodes along aisle Y axis
        prev_shelf_node = j_node
        for s in range(1, shelves_per_aisle + 1):
            y = round(s * shelf_spacing_m, 2)
            shelf_node = WarehouseNode(
                warehouse_id=warehouse_id,
                node_code=f"N-A{a}-S{s:02d}",
                x_coord=x,
                y_coord=y,
                z_coord=0.0,
                is_depot=False,
                is_blocked=False
            )
            db.add(shelf_node)
            db.flush()

            # Edge along aisle
            add_edge_helper(prev_shelf_node, shelf_node)

            # Storage location on shelf node
            loc_code = f"A{a}-S{s:02d}"
            loc = StorageLocation(
                node_id=shelf_node.id,
                location_code=loc_code,
                aisle=f"A{a}",
                shelf=f"S{s:02d}",
                bin="B1",
                max_weight_kg=100.0
            )
            db.add(loc)

            prev_shelf_node = shelf_node

        far_end_nodes.append(prev_shelf_node)

    # Cross-aisle edges at the far end to create loops
    for i in range(len(far_end_nodes) - 1):
        add_edge_helper(far_end_nodes[i], far_end_nodes[i+1])

    db.commit()
    return get_warehouse_graph(db, warehouse_id)


def _sanitize_store_code(name: str) -> str:
    import re
    s = name.upper().strip()
    s = re.sub(r'[^A-Z0-9]+', '-', s)
    s = s.strip('-')
    return s or "STORE"


def import_stores_csv(
    db: Session,
    csv_content: str,
    generate_layout: bool = True,
    aisles: int = 4,
    shelves_per_aisle: int = 5,
    aisle_spacing_m: float = 3.0,
    shelf_spacing_m: float = 2.0,
) -> dict:
    """
    Import Zepto store locations from CSV and upsert warehouses.
    Optionally generate warehouse layout for each store.
    """
    import csv
    import io

    created = 0
    updated = 0
    skipped = 0
    errors = []

    reader = csv.DictReader(io.StringIO(csv_content))
    for row_idx, row in enumerate(reader, start=2):
        name = (row.get("name") or "").strip()
        external_id = (row.get("id") or "").strip()
        city = (row.get("city") or "").strip()
        state = (row.get("state") or "").strip()
        lat_str = row.get("lat") or row.get("latitude")
        lng_str = row.get("lng") or row.get("longitude")

        if not name:
            errors.append({"row": row_idx, "message": "Missing store name."})
            skipped += 1
            continue

        try:
            latitude = float(lat_str)
            longitude = float(lng_str)
        except (ValueError, TypeError):
            errors.append({"row": row_idx, "message": f"Invalid numeric coordinates: lat={lat_str}, lng={lng_str}"})
            skipped += 1
            continue

        # Coordinate validation: lat between -90 and 90, lng between -180 and 180, and not identical lat/lng
        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0) or (abs(latitude - longitude) < 0.0001 and latitude != 0):
            errors.append({"row": row_idx, "message": f"Out-of-range or invalid coordinates: lat={latitude}, lng={longitude}"})
            skipped += 1
            continue

        code = _sanitize_store_code(name)
        address = f"{city}, {state}".strip(", ")

        # Look up existing warehouse by code or external_id
        wh = None
        if code:
            wh = db.query(Warehouse).filter(Warehouse.code == code).first()
        if not wh and external_id:
            wh = db.query(Warehouse).filter(Warehouse.external_id == external_id).first()

        is_update = False
        if wh:
            wh.code = code
            wh.name = name
            wh.latitude = latitude
            wh.longitude = longitude
            wh.address = address
            if external_id:
                wh.external_id = external_id
            is_update = True
        else:
            wh = Warehouse(
                code=code,
                name=name,
                latitude=latitude,
                longitude=longitude,
                address=address,
                external_id=external_id or None,
                status="active",
            )
            db.add(wh)

        try:
            db.flush()
            if is_update:
                updated += 1
            else:
                created += 1

            if generate_layout:
                try:
                    generate_warehouse_layout(
                        db,
                        warehouse_id=wh.id,
                        aisles=aisles,
                        shelves_per_aisle=shelves_per_aisle,
                        aisle_spacing_m=aisle_spacing_m,
                        shelf_spacing_m=shelf_spacing_m,
                        replace_existing=True,
                    )
                except Exception:
                    pass
            db.commit()
        except Exception as e:
            db.rollback()
            errors.append({"row": row_idx, "message": f"Database error: {str(e)}"})
            skipped += 1

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


