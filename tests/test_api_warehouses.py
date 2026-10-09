"""Warehouse API CRUD and pagination tests."""
import pytest


class TestWarehousePagination:
    def test_list_warehouses_returns_page_schema(self, client, admin_headers):
        resp = client.get("/api/v1/warehouses?page=1&page_size=5", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "pagination" in data
        p = data["pagination"]
        assert "page" in p
        assert "page_size" in p
        assert "total_items" in p
        assert "total_pages" in p
        assert "has_next" in p
        assert "has_prev" in p

    def test_pagination_has_prev_false_on_first_page(self, client, admin_headers):
        resp = client.get("/api/v1/warehouses?page=1&page_size=5", headers=admin_headers)
        assert resp.json()["pagination"]["has_prev"] is False

    def test_list_warehouses_page_size_respected(self, client, admin_headers):
        resp = client.get("/api/v1/warehouses?page=1&page_size=2", headers=admin_headers)
        data = resp.json()
        assert len(data["items"]) <= 2


class TestWarehouseCRUD:
    UNIQUE_CODE = "WH-API-TEST-99"

    def test_create_warehouse_returns_201(self, client, admin_headers):
        resp = client.post("/api/v1/warehouses", headers=admin_headers, json={
            "code": self.UNIQUE_CODE,
            "name": "Test Warehouse",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address": "1 Test Street"
        })
        assert resp.status_code in (201, 409)  # 409 if already exists from prior run
        if resp.status_code == 201:
            data = resp.json()
            assert data["code"] == self.UNIQUE_CODE
            assert data["status"] == "active"

    def test_duplicate_code_returns_409(self, client, admin_headers):
        # First create
        client.post("/api/v1/warehouses", headers=admin_headers, json={
            "code": "WH-DUP-TEST",
            "name": "Dup Test",
            "latitude": 0.0,
            "longitude": 0.0,
        })
        # Duplicate
        resp = client.post("/api/v1/warehouses", headers=admin_headers, json={
            "code": "WH-DUP-TEST",
            "name": "Dup Test 2",
            "latitude": 0.0,
            "longitude": 0.0,
        })
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "DUPLICATE_RESOURCE"

    def test_get_nonexistent_warehouse_returns_404(self, client, admin_headers):
        resp = client.get("/api/v1/warehouses/999999", headers=admin_headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"

    def test_invalid_latitude_returns_422(self, client, admin_headers):
        resp = client.post("/api/v1/warehouses", headers=admin_headers, json={
            "code": "WH-INVALID",
            "name": "Bad",
            "latitude": 200.0,  # Invalid — must be <= 90
            "longitude": 0.0,
        })
        assert resp.status_code == 422

    def test_update_warehouse_status(self, client, admin_headers):
        # Get first warehouse
        list_resp = client.get("/api/v1/warehouses?page=1&page_size=1", headers=admin_headers)
        items = list_resp.json().get("items", [])
        if not items:
            pytest.skip("No warehouses in database")
        wh_id = items[0]["id"]
        resp = client.patch(f"/api/v1/warehouses/{wh_id}", headers=admin_headers, json={"status": "maintenance"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "maintenance"


class TestWarehouseGraph:
    def test_graph_endpoint_returns_correct_shape(self, client, admin_headers):
        list_resp = client.get("/api/v1/warehouses?page=1&page_size=1", headers=admin_headers)
        items = list_resp.json().get("items", [])
        if not items:
            pytest.skip("No warehouses in database")
        wh_id = items[0]["id"]
        resp = client.get(f"/api/v1/warehouses/{wh_id}/graph", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "warehouse_id" in data
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)
