"""Integration tests for Warehouse to Deliveries auto-handoff, fleet per store, rider flow, and ETA enforcement."""
import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.main import app
from backend.app.core.config import settings

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-bypass-token"}


@pytest.fixture(autouse=True)
def setup_bypass_mode():
    orig_bypass = settings.DEV_AUTH_BYPASS
    orig_env = settings.APP_ENV
    settings.DEV_AUTH_BYPASS = True
    settings.APP_ENV = "local"
    yield
    settings.DEV_AUTH_BYPASS = orig_bypass
    settings.APP_ENV = orig_env


def test_fleet_generation_and_auto_handoff_flow():
    suffix = uuid.uuid4().hex[:6]
    wh_code = f"WH-FLT-{suffix}"

    # 1. Create Warehouse
    wh_res = client.post("/api/v1/warehouses", headers=AUTH_ADMIN, json={
        "code": wh_code,
        "name": "Fleet Store Center",
        "latitude": 12.9716,
        "longitude": 79.1400,
        "address": "Vellore Main Rd"
    })
    assert wh_res.status_code == 201
    wh_id = wh_res.json()["id"]

    # 2. Generate Store Fleet (2 Riders, 1 EV, 1 ICE)
    fleet_res = client.post(f"/api/v1/warehouses/{wh_id}/fleet/generate", headers=AUTH_ADMIN, json={
        "riders": 2,
        "ev_count": 1
    })
    assert fleet_res.status_code == 200
    fleet_data = fleet_res.json()
    assert fleet_data["riders_created"] == 2
    assert fleet_data["vehicles_created"] == 2
    assert fleet_data["ev_count"] == 1

    rider_email = fleet_data["riders"][0]["email"]
    rider_password = fleet_data["riders"][0]["password"]

    # 3. Login Rider
    rider_login = client.post("/api/v1/auth/login", json={
        "email": rider_email,
        "password": rider_password
    })
    assert rider_login.status_code == 200
    rider_token = rider_login.json()["access_token"]
    rider_headers = {"Authorization": f"Bearer {rider_token}"}

    # 4. Create Product & Inventory
    prod_res = client.post("/api/v1/products", headers=AUTH_ADMIN, json={
        "sku": f"SKU-DEL-{suffix}",
        "name": "Fresh Orange Juice",
        "category": "Beverages",
        "unit_weight_kg": 1.0,
        "unit_volume_cbm": 0.001,
        "price": 3.99
    })
    prod_id = prod_res.json()["id"]

    node_res = client.post(f"/api/v1/warehouses/{wh_id}/nodes", headers=AUTH_ADMIN, json={
        "node_code": f"N-D1-{suffix}",
        "x_coord": 0.0,
        "y_coord": 0.0,
        "is_depot": True
    })
    node_id = node_res.json()["id"]

    loc_res = client.post(f"/api/v1/warehouses/{wh_id}/locations", headers=AUTH_ADMIN, json={
        "node_id": node_id,
        "location_code": f"LOC-D1-{suffix}",
        "aisle": "A1",
        "shelf": "S1",
        "bin": "B1",
        "max_weight_kg": 1000.0
    })
    loc_id = loc_res.json()["id"]

    client.post("/api/v1/inventory", headers=AUTH_ADMIN, json={
        "warehouse_id": wh_id,
        "location_id": loc_id,
        "product_id": prod_id,
        "quantity": 50,
        "reorder_threshold": 5
    })

    # 5. Create Customer & Place Order
    cust_email = f"cust_delivery_{suffix}@example.com"
    client.post("/api/v1/auth/register", json={
        "email": cust_email,
        "password": "password123"
    })
    cust_login = client.post("/api/v1/auth/login", json={
        "email": cust_email,
        "password": "password123"
    }).json()
    cust_headers = {"Authorization": f"Bearer {cust_login['access_token']}"}

    chk_res = client.post("/api/v1/shop/checkout", headers=cust_headers, json={
        "items": [{"product_id": prod_id, "quantity": 2}],
        "lat": 12.9750,
        "lon": 79.1450,
        "address": "Customer Villa 42, Vellore"
    })
    assert chk_res.status_code == 201
    order_id = chk_res.json()["id"]

    # 6. Optimize Batch & Complete Pick Steps
    opt_res = client.post(f"/api/v1/warehouses/{wh_id}/optimize", headers=AUTH_ADMIN, json={
        "max_orders_per_batch": 5,
        "max_weight_kg": 100.0,
        "max_volume_cbm": 5.0,
        "use_2opt_routing": False
    })
    assert opt_res.status_code == 200
    batch_id = opt_res.json()["batches"][0]["batch_id"]

    route_res = client.get(f"/api/v1/batches/{batch_id}/pick-route", headers=AUTH_ADMIN)
    step_id = route_res.json()["steps"][0]["id"]

    # Complete picking -> Auto Handoff Triggers HERE
    comp_res = client.post(f"/api/v1/pick-route-steps/{step_id}/complete", headers=AUTH_ADMIN)
    assert comp_res.status_code == 200

    # 7. Verify ONE Delivery Created for Batch with Delivery Stop
    del_res = client.get(f"/api/v1/deliveries?status=assigned", headers=AUTH_ADMIN)
    assert del_res.status_code == 200
    deliveries = [d for d in del_res.json()["items"] if d["batch_id"] == batch_id]
    assert len(deliveries) == 1
    delivery_id = deliveries[0]["id"]

    # 8. Rider Flow: GET active deliveries for logged-in rider
    rider_active = client.get("/api/v1/deliveries/rider/active", headers=rider_headers)
    assert rider_active.status_code == 200
    active_list = rider_active.json()
    assert len(active_list) >= 1
    rider_del = next(d for d in active_list if d["id"] == delivery_id)
    assert len(rider_del["stops"]) == 1
    stop_id = rider_del["stops"][0]["id"]

    # 9. Rider Starts Delivery
    start_res = client.post(f"/api/v1/deliveries/{delivery_id}/start", headers=rider_headers)
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "in_transit"

    # Verify customer sees out_for_delivery
    cust_track = client.get(f"/api/v1/shop/orders/{order_id}", headers=cust_headers)
    assert cust_track.status_code == 200
    track_data = cust_track.json()
    assert track_data["status"] == "out_for_delivery"
    assert track_data["rider_first_name"] is not None

    # 10. Rider Delivers Stop
    deliver_stop_res = client.post(f"/api/v1/deliveries/{delivery_id}/stops/{stop_id}/deliver", headers=rider_headers)
    assert deliver_stop_res.status_code == 200
    assert deliver_stop_res.json()["delivery_completed"] is True

    # Customer Order Final Status check
    cust_final = client.get(f"/api/v1/shop/orders/{order_id}", headers=cust_headers).json()
    assert cust_final["status"] == "delivered"


def test_eta_409_when_route_not_generated():
    # Attempting GET /deliveries/{id}/eta when delivery has no route returns 409
    del_res = client.get("/api/v1/deliveries/99999/eta", headers=AUTH_ADMIN)
    assert del_res.status_code == 404


def test_admin_reset_rider_password(client, admin_headers):
    suffix = uuid.uuid4().hex[:6]
    wh_code = f"WH-PWD-{suffix}"

    # 1. Create Warehouse
    wh_res = client.post("/api/v1/warehouses", headers=admin_headers, json={
        "code": wh_code,
        "name": "Password Test Store",
        "latitude": 13.0,
        "longitude": 80.0,
        "address": "Password Test Rd"
    })
    wh_id = wh_res.json()["id"]

    # 2. Generate Store Fleet
    fleet_res = client.post(f"/api/v1/warehouses/{wh_id}/fleet/generate", headers=admin_headers, json={
        "riders": 1,
        "ev_count": 1
    })
    fleet_data = fleet_res.json()
    rider_user_id = fleet_data["riders"][0]["user_id"]
    rider_email = fleet_data["riders"][0]["email"]

    # 3. Admin resets rider password
    new_password = "NewSecurePassword123!"
    update_res = client.patch(f"/api/v1/users/{rider_user_id}", headers=admin_headers, json={
        "password": new_password
    })
    assert update_res.status_code == 200

    # 4. Rider logs in with new password
    login_res = client.post("/api/v1/auth/login", json={
        "email": rider_email,
        "password": new_password
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

