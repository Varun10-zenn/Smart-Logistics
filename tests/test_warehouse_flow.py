import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer dev-bypass-token"}


def test_user_driven_warehouse_flow_and_optimization():
    # 1. Create Warehouse
    res = client.post("/api/v1/warehouses", headers=AUTH_HEADERS, json={
        "code": "WH-UD-DARKSTORE",
        "name": "User Driven Darkstore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "address": "123 Test Boulevard"
    })
    assert res.status_code == 201
    wh = res.json()
    wh_id = wh["id"]

    # 2. Add Depot Node & Standard Node
    res = client.post(f"/api/v1/warehouses/{wh_id}/nodes", headers=AUTH_HEADERS, json={
        "node_code": "N-DEPOT-01",
        "x_coord": 0.0,
        "y_coord": 0.0,
        "is_depot": True
    })
    assert res.status_code == 201
    depot_node = res.json()
    assert depot_node["is_depot"] is True

    res = client.post(f"/api/v1/warehouses/{wh_id}/nodes", headers=AUTH_HEADERS, json={
        "node_code": "N-AISLE-01",
        "x_coord": 10.0,
        "y_coord": 0.0,
        "is_depot": False
    })
    assert res.status_code == 201
    aisle_node = res.json()

    # 3. Add Edge connecting Depot to Aisle Node
    res = client.post(f"/api/v1/warehouses/{wh_id}/edges", headers=AUTH_HEADERS, json={
        "from_node_id": depot_node["id"],
        "to_node_id": aisle_node["id"],
        "distance_meters": 10.0,
        "is_bidirectional": True
    })
    assert res.status_code == 201

    # 4. Add Storage Location on Aisle Node
    res = client.post(f"/api/v1/warehouses/{wh_id}/locations", headers=AUTH_HEADERS, json={
        "node_id": aisle_node["id"],
        "location_code": "LOC-A1-S1-B1",
        "aisle": "A1",
        "shelf": "S1",
        "bin": "B1",
        "max_weight_kg": 100.0
    })
    assert res.status_code == 201
    loc = res.json()

    # 5. Create Product & Inventory
    res = client.post("/api/v1/products", headers=AUTH_HEADERS, json={
        "sku": "PROD-WIDGET-01",
        "name": "Smart Widget",
        "category": "Electronics",
        "unit_weight_kg": 1.5,
        "unit_volume_cbm": 0.002,
        "price": 29.99
    })
    assert res.status_code == 201
    prod = res.json()

    res = client.post("/api/v1/inventory", headers=AUTH_HEADERS, json={
        "warehouse_id": wh_id,
        "location_id": loc["id"],
        "product_id": prod["id"],
        "quantity": 50,
        "reorder_threshold": 10
    })
    assert res.status_code == 201

    # 6. Validate Layout
    res = client.get(f"/api/v1/warehouses/{wh_id}/validate", headers=AUTH_HEADERS)
    assert res.status_code == 200
    val_data = res.json()
    assert val_data["valid"] is True
    assert len(val_data["errors"]) == 0

    # 7. Create Pending Order
    res = client.post("/api/v1/orders", headers=AUTH_HEADERS, json={
        "order_number": "ORD-UD-01",
        "warehouse_id": wh_id,
        "customer_name": "Test Customer",
        "destination_address": "456 Tech Park",
        "customer_lat": 12.9800,
        "customer_lon": 77.6000,
        "priority": "normal",
        "promised_at": "2026-10-05T12:00:00Z",
        "items": [
            {"product_id": prod["id"], "quantity": 2}
        ]
    })
    assert res.status_code == 201

    # 8. Run Optimization
    res = client.post(f"/api/v1/warehouses/{wh_id}/optimize", headers=AUTH_HEADERS, json={
        "max_orders_per_batch": 5,
        "max_weight_kg": 50.0,
        "max_volume_cbm": 2.0,
        "use_2opt_routing": True
    })
    assert res.status_code == 200
    opt_res = res.json()
    assert len(opt_res["batches"]) == 1
    batch_id = opt_res["batches"][0]["batch_id"]

    # Verify pick route created
    route_res = client.get(f"/api/v1/batches/{batch_id}/pick-route", headers=AUTH_HEADERS)
    assert route_res.status_code == 200
    assert len(route_res.json()["steps"]) > 0


def test_disconnected_graph_validation_error():
    # Create Warehouse
    res = client.post("/api/v1/warehouses", headers=AUTH_HEADERS, json={
        "code": "WH-DISCONN-01",
        "name": "Disconnected Darkstore",
        "latitude": 13.0000,
        "longitude": 77.5000
    })
    assert res.status_code == 201
    wh_id = res.json()["id"]

    # Add Depot Node
    client.post(f"/api/v1/warehouses/{wh_id}/nodes", headers=AUTH_HEADERS, json={
        "node_code": "N-DEPOT-DISC",
        "x_coord": 0.0,
        "y_coord": 0.0,
        "is_depot": True
    })

    # Add Isolated Node (No edge connecting it to depot)
    res = client.post(f"/api/v1/warehouses/{wh_id}/nodes", headers=AUTH_HEADERS, json={
        "node_code": "N-ISOLATED-01",
        "x_coord": 50.0,
        "y_coord": 50.0,
        "is_depot": False
    })

    # Validate layout graph -> expect valid = False
    res = client.get(f"/api/v1/warehouses/{wh_id}/validate", headers=AUTH_HEADERS)
    assert res.status_code == 200
    val = res.json()
    assert val["valid"] is False
    assert any("disconnected" in err.lower() for err in val["errors"])

    # Run optimization -> expect HTTP 422
    res = client.post(f"/api/v1/warehouses/{wh_id}/optimize", headers=AUTH_HEADERS)
    assert res.status_code == 422


def test_no_depot_node_validation_error():
    res = client.post("/api/v1/warehouses", headers=AUTH_HEADERS, json={
        "code": "WH-NODEPOT-01",
        "name": "No Depot Darkstore",
        "latitude": 13.0000,
        "longitude": 77.5000
    })
    assert res.status_code == 201
    wh_id = res.json()["id"]

    # Add Node without depot setting
    client.post(f"/api/v1/warehouses/{wh_id}/nodes", headers=AUTH_HEADERS, json={
        "node_code": "N-STANDALONE-01",
        "x_coord": 5.0,
        "y_coord": 5.0,
        "is_depot": False
    })

    res = client.get(f"/api/v1/warehouses/{wh_id}/validate", headers=AUTH_HEADERS)
    assert res.json()["valid"] is False

    res = client.post(f"/api/v1/warehouses/{wh_id}/optimize", headers=AUTH_HEADERS)
    assert res.status_code == 422


def test_referenced_delete_returns_409():
    res = client.post("/api/v1/warehouses", headers=AUTH_HEADERS, json={
        "code": "WH-DEL-CONFLICT-01",
        "name": "Conflict Darkstore",
        "latitude": 12.0000,
        "longitude": 77.0000
    })
    assert res.status_code == 201
    wh_id = res.json()["id"]

    # Add node
    node_id = client.post(f"/api/v1/warehouses/{wh_id}/nodes", headers=AUTH_HEADERS, json={
        "node_code": "N-CONF-1", "x_coord": 0.0, "y_coord": 0.0
    }).json()["id"]

    # Add location on node
    loc_id = client.post(f"/api/v1/warehouses/{wh_id}/locations", headers=AUTH_HEADERS, json={
        "node_id": node_id, "location_code": "LOC-CONF-1", "aisle": "A", "shelf": "1", "bin": "1"
    }).json()["id"]

    # Delete node referencing location should fail with 409 Conflict
    res = client.delete(f"/api/v1/warehouses/{wh_id}/nodes/{node_id}", headers=AUTH_HEADERS)
    assert res.status_code == 409
    assert "location" in str(res.json()).lower()

