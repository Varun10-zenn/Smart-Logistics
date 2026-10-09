"""
Service-level integration tests for WarehouseOptimizationService.
Verifies end-to-end transactional execution against PostgreSQL / DB models.
"""
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models.warehouse import Warehouse, WarehouseZone, WarehouseNode, WarehouseEdge, StorageLocation, Product, Inventory
from backend.app.models.order import Order, OrderItem
from backend.app.models.batch import Batch, BatchOrder, PickRoute, PickRouteStep
from backend.app.models.intelligence import AIRecommendation
from backend.app.services.warehouse_optimization_service import WarehouseOptimizationService


@pytest.fixture
def test_db_session():
    """Provides isolated in-memory DB session for service tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    engine.dispose()



def setup_test_warehouse_data(db):
    """Populates valid warehouse, graph, product, inventory, and pending order records."""
    # 1. Warehouse
    wh = Warehouse(code="WH-TEST-01", name="Test Warehouse", latitude=13.0, longitude=80.0)
    db.add(wh)
    db.commit()

    # 2. Nodes & Edges
    n1 = WarehouseNode(warehouse_id=wh.id, node_code="N1", x_coord=0.0, y_coord=0.0, is_depot=True)
    n2 = WarehouseNode(warehouse_id=wh.id, node_code="N2", x_coord=5.0, y_coord=0.0)
    n3 = WarehouseNode(warehouse_id=wh.id, node_code="N3", x_coord=5.0, y_coord=5.0)
    db.add_all([n1, n2, n3])
    db.commit()

    e1 = WarehouseEdge(warehouse_id=wh.id, from_node_id=n1.id, to_node_id=n2.id, distance_meters=5.0, is_bidirectional=True)
    e2 = WarehouseEdge(warehouse_id=wh.id, from_node_id=n2.id, to_node_id=n3.id, distance_meters=5.0, is_bidirectional=True)
    db.add_all([e1, e2])
    db.commit()

    # 3. Storage Location & Product & Inventory
    loc2 = StorageLocation(node_id=n2.id, location_code="LOC-A2", aisle="A1", shelf="S1", bin="B1")
    loc3 = StorageLocation(node_id=n3.id, location_code="LOC-A3", aisle="A1", shelf="S1", bin="B2")
    db.add_all([loc2, loc3])
    db.commit()

    p1 = Product(sku="SKU-P1", name="Product 1", category="Test", unit_weight_kg=2.0, unit_volume_cbm=0.01, price=10.0)
    p2 = Product(sku="SKU-P2", name="Product 2", category="Test", unit_weight_kg=3.0, unit_volume_cbm=0.01, price=20.0)
    db.add_all([p1, p2])
    db.commit()

    inv1 = Inventory(warehouse_id=wh.id, location_id=loc2.id, product_id=p1.id, quantity=100)
    inv2 = Inventory(warehouse_id=wh.id, location_id=loc3.id, product_id=p2.id, quantity=100)
    db.add_all([inv1, inv2])
    db.commit()

    # 4. Pending Orders
    now = datetime.now(timezone.utc)
    o1 = Order(order_number="ORD-OPT-01", warehouse_id=wh.id, customer_name="Cust 1", destination_address="Addr 1", destination_lat=13.0, destination_lon=80.0, priority=1, status="pending", created_at=now, promised_at=now + timedelta(hours=2))
    o2 = Order(order_number="ORD-OPT-02", warehouse_id=wh.id, customer_name="Cust 2", destination_address="Addr 2", destination_lat=13.0, destination_lon=80.0, priority=3, status="pending", created_at=now, promised_at=now + timedelta(hours=1)) # URGENT
    db.add_all([o1, o2])
    db.commit()

    item1 = OrderItem(order_id=o1.id, product_id=p1.id, quantity=1, unit_price=10.0)
    item2 = OrderItem(order_id=o2.id, product_id=p2.id, quantity=1, unit_price=20.0)
    db.add_all([item1, item2])
    db.commit()

    return wh.id


def test_successful_warehouse_optimization(test_db_session):
    wh_id = setup_test_warehouse_data(test_db_session)

    res = WarehouseOptimizationService.optimize_warehouse(test_db_session, warehouse_id=wh_id)

    assert res.success is True
    assert res.warehouse_id == wh_id
    assert res.total_pending_orders == 2
    assert res.eligible_orders_count == 2
    assert res.generated_batches_count == 1
    assert len(res.batches) == 1
    assert res.batches[0].steps_count == 2
    assert res.recommendation_id is not None

    # Verify orders updated to 'batched' in DB
    orders = test_db_session.query(Order).filter(Order.warehouse_id == wh_id).all()
    for o in orders:
        assert o.status == "batched"

    # Verify Batch, PickRoute, and AIRecommendation exist in DB
    batch_db = test_db_session.query(Batch).filter(Batch.id == res.batches[0].batch_id).first()
    assert batch_db is not None
    assert batch_db.status == "created"

    rec_db = test_db_session.query(AIRecommendation).filter(AIRecommendation.id == res.recommendation_id).first()
    assert rec_db is not None
    assert rec_db.agent_name == "warehouse_agent"


def test_invalid_warehouse_id(test_db_session):
    res = WarehouseOptimizationService.optimize_warehouse(test_db_session, warehouse_id=99999)
    assert res.success is False
    assert "not found" in res.failure_reason.lower()


def test_empty_pending_orders(test_db_session):
    wh = Warehouse(code="WH-EMPTY", name="Empty Warehouse", latitude=13.0, longitude=80.0)
    test_db_session.add(wh)
    test_db_session.commit()

    n1 = WarehouseNode(warehouse_id=wh.id, node_code="N1", x_coord=0.0, y_coord=0.0, is_depot=True)
    test_db_session.add(n1)
    test_db_session.commit()

    res = WarehouseOptimizationService.optimize_warehouse(test_db_session, warehouse_id=wh.id)
    assert res.success is True
    assert res.total_pending_orders == 0
    assert res.generated_batches_count == 0


def test_repeated_optimization_is_idempotent(test_db_session):
    wh_id = setup_test_warehouse_data(test_db_session)

    res1 = WarehouseOptimizationService.optimize_warehouse(test_db_session, warehouse_id=wh_id)
    assert res1.generated_batches_count == 1

    # Second run: orders are now status='batched', so pending orders = 0
    res2 = WarehouseOptimizationService.optimize_warehouse(test_db_session, warehouse_id=wh_id)
    assert res2.total_pending_orders == 0
    assert res2.generated_batches_count == 0
