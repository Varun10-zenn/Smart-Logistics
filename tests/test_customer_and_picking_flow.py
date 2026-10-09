"""End-to-end tests for Customer Ordering, Picking & Stock Deduction, and Auth Bypass Rules."""
import pytest
import uuid
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


def test_auth_bypass_off_returns_401():
    settings.DEV_AUTH_BYPASS = False
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer dev-bypass-token"})
    assert res.status_code == 401

    res_invalid = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token_123"})
    assert res_invalid.status_code == 401


def test_customer_registration_flow():
    suffix = uuid.uuid4().hex[:6]
    reg_res = client.post("/api/v1/auth/register", json={
        "username": f"alice_{suffix}",
        "email": f"alice_{suffix}@example.com",
        "password": "password123"
    })
    assert reg_res.status_code == 201
    data = reg_res.json()
    assert data["email"] == f"alice_{suffix}@example.com"
    assert data["role"] == "customer"


def test_shop_and_checkout_flow():
    suffix = uuid.uuid4().hex[:6]
    wh_lat = 14.5000 + (int(suffix[:3], 16) % 100) * 0.01
    wh_lon = 76.5000 + (int(suffix[3:], 16) % 100) * 0.01

    # 1. Setup Warehouse & Product & Inventory as admin
    wh_res = client.post("/api/v1/warehouses", headers=AUTH_ADMIN, json={
        "code": f"WH-SHOP-{suffix}",
        "name": "Central Darkstore",
        "latitude": wh_lat,
        "longitude": wh_lon,
        "address": "MG Road"
    })
    wh_id = wh_res.json()["id"]

    prod_res = client.post("/api/v1/products", headers=AUTH_ADMIN, json={
        "sku": f"SKU-SHOP-{suffix}",
        "name": "Fresh Organic Milk",
        "category": "Dairy",
        "unit_weight_kg": 1.0,
        "unit_volume_cbm": 0.001,
        "price": 4.50
    })
    prod_id = prod_res.json()["id"]

    node_res = client.post(f"/api/v1/warehouses/{wh_id}/nodes", headers=AUTH_ADMIN, json={
        "node_code": f"N-S1-{suffix}",
        "x_coord": 0.0,
        "y_coord": 0.0,
        "is_depot": True
    })
    node_id = node_res.json()["id"]

    loc_res = client.post(f"/api/v1/warehouses/{wh_id}/locations", headers=AUTH_ADMIN, json={
        "node_id": node_id,
        "location_code": f"LOC-S1-{suffix}",
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
        "quantity": 20,
        "reorder_threshold": 5
    })

    # Register Customer Bob
    bob_email = f"bob_{suffix}@example.com"
    reg = client.post("/api/v1/auth/register", json={
        "username": f"bob_{suffix}",
        "email": bob_email,
        "password": "bobpassword"
    })
    bob_id = reg.json()["id"]

    # Login Customer Bob to get real JWT token
    login_res = client.post("/api/v1/auth/login", json={
        "email": bob_email,
        "password": "bobpassword"
    })
    bob_token = login_res.json()["access_token"]
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # 2. Browse Products within 10km radius
    shop_res = client.get(f"/api/v1/shop/products?lat={wh_lat:.4f}&lon={wh_lon:.4f}", headers=bob_headers)
    assert shop_res.status_code == 200
    shop_data = shop_res.json()
    assert shop_data["warehouse_id"] == wh_id
    item = next(p for p in shop_data["products"] if p["id"] == prod_id)
    assert item["available_quantity"] == 20

    # 3. Out-of-radius 404 test
    far_res = client.get("/api/v1/shop/products?lat=28.7041&lon=77.1025", headers=bob_headers)
    assert far_res.status_code == 404

    # 4. Checkout success
    chk_res = client.post("/api/v1/shop/checkout", headers=bob_headers, json={
        "items": [{"product_id": prod_id, "quantity": 5}],
        "lat": wh_lat,
        "lon": wh_lon,
        "address": "Bob's Apartment, MG Road"
    })
    assert chk_res.status_code == 201
    order_data = chk_res.json()
    order_id = order_data["id"]
    assert order_data["status"] == "pending"

    # Reserved stock check: available stock should now be 20 - 5 = 15
    shop_after = client.get(f"/api/v1/shop/products?lat={wh_lat:.4f}&lon={wh_lon:.4f}", headers=bob_headers).json()
    item_after = next(p for p in shop_after["products"] if p["id"] == prod_id)
    assert item_after["available_quantity"] == 15

    # Short stock 409 test: requested 50, available 15
    short_res = client.post("/api/v1/shop/checkout", headers=bob_headers, json={
        "items": [{"product_id": prod_id, "quantity": 50}],
        "lat": wh_lat,
        "lon": wh_lon,
        "address": "Bob's Apartment, MG Road"
    })
    assert short_res.status_code == 409

    # 5. Customer order ownership & isolation test
    cust_orders = client.get("/api/v1/shop/orders", headers=bob_headers).json()
    assert len(cust_orders) >= 1
    assert any(o["id"] == order_id for o in cust_orders)

    # Register Charlie Customer
    charlie_email = f"charlie_{suffix}@example.com"
    charlie_reg = client.post("/api/v1/auth/register", json={
        "email": charlie_email,
        "password": "charliepass"
    })
    charlie_login = client.post("/api/v1/auth/login", json={
        "email": charlie_email,
        "password": "charliepass"
    }).json()
    charlie_headers = {"Authorization": f"Bearer {charlie_login['access_token']}"}

    # Charlie trying to read Bob's order should return 404
    forbidden_res = client.get(f"/api/v1/shop/orders/{order_id}", headers=charlie_headers)
    assert forbidden_res.status_code == 404


def test_customer_order_timeline_status_mapping():
    """Verify backend _to_customer_order_read builds accurate timeline steps for each status."""
    from backend.app.core.database import SessionLocal
    from backend.app.models.order import Order
    from backend.app.models.warehouse import Warehouse
    from backend.app.models.user import User, Role
    from backend.app.services.shop_service import _to_customer_order_read
    from datetime import datetime

    db = SessionLocal()
    try:
        wh = db.query(Warehouse).first()
        user = db.query(User).first()

        statuses = ["pending", "batched", "picking", "picked", "out_for_delivery", "delivered"]
        for st in statuses:
            order = Order(
                order_number=f"ORD-TL-{st.upper()}",
                warehouse_id=wh.id if wh else 1,
                customer_id=user.id if user else 1,
                destination_address="Test Addr",
                destination_lat=12.97,
                destination_lon=79.14,
                priority=1,
                status=st,
                promised_at=datetime.utcnow()
            )
            db.add(order)
            db.commit()

            read_dto = _to_customer_order_read(db, order)
            assert read_dto.status == st

            # Verify step completions
            step_map = {s.step: s.completed for s in read_dto.timeline}
            assert step_map["placed"] is True

            if st == "pending":
                assert step_map["packing"] is False
                assert step_map["picked"] is False
                assert step_map["out_for_delivery"] is False
                assert step_map["delivered"] is False
            elif st == "batched":
                assert step_map["packing"] is True
                assert step_map["picked"] is False
                assert step_map["out_for_delivery"] is False
                assert step_map["delivered"] is False
            elif st in ["picking", "picked"]:
                assert step_map["packing"] is True
                assert step_map["picked"] is True
                assert step_map["out_for_delivery"] is False
                assert step_map["delivered"] is False
            elif st == "out_for_delivery":
                assert step_map["packing"] is True
                assert step_map["picked"] is True
                assert step_map["out_for_delivery"] is True
                assert step_map["delivered"] is False
            elif st == "delivered":
                assert step_map["packing"] is True
                assert step_map["picked"] is True
                assert step_map["out_for_delivery"] is True
                assert step_map["delivered"] is True

            db.delete(order)
            db.commit()
    finally:
        db.close()


def test_picking_and_stock_deduction_flow():
    suffix = uuid.uuid4().hex[:6]
    # Setup Warehouse & Batch
    wh_res = client.post("/api/v1/warehouses", headers=AUTH_ADMIN, json={
        "code": f"WH-PICK-{suffix}",
        "name": "Fulfillment Darkstore",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "address": "Chennai Hub"
    })
    wh_id = wh_res.json()["id"]

    prod_res = client.post("/api/v1/products", headers=AUTH_ADMIN, json={
        "sku": f"SKU-PICK-{suffix}",
        "name": "Energy Drink",
        "category": "Beverages",
        "unit_weight_kg": 0.5,
        "unit_volume_cbm": 0.0005,
        "price": 2.50
    })
    prod_id = prod_res.json()["id"]

    node_res = client.post(f"/api/v1/warehouses/{wh_id}/nodes", headers=AUTH_ADMIN, json={
        "node_code": f"N-P1-{suffix}",
        "x_coord": 0.0,
        "y_coord": 0.0,
        "is_depot": True
    })
    node_id = node_res.json()["id"]

    loc_res = client.post(f"/api/v1/warehouses/{wh_id}/locations", headers=AUTH_ADMIN, json={
        "node_id": node_id,
        "location_code": f"LOC-P1-{suffix}",
        "aisle": "A2",
        "shelf": "S1",
        "bin": "B2",
        "max_weight_kg": 500.0
    })
    loc_id = loc_res.json()["id"]

    # Initial physical stock = 10
    client.post("/api/v1/inventory", headers=AUTH_ADMIN, json={
        "warehouse_id": wh_id,
        "location_id": loc_id,
        "product_id": prod_id,
        "quantity": 10,
        "reorder_threshold": 2
    })

    # Create customer & order for 3 items
    cust_email = f"picker_user_{suffix}@example.com"
    reg = client.post("/api/v1/auth/register", json={
        "email": cust_email,
        "password": "password123"
    })
    login_res = client.post("/api/v1/auth/login", json={
        "email": cust_email,
        "password": "password123"
    }).json()
    headers = {"Authorization": f"Bearer {login_res['access_token']}"}

    chk = client.post("/api/v1/shop/checkout", headers=headers, json={
        "items": [{"product_id": prod_id, "quantity": 3}],
        "lat": 13.0830,
        "lon": 80.2710,
        "address": "Chennai Address"
    }).json()
    order_id = chk["id"]

    # Batch Optimization by admin
    opt_res = client.post(f"/api/v1/warehouses/{wh_id}/optimize", headers=AUTH_ADMIN, json={
        "max_orders_per_batch": 5,
        "max_weight_kg": 100.0,
        "max_volume_cbm": 5.0,
        "use_2opt_routing": False
    })
    assert opt_res.status_code == 200
    opt_data = opt_res.json()
    batch_id = opt_data["batches"][0]["batch_id"]

    # Fetch batch pick route
    route_res = client.get(f"/api/v1/batches/{batch_id}/pick-route", headers=AUTH_ADMIN)
    assert route_res.status_code == 200
    route_data = route_res.json()
    steps = route_data["steps"]
    assert len(steps) >= 1
    step_id = steps[0]["id"]
    assert steps[0]["is_completed"] is False
    assert steps[0]["quantity_to_pick"] == 3

    # Complete pick step -> Stock deduction happens ONLY here
    comp_res = client.post(f"/api/v1/pick-route-steps/{step_id}/complete", headers=AUTH_ADMIN)
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["is_completed"] is True

    # Check batch status & order status -> Batch status = completed, Order status = picked
    batch_check = client.get(f"/api/v1/batches/{batch_id}", headers=AUTH_ADMIN).json()
    assert batch_check["status"] == "completed"

    order_check = client.get(f"/api/v1/orders/{order_id}", headers=AUTH_ADMIN).json()
    assert order_check["status"] == "picked"

    # Verify inventory was deducted: 10 - 3 = 7
    inv_res = client.get(f"/api/v1/inventory?warehouse_id={wh_id}", headers=AUTH_ADMIN).json()
    inv_item = next(i for i in inv_res["items"] if i["product_id"] == prod_id)
    assert inv_item["quantity"] == 7

    # Double complete check: completing step twice does NOT double deduct!
    comp_twice = client.post(f"/api/v1/pick-route-steps/{step_id}/complete", headers=AUTH_ADMIN)
    assert comp_twice.status_code == 200
    inv_after_twice = client.get(f"/api/v1/inventory?warehouse_id={wh_id}", headers=AUTH_ADMIN).json()
    inv_item_twice = next(i for i in inv_after_twice["items"] if i["product_id"] == prod_id)
    assert inv_item_twice["quantity"] == 7
