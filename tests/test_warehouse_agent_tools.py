"""
Unit tests for Phase 3.5 Controlled Tool Interface Layer.
Tests tool registration, schema validation, role authorization, invalid tool rejection, and deterministic outputs.
"""
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import sessionmaker

from backend.app.models.warehouse import Warehouse, WarehouseNode, WarehouseEdge, StorageLocation, Product, Inventory
from backend.app.models.order import Order, OrderItem
from backend.app.services.warehouse_agent_tools import (
    dispatch_warehouse_tool, WAREHOUSE_TOOL_REGISTRY
)


@pytest.fixture
def tool_db_session():
    """Provides isolated DB session for tool tests."""
    from sqlalchemy import create_engine
    from backend.app.core.database import Base
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    engine.dispose()



def setup_tool_warehouse(db):
    """Sets up test warehouse data."""
    wh = Warehouse(code="WH-TOOL-01", name="Tool Test Warehouse", latitude=13.0, longitude=80.0)
    db.add(wh)
    db.commit()

    n1 = WarehouseNode(warehouse_id=wh.id, node_code="N1", x_coord=0.0, y_coord=0.0)
    n2 = WarehouseNode(warehouse_id=wh.id, node_code="N2", x_coord=5.0, y_coord=0.0)
    db.add_all([n1, n2])
    db.commit()

    e1 = WarehouseEdge(warehouse_id=wh.id, from_node_id=n1.id, to_node_id=n2.id, distance_meters=5.0, is_bidirectional=True)
    db.add(e1)
    db.commit()

    loc1 = StorageLocation(node_id=n1.id, location_code="LOC-T1", aisle="A1", shelf="S1", bin="B1")
    db.add(loc1)
    db.commit()

    p1 = Product(sku="SKU-T1", name="Tool Product 1", category="Test", unit_weight_kg=2.0, unit_volume_cbm=0.01, price=10.0)
    db.add(p1)
    db.commit()

    inv1 = Inventory(warehouse_id=wh.id, location_id=loc1.id, product_id=p1.id, quantity=50)
    db.add(inv1)
    db.commit()

    now = datetime.now(timezone.utc)
    o1 = Order(order_number="ORD-TOOL-01", warehouse_id=wh.id, customer_name="Tool Cust", destination_address="Addr", destination_lat=13.0, destination_lon=80.0, priority=2, status="pending", created_at=now, promised_at=now + timedelta(hours=2))
    db.add(o1)
    db.commit()

    item1 = OrderItem(order_id=o1.id, product_id=p1.id, quantity=2, unit_price=10.0)
    db.add(item1)
    db.commit()

    return wh.id, n1.id, n2.id, loc1.id, p1.id, o1.id


def test_tool_registry_contains_exactly_9_approved_tools():
    assert len(WAREHOUSE_TOOL_REGISTRY) == 9
    expected = {
        "get_warehouse_graph", "get_eligible_orders", "get_inventory_state",
        "calculate_shortest_path", "generate_order_batches", "generate_pick_route",
        "validate_batch", "validate_pick_route", "calculate_warehouse_metrics"
    }
    assert set(WAREHOUSE_TOOL_REGISTRY.keys()) == expected


def test_dispatch_valid_tool(tool_db_session):
    wh_id, n1_id, n2_id, loc1_id, p1_id, o1_id = setup_tool_warehouse(tool_db_session)

    res = dispatch_warehouse_tool(
        db=tool_db_session,
        user_role="warehouse_operator",
        tool_name="get_warehouse_graph",
        payload={"warehouse_id": wh_id}
    )

    assert res["success"] is True
    assert res["warehouse_id"] == wh_id
    assert res["total_nodes"] == 2
    assert res["total_edges"] == 1


def test_unauthorized_role_rejected(tool_db_session):
    wh_id, _, _, _, _, _ = setup_tool_warehouse(tool_db_session)

    with pytest.raises(PermissionError) as exc_info:
        dispatch_warehouse_tool(
            db=tool_db_session,
            user_role="driver",  # Driver is not allowed warehouse tools
            tool_name="get_warehouse_graph",
            payload={"warehouse_id": wh_id}
        )
    assert "Unauthorized: Role 'driver'" in str(exc_info.value)


def test_invalid_tool_name_rejected(tool_db_session):
    with pytest.raises(ValueError) as exc_info:
        dispatch_warehouse_tool(
            db=tool_db_session,
            user_role="admin",
            tool_name="DROP_TABLE_USERS",  # Malicious/invalid tool name
            payload={}
        )
    assert "Invalid tool 'DROP_TABLE_USERS'" in str(exc_info.value)


def test_invalid_tool_arguments(tool_db_session):
    # Missing required 'warehouse_id'
    res = dispatch_warehouse_tool(
        db=tool_db_session,
        user_role="admin",
        tool_name="get_warehouse_graph",
        payload={"warehouse_id": -5}  # Violation of Field gt=0
    )
    assert res["success"] is False


def test_tool_calculate_shortest_path(tool_db_session):
    wh_id, n1_id, n2_id, _, _, _ = setup_tool_warehouse(tool_db_session)

    res = dispatch_warehouse_tool(
        db=tool_db_session,
        user_role="admin",
        tool_name="calculate_shortest_path",
        payload={"warehouse_id": wh_id, "start_node_id": n1_id, "destination_node_id": n2_id, "algorithm": "a_star"}
    )

    assert res["success"] is True
    assert res["path"] == [n1_id, n2_id]
    assert res["total_distance_meters"] == 5.0


def test_tool_validate_batch(tool_db_session):
    wh_id, _, _, _, _, o1_id = setup_tool_warehouse(tool_db_session)

    res = dispatch_warehouse_tool(
        db=tool_db_session,
        user_role="warehouse_operator",
        tool_name="validate_batch",
        payload={"warehouse_id": wh_id, "order_ids": [o1_id], "max_orders": 5, "max_weight_kg": 25.0, "max_volume_cbm": 0.12}
    )

    assert res["is_valid"] is True
    assert res["total_orders"] == 1
    assert res["total_weight_kg"] == 4.0  # 2 items * 2.0kg = 4.0kg


def test_tool_determinism(tool_db_session):
    wh_id, _, _, _, _, _ = setup_tool_warehouse(tool_db_session)

    res1 = dispatch_warehouse_tool(tool_db_session, "admin", "calculate_warehouse_metrics", {"warehouse_id": wh_id})
    res2 = dispatch_warehouse_tool(tool_db_session, "admin", "calculate_warehouse_metrics", {"warehouse_id": wh_id})

    assert res1 == res2
