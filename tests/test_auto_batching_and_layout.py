"""
Integration tests for layout generator, CSV imports, and auto-batching.
"""
import io
import time
import pytest
from fastapi.testclient import TestClient
from backend.app.core.config import settings
from backend.app.models.order import Order
from backend.app.services.auto_batch_scheduler import run_auto_batch_cycle, get_warehouse_lock

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


def test_layout_generator_output_validates_and_has_loops(client):
    # 1. Create Warehouse
    res = client.post("/api/v1/warehouses", headers=AUTH_ADMIN, json={
        "code": "WH-GEN-01",
        "name": "Generated Warehouse",
        "latitude": 13.0,
        "longitude": 80.0
    })
    wh_id = res.json()["id"]

    # 2. Generate Layout (2 aisles, 3 shelves per aisle)
    gen_res = client.post(f"/api/v1/warehouses/{wh_id}/layout/generate", headers=AUTH_ADMIN, json={
        "aisles": 2,
        "shelves_per_aisle": 3,
        "aisle_spacing_m": 4.0,
        "shelf_spacing_m": 2.0,
        "replace_existing": False
    })
    assert gen_res.status_code == 201
    graph = gen_res.json()

    # Nodes count: 1 depot + 2 junctions + 6 shelves = 9
    assert len(graph["nodes"]) == 9
    assert any(n["is_depot"] for n in graph["nodes"])
    assert len(graph["locations"]) == 6

    # Verify loop existence (cross-aisle edge connecting far-end nodes)
    # Total edges: 1 (depot to J1) + 1 (J1 to J2) + 3 (aisle 1) + 3 (aisle 2) + 1 (cross-aisle far end) = 9 edges
    assert len(graph["edges"]) == 9

    # 3. Validate layout
    val_res = client.get(f"/api/v1/warehouses/{wh_id}/validate", headers=AUTH_ADMIN)
    assert val_res.status_code == 200
    assert val_res.json()["valid"] is True


def test_layout_generator_replace_existing(client):
    res = client.post("/api/v1/warehouses", headers=AUTH_ADMIN, json={
        "code": "WH-REPLACE-01",
        "name": "Replace Warehouse",
        "latitude": 13.0,
        "longitude": 80.0
    })
    wh_id = res.json()["id"]

    # Initial layout
    client.post(f"/api/v1/warehouses/{wh_id}/layout/generate", headers=AUTH_ADMIN, json={
        "aisles": 1,
        "shelves_per_aisle": 2,
        "aisle_spacing_m": 3.0,
        "shelf_spacing_m": 2.0,
        "replace_existing": False
    })

    # Second generate without replace_existing -> 409
    res_conflict = client.post(f"/api/v1/warehouses/{wh_id}/layout/generate", headers=AUTH_ADMIN, json={
        "aisles": 1,
        "shelves_per_aisle": 2,
        "aisle_spacing_m": 3.0,
        "shelf_spacing_m": 2.0,
        "replace_existing": False
    })
    assert res_conflict.status_code == 409

    # Second generate WITH replace_existing -> 201 Success
    res_success = client.post(f"/api/v1/warehouses/{wh_id}/layout/generate", headers=AUTH_ADMIN, json={
        "aisles": 1,
        "shelves_per_aisle": 2,
        "aisle_spacing_m": 3.0,
        "shelf_spacing_m": 2.0,
        "replace_existing": True
    })
    assert res_success.status_code == 201


def test_csv_import_products_and_inventory(client):
    # Get Templates
    t_prod = client.get("/api/v1/products/import/template")
    assert t_prod.status_code == 200
    assert "sku,name" in t_prod.text

    t_inv = client.get("/api/v1/inventory/import/template")
    assert t_inv.status_code == 200
    assert "warehouse_code,location_code" in t_inv.text

    # Import Products (Good & Bad rows)
    prod_csv = "sku,name,category,unit_weight_kg,unit_volume_cbm,price\nPROD-CSV-1,CSV Widget,Tech,1.0,0.002,19.99\nBAD_ROW_SKU\n"
    files = {"file": ("products.csv", io.BytesIO(prod_csv.encode("utf-8")), "text/csv")}
    prod_res = client.post("/api/v1/products/import", headers=AUTH_ADMIN, files=files)
    assert prod_res.status_code == 200
    prod_data = prod_res.json()
    assert prod_data["created"] == 1
    assert len(prod_data["errors"]) == 1

    # Setup Warehouse & Layout
    wh_res = client.post("/api/v1/warehouses", headers=AUTH_ADMIN, json={
        "code": "WH-CSV-01",
        "name": "CSV Darkstore",
        "latitude": 12.0,
        "longitude": 77.0
    })
    wh_id = wh_res.json()["id"]

    client.post(f"/api/v1/warehouses/{wh_id}/layout/generate", headers=AUTH_ADMIN, json={
        "aisles": 1,
        "shelves_per_aisle": 2,
        "aisle_spacing_m": 3.0,
        "shelf_spacing_m": 2.0,
        "replace_existing": True
    })

    # Import Inventory
    inv_csv = "warehouse_code,location_code,sku,quantity,reorder_threshold\nWH-CSV-01,A1-S01,PROD-CSV-1,50,5\nWH-CSV-01,NON_EXISTENT_LOC,PROD-CSV-1,10,2\n"
    inv_files = {"file": ("inventory.csv", io.BytesIO(inv_csv.encode("utf-8")), "text/csv")}
    inv_res = client.post("/api/v1/inventory/import", headers=AUTH_ADMIN, files=inv_files)
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["created"] == 1
    assert len(inv_data["errors"]) == 1


@pytest.mark.asyncio
async def test_auto_batching_cycle_and_lock(client, db_session):
    # 1. Setup Warehouse & Products & Inventory
    wh_res = client.post("/api/v1/warehouses", headers=AUTH_ADMIN, json={
        "code": "WH-AUTO-01",
        "name": "Auto Batch Darkstore",
        "latitude": 12.95,
        "longitude": 77.59
    })
    wh_id = wh_res.json()["id"]

    client.post(f"/api/v1/warehouses/{wh_id}/layout/generate", headers=AUTH_ADMIN, json={
        "aisles": 1,
        "shelves_per_aisle": 2,
        "aisle_spacing_m": 3.0,
        "shelf_spacing_m": 2.0,
        "replace_existing": True
    })

    prod_res = client.post("/api/v1/products", headers=AUTH_ADMIN, json={
        "sku": "SKU-AUTO-1",
        "name": "Auto Item",
        "category": "General",
        "unit_weight_kg": 1.0,
        "unit_volume_cbm": 0.001,
        "price": 10.0
    })
    prod_id = prod_res.json()["id"]

    locs = client.get(f"/api/v1/warehouses/{wh_id}/locations", headers=AUTH_ADMIN).json()
    loc_id = locs[0]["id"]

    client.post("/api/v1/inventory", headers=AUTH_ADMIN, json={
        "warehouse_id": wh_id,
        "location_id": loc_id,
        "product_id": prod_id,
        "quantity": 100,
        "reorder_threshold": 10
    })

    # Create Customer Order via checkout
    cust_reg = client.post("/api/v1/auth/register", json={
        "email": "autocust@example.com",
        "password": "password123"
    })
    cust_login = client.post("/api/v1/auth/login", json={
        "email": "autocust@example.com",
        "password": "password123"
    }).json()
    cust_headers = {"Authorization": f"Bearer {cust_login['access_token']}"}

    chk_res = client.post("/api/v1/shop/checkout", headers=cust_headers, json={
        "items": [{"product_id": prod_id, "quantity": 2}],
        "lat": 12.95,
        "lon": 77.59,
        "address": "Auto Customer Address"
    })
    assert chk_res.status_code == 201
    order_id = chk_res.json()["id"]

    # Verify initial state is pending
    order_init = client.get(f"/api/v1/orders/{order_id}", headers=AUTH_ADMIN).json()
    assert order_init["status"] == "pending"

    # Override settings temporarily to allow run_auto_batch_cycle execution
    orig_env = settings.APP_ENV
    settings.APP_ENV = "local"
    settings.AUTO_BATCH_ENABLED = True
    settings.AUTO_BATCH_MIN_ORDERS = 1

    try:
        # Run auto-batch cycle
        await run_auto_batch_cycle()

        # Order status should now automatically be 'batched' without manual optimize call
        order_after = client.get(f"/api/v1/orders/{order_id}", headers=AUTH_ADMIN).json()
        assert order_after["status"] == "batched"
    finally:
        settings.APP_ENV = orig_env


@pytest.mark.asyncio
async def test_auto_batching_skips_invalid_layout(client):
    # Create Warehouse with disconnected / invalid layout
    wh_res = client.post("/api/v1/warehouses", headers=AUTH_ADMIN, json={
        "code": "WH-INVALID-01",
        "name": "Invalid Darkstore",
        "latitude": 13.0,
        "longitude": 80.0
    })
    wh_id = wh_res.json()["id"]

    # Add isolated node (no depot) -> invalid layout
    client.post(f"/api/v1/warehouses/{wh_id}/nodes", headers=AUTH_ADMIN, json={
        "node_code": "N-ISOLATED",
        "x_coord": 1.0,
        "y_coord": 1.0,
        "is_depot": False
    })

    orig_env = settings.APP_ENV
    settings.APP_ENV = "local"
    try:
        # Run cycle -> should skip cleanly without crashing
        await run_auto_batch_cycle()
    finally:
        settings.APP_ENV = orig_env
