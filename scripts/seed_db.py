"""Comprehensive seed data script for Smart Logistics Platform."""
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.app.core.database import get_db
from backend.app.models import (
    Role, User, Warehouse, Product, VehicleType, Vehicle,
    Driver, Order, Batch, BatchOrder, Delivery, DeliveryRoute,
    SafetyAlert, ChargingStation, ChargingConnector, ChargingSlot
)
from backend.app.core.security import hash_password

def seed_database():
    db_gen = get_db()
    db = next(db_gen)

    try:
        print("Seeding database...")
        # 1. Roles
        roles = ["admin", "warehouse_operator", "fleet_manager", "driver", "station_admin"]
        role_objs = {}
        for r in roles:
            role = db.query(Role).filter(Role.code == r).first()
            if not role:
                role = Role(code=r, description=f"{r.replace('_', ' ').title()} role")
                db.add(role)
                db.flush()
            role_objs[r] = role
        db.commit()

        # 2. Users
        users_data = [
            ("admin@smartlogistics.com", "Admin User", "admin"),
            ("warehouse@smartlogistics.com", "Warehouse Op", "warehouse_operator"),
            ("fleet@smartlogistics.com", "Fleet Manager", "fleet_manager"),
            ("driver@smartlogistics.com", "Alex Driver", "driver"),
            ("station@smartlogistics.com", "Station Admin", "station_admin"),
        ]
        pwd_hash = hash_password("test1234")
        user_objs = {}
        for email, name, role_code in users_data:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    full_name=name,
                    password_hash=pwd_hash,
                    role_id=role_objs[role_code].id,
                    is_active=True
                )
                db.add(user)
                db.flush()
            user_objs[role_code] = user
        db.commit()

        # 3. Warehouses
        wh1 = db.query(Warehouse).filter(Warehouse.code == "WH-MAIN").first()
        if not wh1:
            wh1 = Warehouse(
                code="WH-MAIN",
                name="Central Fulfilment Hub",
                latitude=12.9716,
                longitude=77.5946,
                address="100 Logistics Way, Tech Park",
                status="active"
            )
            db.add(wh1)
            db.flush()

        wh2 = db.query(Warehouse).filter(Warehouse.code == "WH-NORTH").first()
        if not wh2:
            wh2 = Warehouse(
                code="WH-NORTH",
                name="North Express Depot",
                latitude=13.0827,
                longitude=80.2707,
                address="45 Cargo Highway, North Zone",
                status="active"
            )
            db.add(wh2)
            db.flush()
        db.commit()

        # 4. Products
        p1 = db.query(Product).filter(Product.sku == "PROD-ELEC-001").first()
        if not p1:
            p1 = Product(sku="PROD-ELEC-001", name="Smart IoT Tracker Module", category="Electronics", unit_weight_kg=0.5, unit_volume_cbm=0.002, price=149.99)
            db.add(p1)
            db.flush()

        p2 = db.query(Product).filter(Product.sku == "PROD-MED-002").first()
        if not p2:
            p2 = Product(sku="PROD-MED-002", name="Temperature Controlled Vaccine Box", category="Medical", unit_weight_kg=2.5, unit_volume_cbm=0.015, price=299.00)
            db.add(p2)
            db.flush()
        db.commit()

        # 5. Vehicle Types & Vehicles
        vt = db.query(VehicleType).filter(VehicleType.type_name == "EV Freight Van").first()
        if not vt:
            vt = VehicleType(type_name="EV Freight Van", is_ev=True, max_payload_kg=1200.0, battery_capacity_kwh=80.0)
            db.add(vt)
            db.flush()

        v1 = db.query(Vehicle).filter(Vehicle.registration_number == "EV-LOG-901").first()
        if not v1:
            v1 = Vehicle(registration_number="EV-LOG-901", vehicle_type_id=vt.id, is_ev=True, battery_capacity_kwh=80.0, current_soc_percent=85.5, status="available")
            db.add(v1)
            db.flush()
        db.commit()

        # 6. Driver
        drv = db.query(Driver).filter(Driver.user_id == user_objs["driver"].id).first()
        if not drv:
            drv = Driver(user_id=user_objs["driver"].id, license_number="DL-EV-88219", status="available")
            db.add(drv)
            db.flush()
        db.commit()

        # 7. Orders & Batches
        o1 = db.query(Order).filter(Order.order_number == "ORD-2026-001").first()
        if not o1:
            o1 = Order(
                order_number="ORD-2026-001",
                warehouse_id=wh1.id,
                destination_address="Sector 5, Electronics City",
                destination_lat=12.9352,
                destination_lon=77.6245,
                status="batched",
                priority="urgent",
                promised_at=datetime.now(timezone.utc) + timedelta(hours=4)
            )
            db.add(o1)
            db.flush()

        b1 = db.query(Batch).filter(Batch.batch_code == "BATCH-2026-A1").first()
        if not b1:
            b1 = Batch(batch_code="BATCH-2026-A1", warehouse_id=wh1.id, status="assigned")
            db.add(b1)
            db.flush()
            bo = BatchOrder(batch_id=b1.id, order_id=o1.id)
            db.add(bo)
        db.commit()

        # 8. Deliveries & Delivery Routes
        deliv = db.query(Delivery).filter(Delivery.delivery_code == "DEL-2026-8801").first()
        if not deliv:
            deliv = Delivery(
                delivery_code="DEL-2026-8801",
                batch_id=b1.id,
                driver_id=drv.id,
                vehicle_id=v1.id,
                status="in_transit",
                scheduled_dispatch_time=datetime.now(timezone.utc) - timedelta(minutes=45),
                actual_dispatch_time=datetime.now(timezone.utc) - timedelta(minutes=40),
                estimated_eta=datetime.now(timezone.utc) + timedelta(minutes=35)
            )
            db.add(deliv)
            db.flush()
            route = DeliveryRoute(
                delivery_id=deliv.id,
                total_distance_km=18.4,
                estimated_travel_minutes=35.0,
                traffic_factor=1.1,
                weather_factor=1.0,
                route_polyline="encoded_stub_polyline"
            )
            db.add(route)
        db.commit()

        # 9. Safety Alerts
        alert1 = db.query(SafetyAlert).filter(SafetyAlert.delivery_id == deliv.id).first()
        if not alert1:
            alert1 = SafetyAlert(
                delivery_id=deliv.id,
                alert_type="sudden_braking",
                severity="medium",
                message="Sudden braking detected near junction (12.4 m/s² deceleration)",
                acknowledged=False
            )
            db.add(alert1)
        db.commit()

        # 10. Charging Stations
        cs1 = db.query(ChargingStation).filter(ChargingStation.station_code == "CS-HUB-01").first()
        if not cs1:
            cs1 = ChargingStation(
                station_code="CS-HUB-01",
                name="Central Depot Fast Charge Station",
                latitude=12.9720,
                longitude=77.5950,
                address="100 Logistics Way, Bay 3",
                status="active"
            )
            db.add(cs1)
            db.flush()

            conn1 = ChargingConnector(charging_station_id=cs1.id, connector_type="CCS2", max_kw=150.0, status="available")
            db.add(conn1)
            db.flush()

            slot1 = ChargingSlot(charging_connector_id=conn1.id, start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc) + timedelta(hours=1), is_booked=False)
            db.add(slot1)
        db.commit()

        print("Database seeded successfully with realistic domain records!")

    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

if __name__ == "__main__":
    seed_database()
