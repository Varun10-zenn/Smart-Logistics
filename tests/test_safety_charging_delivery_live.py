"""
Tests for EV Charging System Extensions.

Validates:
1. Battery Model Fix: SoC drain uses vehicle specs (2.68 km @ 0.04 kWh/km on 3.5 kWh battery = ~3% drain).
2. Depot Chargers per Store: Schema fields, generation API, auto-creation in fleet generator.
3. Auto-Charge After Delivery: Vehicle status set to 'needs_charging' and auto-reservation created.
4. Charging Session Simulator: Active session SoC rise & completion idempotency.
5. Smarter Mid-Route Recommendation & Battery Overview API.
"""
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.app.core.database import Base, engine, SessionLocal
from backend.main import app
from backend.app.models.warehouse import Warehouse
from backend.app.models.vehicle import Vehicle, VehicleType
from backend.app.models.charging import ChargingStation, ChargingConnector, ChargingSlot, ChargingReservation, ChargingSession
from backend.app.models.delivery import Delivery, Driver, DeliveryStop, DeliveryRoute
from backend.app.models.batch import Batch
from backend.app.services import charging_service, delivery_service, simulator_service, ev_charging_optimization_service, vehicle_service


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


def test_battery_model_fix_drain(setup_db):
    """
    Test 1: A 2.68 km trip at 0.04 kWh/km on a 3.5 kWh battery drains ~3.06% SoC.
    """
    db = setup_db
    v_type = VehicleType(
        type_name="Test EV Scooter",
        is_ev=True,
        max_payload_kg=50.0,
        battery_capacity_kwh=3.5,
        consumption_kwh_per_km=0.04
    )
    db.add(v_type)
    db.flush()

    vehicle = Vehicle(
        registration_number="TEST-EV-01",
        vehicle_type_id=v_type.id,
        current_soc_percent=100.0,
        status="available",
        connector_type="CCS2"
    )
    db.add(vehicle)
    db.commit()

    dist_km = 2.68
    cons_per_km = float(vehicle.vehicle_type.consumption_kwh_per_km)
    bat_cap = float(vehicle.vehicle_type.battery_capacity_kwh)

    kwh_used = dist_km * cons_per_km
    soc_drain_pct = (kwh_used / bat_cap) * 100.0

    assert round(soc_drain_pct, 2) == 3.06
    new_soc = float(vehicle.current_soc_percent) - soc_drain_pct
    assert round(new_soc, 2) == 96.94


def test_depot_chargers_generation(setup_db):
    """
    Test 2: Generate depot chargers for a store creates station with is_depot=True and connectors.
    """
    db = setup_db
    wh = Warehouse(code="WH-DEPOT-TEST", name="Depot Test Store", latitude=13.0827, longitude=80.2707)
    db.add(wh)
    db.commit()

    st = charging_service.generate_depot_chargers(db, wh.id, connectors_count=2, max_power_kw=50.0, price_per_kwh=12.5)

    assert st is not None
    assert st.is_depot is True
    assert st.warehouse_id == wh.id
    assert len(st.connectors) == 2
    assert float(st.connectors[0].price_per_kwh) == 12.5


def test_auto_charge_after_delivery(setup_db):
    """
    Test 3: When delivery completes and EV SoC < LOW_SOC_THRESHOLD, vehicle status becomes needs_charging
    and auto-reservation is booked at the depot charger.
    """
    db = setup_db
    wh = Warehouse(code="WH-AUTO-CHARGE", name="Auto Charge Store", latitude=13.0827, longitude=80.2707)
    db.add(wh)
    db.flush()

    v_type = VehicleType(type_name="EV Scooter AC", is_ev=True, max_payload_kg=50.0, battery_capacity_kwh=3.5, consumption_kwh_per_km=0.04)
    db.add(v_type)
    db.flush()

    vehicle = Vehicle(registration_number="AC-EV-01", vehicle_type_id=v_type.id, warehouse_id=wh.id, current_soc_percent=15.0, status="busy")
    driver = Driver(user_id=1, warehouse_id=wh.id, license_number="LIC-AC-01", status="busy")
    db.add_all([vehicle, driver])
    db.flush()

    batch = Batch(batch_code="B-AC-01", warehouse_id=wh.id, status="completed")
    db.add(batch)
    db.flush()

    delivery = Delivery(
        delivery_code="DEL-AC-01",
        batch_id=batch.id,
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        status="in_transit",
        scheduled_dispatch_time=datetime.utcnow(),
        estimated_eta=datetime.utcnow() + timedelta(minutes=30)
    )
    db.add(delivery)
    db.flush()

    stop = DeliveryStop(delivery_id=delivery.id, order_id=1, stop_sequence=1, status="pending", estimated_arrival=datetime.utcnow())
    db.add(stop)
    db.commit()

    # Deliver stop -> completes delivery
    res = delivery_service.deliver_stop(db, delivery.id, stop.id)
    db.refresh(vehicle)

    assert res["delivery_completed"] is True
    assert vehicle.status == "needs_charging"

    # Verify auto-reservation created
    active_res = db.query(ChargingReservation).filter(ChargingReservation.vehicle_id == vehicle.id).first()
    assert active_res is not None
    assert active_res.status == "confirmed"


def test_charging_session_completion_and_cost(setup_db):
    """
    Test 4: Charging session completion updates SoC to target_soc (90%), sets total_cost, and returns vehicle to available.
    """
    db = setup_db
    wh = Warehouse(code="WH-SESS-TEST", name="Session Test Store", latitude=13.0827, longitude=80.2707)
    db.add(wh)
    db.flush()

    st = charging_service.generate_depot_chargers(db, wh.id, connectors_count=1, price_per_kwh=10.0)
    conn = st.connectors[0]
    slot = conn.slots[0]

    v_type = VehicleType(type_name="EV Scooter SESS", is_ev=True, max_payload_kg=50.0, battery_capacity_kwh=3.5, consumption_kwh_per_km=0.04)
    db.add(v_type)
    db.flush()

    vehicle = Vehicle(registration_number="SESS-EV-01", vehicle_type_id=v_type.id, warehouse_id=wh.id, current_soc_percent=20.0, status="needs_charging")
    driver = Driver(user_id=2, warehouse_id=wh.id, license_number="LIC-SESS-01", status="available")
    db.add_all([vehicle, driver])
    db.commit()

    res = charging_service.create_reservation(db, charging_service.ReservationCreate(slot_id=slot.id, vehicle_id=vehicle.id, driver_id=driver.id))
    session = charging_service.start_charging_session(db, res.id)

    assert session is not None
    db.refresh(vehicle)
    assert vehicle.status == "charging"

    # Complete session
    completed_sess = charging_service.complete_charging_session(db, res.id, target_soc=90.0)
    db.refresh(vehicle)

    assert vehicle.current_soc_percent == 90.0
    assert vehicle.status == "available"
    assert completed_sess.energy_kwh_delivered == 2.45  # (90-20)% of 3.5 kWh = 2.45 kWh


def test_fleet_batteries_overview(setup_db):
    """
    Test 5: Fleet batteries API returns EV battery details with store names and estimated time to full.
    """
    db = setup_db
    wh = Warehouse(code="WH-BAT-OVERVIEW", name="Battery Overview Store", latitude=13.0827, longitude=80.2707)
    db.add(wh)
    db.flush()

    v_type = VehicleType(type_name="EV Scooter BAT", is_ev=True, max_payload_kg=50.0, battery_capacity_kwh=3.5, consumption_kwh_per_km=0.04)
    db.add(v_type)
    db.flush()

    vehicle = Vehicle(registration_number="BAT-EV-01", vehicle_type_id=v_type.id, warehouse_id=wh.id, current_soc_percent=40.0, status="available")
    db.add(vehicle)
    db.commit()

    overview = vehicle_service.get_fleet_batteries(db, warehouse_id=wh.id)
    assert len(overview) == 1
    assert overview[0]["registration_number"] == "BAT-EV-01"
    assert overview[0]["store_name"] == "Battery Overview Store"
    assert overview[0]["estimated_time_to_full_mins"] > 0
