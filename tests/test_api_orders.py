"""Order API tests."""
import pytest
from datetime import datetime, timezone, timedelta


def _future_time(hours=24):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


class TestOrderCreation:
    def test_create_order_requires_items(self, client, warehouse_op_headers):
        resp = client.post("/api/v1/orders", headers=warehouse_op_headers, json={
            "warehouse_id": 1,
            "customer_lat": 12.9716,
            "customer_lon": 77.5946,
            "promised_at": _future_time(),
            "priority": "normal",
            "items": []  # Empty items — must fail
        })
        assert resp.status_code == 422

    def test_create_order_invalid_priority_returns_422(self, client, warehouse_op_headers):
        resp = client.post("/api/v1/orders", headers=warehouse_op_headers, json={
            "warehouse_id": 1,
            "customer_lat": 12.9716,
            "customer_lon": 77.5946,
            "promised_at": _future_time(),
            "priority": "super_urgent",  # Invalid
            "items": [{"product_id": 1, "quantity": 1}]
        })
        assert resp.status_code == 422

    def test_create_order_invalid_coordinates_returns_422(self, client, warehouse_op_headers):
        resp = client.post("/api/v1/orders", headers=warehouse_op_headers, json={
            "warehouse_id": 1,
            "customer_lat": 200.0,  # Invalid
            "customer_lon": 0.0,
            "promised_at": _future_time(),
            "priority": "normal",
            "items": [{"product_id": 1, "quantity": 1}]
        })
        assert resp.status_code == 422

    def test_create_order_zero_quantity_returns_422(self, client, warehouse_op_headers):
        resp = client.post("/api/v1/orders", headers=warehouse_op_headers, json={
            "warehouse_id": 1,
            "customer_lat": 12.9,
            "customer_lon": 77.5,
            "promised_at": _future_time(),
            "priority": "normal",
            "items": [{"product_id": 1, "quantity": 0}]  # Invalid
        })
        assert resp.status_code == 422


class TestOrderList:
    def test_list_orders_returns_pagination(self, client, admin_headers):
        resp = client.get("/api/v1/orders", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "pagination" in data

    def test_filter_by_status(self, client, admin_headers):
        resp = client.get("/api/v1/orders?status=pending", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["status"] == "pending"

    def test_filter_by_priority(self, client, admin_headers):
        resp = client.get("/api/v1/orders?priority=normal", headers=admin_headers)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["priority"] == "normal"


class TestOrderStatusUpdate:
    def test_update_status_invalid_value_returns_422(self, client, admin_headers):
        resp = client.patch("/api/v1/orders/1/status", headers=admin_headers, json={
            "status": "flying"  # Invalid
        })
        assert resp.status_code == 422

    def test_get_nonexistent_order_returns_404(self, client, admin_headers):
        resp = client.get("/api/v1/orders/999999", headers=admin_headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"
