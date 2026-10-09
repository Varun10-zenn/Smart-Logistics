"""
Tests for Phase 3.7 — Warehouse Optimization API Integration.
"""

import pytest


def test_unauthenticated_request_rejected(client):
    res = client.get("/api/v1/warehouses/1/graph")
    assert res.status_code == 401


def test_unauthorized_role_rejected(client, driver_headers):
    res = client.get("/api/v1/warehouses/1/graph", headers=driver_headers)
    assert res.status_code == 403


def test_get_warehouse_graph_success(client, admin_headers):
    list_resp = client.get("/api/v1/warehouses?page=1&page_size=1", headers=admin_headers)
    items = list_resp.json().get("items", [])
    if not items:
        pytest.skip("No warehouses seeded")
    wh_id = items[0]["id"]
    res = client.get(f"/api/v1/warehouses/{wh_id}/graph", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "warehouse_id" in data
    assert "nodes" in data


def test_missing_warehouse_not_found(client, admin_headers):
    res = client.get("/api/v1/warehouses/99999/graph", headers=admin_headers)
    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "NOT_FOUND"


def test_post_calculate_shortest_path(client, admin_headers):
    list_resp = client.get("/api/v1/warehouses?page=1&page_size=1", headers=admin_headers)
    items = list_resp.json().get("items", [])
    if not items:
        pytest.skip("No warehouses seeded")
    wh_id = items[0]["id"]
    payload = {
        "start_node_id": 1,
        "destination_node_id": 2,
        "algorithm": "a_star",
    }
    res = client.post(f"/api/v1/warehouses/{wh_id}/path", json=payload, headers=admin_headers)
    assert res.status_code in (200, 400)


def test_post_calculate_shortest_path_invalid_node(client, admin_headers):
    list_resp = client.get("/api/v1/warehouses?page=1&page_size=1", headers=admin_headers)
    items = list_resp.json().get("items", [])
    if not items:
        pytest.skip("No warehouses seeded")
    wh_id = items[0]["id"]
    payload = {
        "start_node_id": 99999,
        "destination_node_id": 2,
        "algorithm": "a_star",
    }
    res = client.post(f"/api/v1/warehouses/{wh_id}/path", json=payload, headers=admin_headers)
    assert res.status_code == 400
    data = res.json()
    assert data["error"]["code"] == "INVALID_ARGUMENT"


def test_post_generate_order_batches(client, admin_headers):
    list_resp = client.get("/api/v1/warehouses?page=1&page_size=1", headers=admin_headers)
    items = list_resp.json().get("items", [])
    if not items:
        pytest.skip("No warehouses seeded")
    wh_id = items[0]["id"]
    payload = {
        "max_orders_per_batch": 5,
        "strategy": "priority_heuristic",
    }
    res = client.post(f"/api/v1/warehouses/{wh_id}/batch", json=payload, headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True


def test_post_optimize_agent_endpoint(client, admin_headers):
    list_resp = client.get("/api/v1/warehouses?page=1&page_size=1", headers=admin_headers)
    items = list_resp.json().get("items", [])
    if not items:
        pytest.skip("No warehouses seeded")
    wh_id = items[0]["id"]
    payload = {
        "operation": "get_warehouse_graph",
        "payload": {},
        "user_prompt": "Optimize warehouse graph layout",
    }
    res = client.post(f"/api/v1/warehouses/{wh_id}/optimize", json=payload, headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["operation"] == "get_warehouse_graph"


def test_get_warehouse_metrics(client, admin_headers):
    list_resp = client.get("/api/v1/warehouses?page=1&page_size=1", headers=admin_headers)
    items = list_resp.json().get("items", [])
    if not items:
        pytest.skip("No warehouses seeded")
    wh_id = items[0]["id"]
    res = client.get(f"/api/v1/warehouses/{wh_id}/metrics", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["warehouse_id"] == wh_id
