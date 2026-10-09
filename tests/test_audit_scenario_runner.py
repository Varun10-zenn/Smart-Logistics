"""Audit script for Deliveries, Safety, and EV Charging endpoints and scenarios."""
import pytest
from datetime import datetime, timedelta
from backend.app.models.user import User, Role
from backend.app.models.delivery import Driver, Delivery
from backend.app.models.vehicle import Vehicle, VehicleType
from backend.app.models.warehouse import Warehouse
from backend.app.models.order import Order
from backend.app.models.batch import Batch
from backend.app.models.charging import ChargingStation, ChargingConnector, ChargingSlot
from backend.app.core.security import hash_password, create_access_token


def test_audit_empty_db_endpoints(client, admin_headers):
    print("\n--- 1) AUDIT ENDPOINTS ON EMPTY DB ---")
    endpoints = [
        ("GET", "/api/v1/deliveries"),
        ("GET", "/api/v1/deliveries/999"),
        ("GET", "/api/v1/deliveries/999/eta"),
        ("GET", "/api/v1/deliveries/999/route"),
        ("GET", "/api/v1/telemetry/events"),
        ("GET", "/api/v1/safety/scores"),
        ("GET", "/api/v1/safety/scores/999"),
        ("GET", "/api/v1/safety/events"),
        ("GET", "/api/v1/safety/alerts"),
        ("GET", "/api/v1/charging/stations"),
        ("GET", "/api/v1/charging/stations/999"),
        ("GET", "/api/v1/charging/connectors"),
        ("GET", "/api/v1/charging/slots"),
        ("GET", "/api/v1/charging/reservations"),
        ("GET", "/api/v1/charging/sessions"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = client.get(path, headers=admin_headers)
        print(f"{method} {path} -> {res.status_code}")


def test_scenario_deliveries(client, admin_headers, db_session):
    print("\n--- 2A) DELIVERIES SCENARIO ---")
    # Create warehouse, batch, vehicle type, vehicle, driver
    wh = Warehouse(code="WH-DEL-01", name="Delivery WH", latitude=13.0, longitude=80.0, status="active")
    db_session.add(wh)
    db_session.commit()

    b = Batch(batch_code="B-DEL-01", warehouse_id=wh.id)
    db_session.add(b)

    vt = db_session.query(VehicleType).first()
    if not vt:
        vt = VehicleType(type_name="EV-Van", is_ev=True, max_payload_kg=500.0)
        db_session.add(vt)
        db_session.commit()

    v = Vehicle(registration_number="TN-01-EV-01", vehicle_type_id=vt.id, current_soc_percent=100.0)
    db_session.add(v)
    
    r_dr = db_session.query(Role).filter(Role.code == "driver").first()
    u_dr = User(email="driver_del@test.com", full_name="Driver Del", password_hash=hash_password("test"), role_id=r_dr.id)
    db_session.add(u_dr)
    db_session.commit()

    dr = Driver(user_id=u_dr.id, license_number="DL-DEL-01", status="available")
    db_session.add(dr)
    db_session.commit()

    # Create delivery via API
    res_del = client.post("/api/v1/deliveries", json={
        "batch_id": b.id,
        "driver_id": dr.id,
        "vehicle_id": v.id
    }, headers=admin_headers)
    print("Create Delivery:", res_del.status_code, res_del.json())
    del_id = res_del.json()["id"]

    # Generate route
    res_route = client.post(f"/api/v1/deliveries/{del_id}/route", headers=admin_headers)
    print("Generate Route:", res_route.status_code, res_route.json() if res_route.status_code == 201 else res_route.text)

    # Read ETA
    res_eta = client.get(f"/api/v1/deliveries/{del_id}/eta", headers=admin_headers)
    print("Read ETA:", res_eta.status_code, res_eta.json())


def test_scenario_safety(client, admin_headers, db_session):
    print("\n--- 2B) SAFETY SCENARIO ---")
    deliv = db_session.query(Delivery).first()
    if not deliv:
        # Create minimal setup
        wh = db_session.query(Warehouse).first()
        b = Batch(batch_code="B-DEL-SAF", warehouse_id=wh.id)
        db_session.add(b)
        v = db_session.query(Vehicle).first()
        dr = db_session.query(Driver).first()
        db_session.commit()
        deliv = Delivery(delivery_code="DEL-SAF-001", batch_id=b.id, driver_id=dr.id, vehicle_id=v.id, status="assigned", scheduled_dispatch_time=datetime.utcnow(), estimated_eta=datetime.utcnow()+timedelta(hours=1))
        db_session.add(deliv)
        db_session.commit()

    # Ingest telemetry with speed 95 and accel -4.5
    event_payload = {
        "vehicle_id": deliv.vehicle_id,
        "delivery_id": deliv.id,
        "timestamp": datetime.utcnow().isoformat(),
        "latitude": 13.01,
        "longitude": 80.01,
        "speed_kmh": 95.0,
        "acceleration_ms2": -4.5,
        "battery_soc_percent": 80.0
    }
    res_telem = client.post("/api/v1/telemetry/events", json=event_payload, headers=admin_headers)
    print("Ingest Telemetry:", res_telem.status_code, res_telem.json())

    # Check safety events
    res_events = client.get(f"/api/v1/safety/events?delivery_id={deliv.id}", headers=admin_headers)
    print("Safety Events:", res_events.status_code, res_events.json())

    # Check safety score
    res_score = client.get(f"/api/v1/safety/scores/{deliv.id}", headers=admin_headers)
    print("Safety Score:", res_score.status_code, res_score.json() if res_score.status_code == 200 else res_score.text)

    # Check safety alerts
    res_alerts = client.get(f"/api/v1/safety/alerts?delivery_id={deliv.id}", headers=admin_headers)
    print("Safety Alerts:", res_alerts.status_code, res_alerts.json())


def test_scenario_charging(client, admin_headers, db_session):
    print("\n--- 2C) CHARGING SCENARIO ---")
    # 1. Create Station via API
    res_st = client.post("/api/v1/charging/stations", json={
        "station_code": "ST-AUDIT-01",
        "name": "Audit Charging Station",
        "latitude": 13.0,
        "longitude": 80.0,
        "address": "Audit St",
        "total_connectors": 2
    }, headers=admin_headers)
    print("Create Station:", res_st.status_code, res_st.json() if res_st.status_code == 201 else res_st.text)
    if res_st.status_code != 201:
        return
    st_id = res_st.json()["id"]

    # Check if connectors/slots endpoints exist for creation
    res_conn_create = client.post("/api/v1/charging/connectors", json={}, headers=admin_headers)
    print("POST /charging/connectors ->", res_conn_create.status_code)
    res_slot_create = client.post("/api/v1/charging/slots", json={}, headers=admin_headers)
    print("POST /charging/slots ->", res_slot_create.status_code)

    # Seed connector and slot directly in DB for test continuation
    conn = ChargingConnector(station_id=st_id, connector_number=1, connector_type="CCS2", max_power_kw=50.0, status="available")
    db_session.add(conn)
    db_session.commit()

    now = datetime.utcnow()
    slot = ChargingSlot(connector_id=conn.id, start_time=now, end_time=now + timedelta(hours=2), is_booked=False)
    db_session.add(slot)
    db_session.commit()

    v = db_session.query(Vehicle).first()
    dr = db_session.query(Driver).first()

    # Recommend for vehicle at 15% SoC
    res_rec = client.post("/api/v1/charging/recommend", json={
        "vehicle_id": v.id,
        "current_lat": 13.0,
        "current_lon": 80.0,
        "current_soc_percent": 15.0
    }, headers=admin_headers)
    print("Recommend Charging:", res_rec.status_code, res_rec.json() if res_rec.status_code == 200 else res_rec.text)

    # Reserve slot
    now = datetime.utcnow()
    res_res1 = client.post("/api/v1/charging/reservations", json={
        "slot_id": slot.id,
        "vehicle_id": v.id,
        "driver_id": dr.id,
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(hours=1)).isoformat()
    }, headers=admin_headers)
    print("Reservation 1:", res_res1.status_code, res_res1.json() if res_res1.status_code == 201 else res_res1.text)

    # Overlapping reservation attempt
    res_res2 = client.post("/api/v1/charging/reservations", json={
        "slot_id": slot.id,
        "vehicle_id": v.id,
        "driver_id": dr.id,
        "start_time": (now + timedelta(minutes=30)).isoformat(),
        "end_time": (now + timedelta(hours=1, minutes=30)).isoformat()
    }, headers=admin_headers)
    print("Overlapping Reservation 2:", res_res2.status_code, res_res2.text)
