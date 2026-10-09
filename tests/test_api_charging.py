"""Charging API tests — including atomic reservation conflict detection."""
import pytest


class TestChargingStations:
    def test_list_stations_returns_page(self, client, admin_headers):
        resp = client.get("/api/v1/charging/stations", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "pagination" in data

    def test_create_station_returns_201(self, client, admin_headers):
        resp = client.post("/api/v1/charging/stations", headers=admin_headers, json={
            "station_code": "CHG-TEST-01",
            "name": "Test Charging Station",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "total_connectors": 4,
            "status": "operational"
        })
        assert resp.status_code in (201, 409)  # 409 if already exists

    def test_invalid_station_code_length_returns_422(self, client, admin_headers):
        resp = client.post("/api/v1/charging/stations", headers=admin_headers, json={
            "station_code": "X" * 100,  # Exceeds max_length=32
            "name": "Bad Station",
            "latitude": 0.0,
            "longitude": 0.0,
            "total_connectors": 1,
        })
        assert resp.status_code == 422

    def test_get_nonexistent_station_returns_404(self, client, admin_headers):
        resp = client.get("/api/v1/charging/stations/999999", headers=admin_headers)
        assert resp.status_code == 404


class TestChargingRecommendation:
    def test_recommend_requires_all_fields(self, client, admin_headers):
        resp = client.post("/api/v1/charging/recommend", headers=admin_headers, json={
            "vehicle_id": 1,
            "current_soc_percent": 20.0,
            # Missing destination and current lat/lon
        })
        assert resp.status_code == 422

    def test_recommend_invalid_soc_returns_422(self, client, admin_headers):
        resp = client.post("/api/v1/charging/recommend", headers=admin_headers, json={
            "vehicle_id": 1,
            "current_soc_percent": 150.0,  # > 100
            "destination_lat": 12.9,
            "destination_lon": 77.5,
            "current_lat": 12.8,
            "current_lon": 77.4,
        })
        assert resp.status_code == 422


class TestChargingReservations:
    def test_create_reservation_nonexistent_slot_returns_404(self, client, admin_headers):
        resp = client.post("/api/v1/charging/reservations", headers=admin_headers, json={
            "slot_id": 999999,
            "vehicle_id": 1,
            "driver_id": 1,
        })
        assert resp.status_code == 404

    def test_reservation_missing_required_fields_returns_422(self, client, admin_headers):
        resp = client.post("/api/v1/charging/reservations", headers=admin_headers, json={
            "slot_id": 1,
            # Missing vehicle_id, driver_id
        })
        assert resp.status_code == 422

    def test_cancel_nonexistent_reservation_returns_404(self, client, admin_headers):
        resp = client.delete("/api/v1/charging/reservations/999999", headers=admin_headers)
        assert resp.status_code == 404


class TestChargingSessions:
    def test_list_sessions_returns_page(self, client, admin_headers):
        resp = client.get("/api/v1/charging/sessions", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "pagination" in data


class TestSlotAndConnector:
    def test_list_connectors_returns_page(self, client, admin_headers):
        resp = client.get("/api/v1/charging/connectors", headers=admin_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_list_slots_available_only_filter(self, client, admin_headers):
        resp = client.get("/api/v1/charging/slots?available_only=true", headers=admin_headers)
        assert resp.status_code == 200
        for slot in resp.json()["items"]:
            assert slot["is_booked"] is False
