"""RBAC enforcement tests — one allowed/denied pair per critical endpoint."""
import pytest


class TestWarehouseRBAC:
    def test_admin_can_list_warehouses(self, client, admin_headers):
        resp = client.get("/api/v1/warehouses", headers=admin_headers)
        assert resp.status_code == 200

    def test_warehouse_op_can_list_warehouses(self, client, warehouse_op_headers):
        resp = client.get("/api/v1/warehouses", headers=warehouse_op_headers)
        assert resp.status_code == 200

    def test_driver_cannot_list_warehouses(self, client, driver_headers):
        resp = client.get("/api/v1/warehouses", headers=driver_headers)
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"

    def test_driver_cannot_create_warehouse(self, client, driver_headers):
        resp = client.post("/api/v1/warehouses", headers=driver_headers, json={
            "code": "WH-X", "name": "X", "latitude": 0.0, "longitude": 0.0
        })
        assert resp.status_code == 403

    def test_unauthenticated_cannot_list_warehouses(self, client):
        resp = client.get("/api/v1/warehouses")
        assert resp.status_code == 401


class TestOrdersRBAC:
    def test_warehouse_op_can_list_orders(self, client, warehouse_op_headers):
        resp = client.get("/api/v1/orders", headers=warehouse_op_headers)
        assert resp.status_code == 200

    def test_driver_cannot_list_orders(self, client, driver_headers):
        resp = client.get("/api/v1/orders", headers=driver_headers)
        assert resp.status_code == 403

    def test_station_admin_cannot_list_orders(self, client, station_admin_headers):
        resp = client.get("/api/v1/orders", headers=station_admin_headers)
        assert resp.status_code == 403


class TestUsersRBAC:
    def test_admin_can_list_users(self, client, admin_headers):
        resp = client.get("/api/v1/users", headers=admin_headers)
        assert resp.status_code == 200

    def test_non_admin_cannot_list_users(self, client, warehouse_op_headers):
        resp = client.get("/api/v1/users", headers=warehouse_op_headers)
        assert resp.status_code == 403

    def test_driver_cannot_list_users(self, client, driver_headers):
        resp = client.get("/api/v1/users", headers=driver_headers)
        assert resp.status_code == 403


class TestAuditRBAC:
    def test_admin_can_read_audit_logs(self, client, admin_headers):
        resp = client.get("/api/v1/audit/logs", headers=admin_headers)
        assert resp.status_code == 200

    def test_warehouse_op_cannot_read_audit_logs(self, client, warehouse_op_headers):
        resp = client.get("/api/v1/audit/logs", headers=warehouse_op_headers)
        assert resp.status_code == 403

    def test_driver_cannot_read_audit_logs(self, client, driver_headers):
        resp = client.get("/api/v1/audit/logs", headers=driver_headers)
        assert resp.status_code == 403

    def test_fleet_manager_cannot_read_audit_logs(self, client, fleet_manager_headers):
        resp = client.get("/api/v1/audit/logs", headers=fleet_manager_headers)
        assert resp.status_code == 403


class TestChargingRBAC:
    def test_driver_can_list_stations(self, client, driver_headers):
        resp = client.get("/api/v1/charging/stations", headers=driver_headers)
        assert resp.status_code == 200

    def test_warehouse_op_cannot_list_stations(self, client, warehouse_op_headers):
        resp = client.get("/api/v1/charging/stations", headers=warehouse_op_headers)
        assert resp.status_code == 403

    def test_station_admin_can_create_station(self, client, station_admin_headers):
        resp = client.post("/api/v1/charging/stations", headers=station_admin_headers, json={
            "station_code": "RBAC-TEST-01",
            "name": "Test Station",
            "latitude": 1.0,
            "longitude": 1.0,
            "total_connectors": 2,
        })
        # 201 or 409 (already exists) — both mean RBAC passed
        assert resp.status_code in (201, 409)

    def test_warehouse_op_cannot_create_station(self, client, warehouse_op_headers):
        resp = client.post("/api/v1/charging/stations", headers=warehouse_op_headers, json={
            "station_code": "RBAC-TEST-02",
            "name": "Test Station 2",
            "latitude": 1.0,
            "longitude": 1.0,
            "total_connectors": 2,
        })
        assert resp.status_code == 403


class TestIntelligenceRBAC:
    def test_any_authenticated_user_can_run_intelligence(self, client, driver_headers):
        resp = client.post("/api/v1/intelligence/run", headers=driver_headers, json={
            "operation": "warehouse_batch_recommendation",
            "context": {"warehouse_id": 1, "order_count": 10}
        })
        # Stub may fail if warehouse doesn't exist, but RBAC should pass
        assert resp.status_code in (200, 404)

    def test_unauthenticated_cannot_run_intelligence(self, client):
        resp = client.post("/api/v1/intelligence/run", json={
            "operation": "warehouse_batch_recommendation",
            "context": {}
        })
        assert resp.status_code == 401


class TestDeliveriesRBAC:
    def test_fleet_manager_can_list_deliveries(self, client, fleet_manager_headers):
        resp = client.get("/api/v1/deliveries", headers=fleet_manager_headers)
        assert resp.status_code == 200

    def test_warehouse_op_cannot_list_deliveries(self, client, warehouse_op_headers):
        resp = client.get("/api/v1/deliveries", headers=warehouse_op_headers)
        assert resp.status_code == 403

    def test_station_admin_cannot_list_deliveries(self, client, station_admin_headers):
        resp = client.get("/api/v1/deliveries", headers=station_admin_headers)
        assert resp.status_code == 403
