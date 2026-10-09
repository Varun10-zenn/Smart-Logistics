"""Integration tests for Zepto store locations import, picker-store link, wildcard inventory import, and batching."""
import os
import pytest
from fastapi.testclient import TestClient
from backend.app.models.warehouse import Warehouse, StorageLocation, WarehouseNode, Product, Inventory
from backend.app.models.user import User, Role
from backend.app.models.order import Order
from backend.app.models.batch import Batch, PickRouteStep


def test_import_zepto_stores_csv(client, admin_headers, db_session):
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "zepto_stores_chennai_vellore.csv")
    assert os.path.exists(csv_path), "Dataset CSV file must exist"

    with open(csv_path, "rb") as f:
        res = client.post(
            "/api/v1/warehouses/import?generate_layout=true&aisles=2&shelves_per_aisle=3",
            files={"file": ("zepto_stores.csv", f, "text/csv")},
            headers=admin_headers,
        )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["created"] > 0

    # Check Adyar warehouse
    adyar = db_session.query(Warehouse).filter(Warehouse.code == "CHN-ADYAR").first()
    assert adyar is not None
    assert adyar.external_id is not None
    assert float(adyar.latitude) == pytest.approx(13.001967)

    # Check generated layout
    nodes_count = db_session.query(WarehouseNode).filter(WarehouseNode.warehouse_id == adyar.id).count()
    assert nodes_count > 0
    locs_count = db_session.query(StorageLocation).join(WarehouseNode).filter(WarehouseNode.warehouse_id == adyar.id).count()
    assert locs_count > 0


def test_wildcard_inventory_csv_import(client, admin_headers, db_session):
    # Ensure warehouse and layout exist
    wh = Warehouse(code="WH-TEST-IMP", name="Test Import WH", latitude=13.0, longitude=80.0, status="active")
    db_session.add(wh)
    db_session.commit()

    node = WarehouseNode(warehouse_id=wh.id, node_code="N-TEST-1", x_coord=0.0, y_coord=0.0)
    db_session.add(node)
    db_session.commit()

    loc = StorageLocation(node_id=node.id, location_code="A1-S01", aisle="A1", shelf="S1", bin="B1")
    db_session.add(loc)
    p1 = Product(sku="SKU-ZEP-001", name="Amul Milk 500ml", category="Dairy", unit_weight_kg=0.5, unit_volume_cbm=0.001, price=30.0)
    db_session.add(p1)
    db_session.commit()

    csv_content = (
        "warehouse_code,location_code,sku,quantity,reorder_threshold\n"
        "*,A1-S01,SKU-ZEP-001,50,10\n"
    )

    res = client.post(
        "/api/v1/inventory/import",
        files={"file": ("inventory.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=admin_headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["created"] > 0


def test_picker_operator_creation_validation(client, admin_headers, db_session):
    wh = db_session.query(Warehouse).first()

    # Missing warehouse_id should fail with 422
    payload_invalid = {
        "username": "op_invalid",
        "email": "op_invalid@test.com",
        "password": "password123",
        "full_name": "Invalid Operator",
        "role_code": "warehouse_operator"
    }
    res = client.post("/api/v1/users", json=payload_invalid, headers=admin_headers)
    assert res.status_code == 422, res.text

    # Valid payload
    payload_valid = {
        "username": "op_valid",
        "email": "op_valid@test.com",
        "password": "password123",
        "full_name": "Valid Operator",
        "role_code": "warehouse_operator",
        "warehouse_id": wh.id
    }
    res = client.post("/api/v1/users", json=payload_valid, headers=admin_headers)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["warehouse_id"] == wh.id


def test_picker_batch_scoping_authorization(client, db_session):
    wh1 = db_session.query(Warehouse).first()
    wh2 = Warehouse(code="WH-OTHER-01", name="Other Store", latitude=13.1, longitude=80.1, status="active")
    db_session.add(wh2)
    db_session.commit()

    # Create batch for WH2
    batch2 = Batch(batch_code="B-WH2-001", warehouse_id=wh2.id, status="pending")
    db_session.add(batch2)
    db_session.commit()

    # Create operator assigned to WH1
    from backend.app.core.security import hash_password, create_access_token
    role_op = db_session.query(Role).filter(Role.code == "warehouse_operator").first()
    op_wh1 = User(
        email="op1@test.com",
        full_name="Operator 1",
        password_hash=hash_password("test1234"),
        role_id=role_op.id,
        warehouse_id=wh1.id,
        is_active=True
    )
    db_session.add(op_wh1)
    db_session.commit()

    token = create_access_token(data={"sub": str(op_wh1.id), "role": "warehouse_operator"})
    op_headers = {"Authorization": f"Bearer {token}"}

    # Operator listing batches should only see WH1 batches
    res = client.get("/api/v1/batches", headers=op_headers)
    assert res.status_code == 200
    for b in res.json()["items"]:
        assert b["warehouse_id"] == wh1.id

    # Operator trying to view WH2 batch detail gets 403
    res_batch = client.get(f"/api/v1/batches/{batch2.id}", headers=op_headers)
    assert res_batch.status_code == 403


def test_customer_nearest_store_selection(client, admin_headers, db_session):
    adyar = Warehouse(code="CHN-ADYAR-TEST", name="CHN-ADYAR", latitude=13.001967, longitude=80.256008, status="active")
    db_session.add(adyar)
    db_session.commit()

    node = WarehouseNode(warehouse_id=adyar.id, node_code="N-ADYAR-1", x_coord=0.0, y_coord=0.0)
    db_session.add(node)
    db_session.commit()

    loc = StorageLocation(node_id=node.id, location_code="A1-S01", aisle="A1", shelf="S1", bin="B1")
    prod = Product(sku="SKU-ZEP-002", name="Milk", category="Dairy", unit_weight_kg=0.5, unit_volume_cbm=0.001, price=30.0)
    db_session.add(loc)
    db_session.add(prod)
    db_session.commit()

    inv = Inventory(warehouse_id=adyar.id, location_id=loc.id, product_id=prod.id, quantity=100, reorder_threshold=10)
    db_session.add(inv)
    db_session.commit()

    # Customer at Adyar coords (13.002, 80.256)
    res = client.get("/api/v1/shop/products?lat=13.002&lon=80.256", headers=admin_headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["warehouse_name"] is not None
