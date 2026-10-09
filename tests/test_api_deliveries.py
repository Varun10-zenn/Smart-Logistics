"""Integration tests for Phase 4 Delivery and Safety."""
import pytest
from datetime import datetime, timezone

@pytest.fixture
def test_delivery(client, admin_headers):
    resp = client.post("/api/v1/deliveries", headers=admin_headers, json={
        "batch_id": 1,
        "driver_id": 1,
        "vehicle_id": 1,
        "scheduled_dispatch_time": datetime.now(timezone.utc).isoformat()
    })
    assert resp.status_code == 201
    return resp.json()

def test_create_delivery(test_delivery):
    assert test_delivery["status"] == "assigned"
    assert "delivery_code" in test_delivery
    
def test_create_delivery_vehicle_in_use(client, admin_headers, test_delivery):
    # Vehicle 1 is already assigned to the delivery created above
    resp = client.post("/api/v1/deliveries", headers=admin_headers, json={
        "batch_id": 1,
        "driver_id": 1,
        "vehicle_id": 1,
        "scheduled_dispatch_time": datetime.now(timezone.utc).isoformat()
    })
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"

def test_generate_route(client, admin_headers, test_delivery):
    delivery_id = test_delivery["id"]
    resp = client.post(f"/api/v1/deliveries/{delivery_id}/route", headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "total_distance_km" in data
    assert "estimated_travel_minutes" in data

def test_get_eta(client, admin_headers, driver_headers, test_delivery):
    delivery_id = test_delivery["id"]
    client.post(f"/api/v1/deliveries/{delivery_id}/route", headers=admin_headers)
    resp = client.get(f"/api/v1/deliveries/{delivery_id}/eta", headers=driver_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "eta" in data

def test_telemetry_and_safety_analysis(client, driver_headers, test_delivery):
    delivery_id = test_delivery["id"]
    now = datetime.now(timezone.utc).isoformat()
    
    # Send a normal event
    resp1 = client.post("/api/v1/telemetry/events", headers=driver_headers, json={
        "vehicle_id": 1,
        "delivery_id": delivery_id,
        "timestamp": now,
        "latitude": 13.05,
        "longitude": 80.05,
        "speed_kmh": 40.0,
        "heading_degrees": 90.0,
        "acceleration_ms2": 0.0,
        "soc_percent": 95.0
    })
    assert resp1.status_code == 201
    
    # Send a speeding event (speed > 80.0)
    resp2 = client.post("/api/v1/telemetry/events", headers=driver_headers, json={
        "vehicle_id": 1,
        "delivery_id": delivery_id,
        "timestamp": now,
        "latitude": 13.06,
        "longitude": 80.06,
        "speed_kmh": 90.0,
        "heading_degrees": 90.0,
        "acceleration_ms2": 0.5,
        "soc_percent": 94.0
    })
    assert resp2.status_code == 201

    # Send a harsh braking event (accel < -4.0)
    resp3 = client.post("/api/v1/telemetry/events", headers=driver_headers, json={
        "vehicle_id": 1,
        "delivery_id": delivery_id,
        "timestamp": now,
        "latitude": 13.07,
        "longitude": 80.07,
        "speed_kmh": 60.0,
        "heading_degrees": 90.0,
        "acceleration_ms2": -5.0,
        "soc_percent": 93.0
    })
    assert resp3.status_code == 201
    
    # Get safety score
    resp = client.get(f"/api/v1/safety/scores/{delivery_id}", headers=driver_headers)
    assert resp.status_code == 200
    score_data = resp.json()
    
    assert score_data["score"] == 98.75
    assert score_data["speed_score"] == 98.0
    assert score_data["braking_score"] == 97.0
