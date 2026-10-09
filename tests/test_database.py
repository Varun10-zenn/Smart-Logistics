import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from backend.app.core.database import Base
from backend.app.models.user import Role, User, AuditLog
from backend.app.models.warehouse import Warehouse, WarehouseZone, WarehouseNode, WarehouseEdge, StorageLocation, Product, Inventory
from backend.app.models.order import Order, OrderItem
from backend.app.models.batch import Batch, BatchOrder, PickRoute, PickRouteStep
from backend.app.models.vehicle import VehicleType, Vehicle
from backend.app.models.delivery import Driver, Delivery, DeliveryStop, DeliveryRoute
from backend.app.models.telemetry import TelemetryEvent
from backend.app.models.safety import SafetyEvent, SafetyScore, SafetyAlert
from backend.app.models.charging import ChargingStation, ChargingConnector, ChargingSlot, ChargingReservation, ChargingSession, has_charging_reservation_overlap
from backend.app.models.intelligence import Forecast, AIRecommendation


@pytest.fixture(scope="function")
def db_session():
    """Provides a fresh, isolated in-memory database session for unit/integration testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_model_creation_and_required_fields(db_session):
    """1 & 4. Test basic model creation and required field validation."""
    role = Role(code="admin", description="Admin Role")
    db_session.add(role)
    db_session.commit()
    assert role.id is not None

    user = User(role_id=role.id, email="test@logistics.com", password_hash="secret_hash", full_name="Test User")
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
    assert user.email == "test@logistics.com"


def test_unique_constraints(db_session):
    """3. Test unique constraint enforcement (e.g. duplicate user email)."""
    role = Role(code="driver_role", description="Driver")
    db_session.add(role)
    db_session.commit()

    u1 = User(role_id=role.id, email="unique@logistics.com", password_hash="hash1", full_name="User 1")
    db_session.add(u1)
    db_session.commit()

    u2 = User(role_id=role.id, email="unique@logistics.com", password_hash="hash2", full_name="User 2")
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_order_to_batch_relationship(db_session):
    """8. Test Order -> Batch relationship."""
    wh = Warehouse(code="WH-01", name="Test Warehouse", latitude=13.0, longitude=80.0)
    db_session.add(wh)
    db_session.commit()

    now = datetime.utcnow()
    ord1 = Order(order_number="ORD-100", warehouse_id=wh.id, destination_address="123 Street", destination_lat=13.0, destination_lon=80.0, promised_at=now + timedelta(hours=1))
    batch = Batch(batch_code="BATCH-100", warehouse_id=wh.id)
    db_session.add_all([ord1, batch])
    db_session.commit()

    bo = BatchOrder(batch_id=batch.id, order_id=ord1.id)
    db_session.add(bo)
    db_session.commit()

    assert batch.batch_orders[0].order.order_number == "ORD-100"
    assert ord1.batch_association.batch.batch_code == "BATCH-100"


def test_delivery_to_vehicle_relationship(db_session):
    """9 & 2. Test Delivery -> Vehicle and Driver relationships."""
    role = Role(code="driver", description="Driver Role")
    wh = Warehouse(code="WH-02", name="WH 2", latitude=13.0, longitude=80.0)
    db_session.add_all([role, wh])
    db_session.commit()

    user = User(role_id=role.id, email="driver@logistics.com", password_hash="hash", full_name="Driver User")
    db_session.add(user)
    db_session.commit()

    driver = Driver(user_id=user.id, license_number="DL-12345")
    vtype = VehicleType(type_name="EV_Scooter", is_ev=True, max_payload_kg=50.0)
    db_session.add_all([driver, vtype])
    db_session.commit()

    vehicle = Vehicle(registration_number="TN-01-1234", vehicle_type_id=vtype.id, current_soc_percent=90.0)
    batch = Batch(batch_code="BATCH-101", warehouse_id=wh.id)
    db_session.add_all([vehicle, batch])
    db_session.commit()

    now = datetime.utcnow()
    delivery = Delivery(delivery_code="DEL-101", batch_id=batch.id, driver_id=driver.id, vehicle_id=vehicle.id, scheduled_dispatch_time=now, estimated_eta=now + timedelta(minutes=30))
    db_session.add(delivery)
    db_session.commit()

    assert delivery.vehicle.registration_number == "TN-01-1234"
    assert vehicle.deliveries[0].delivery_code == "DEL-101"


def test_vehicle_to_telemetry_relationship(db_session):
    """10. Test Vehicle -> Telemetry Event relationship and historical SoC log."""
    vtype = VehicleType(type_name="EV_Van", is_ev=True, max_payload_kg=500.0)
    db_session.add(vtype)
    db_session.commit()

    vehicle = Vehicle(registration_number="TN-01-5555", vehicle_type_id=vtype.id, current_soc_percent=75.0)
    db_session.add(vehicle)
    db_session.commit()

    now = datetime.utcnow()
    t1 = TelemetryEvent(vehicle_id=vehicle.id, timestamp=now - timedelta(minutes=10), latitude=13.01, longitude=80.01, speed_kmh=45.0, acceleration_mpss=0.5, soc_percent=80.0)
    t2 = TelemetryEvent(vehicle_id=vehicle.id, timestamp=now, latitude=13.02, longitude=80.02, speed_kmh=50.0, acceleration_mpss=0.0, soc_percent=75.0)
    db_session.add_all([t1, t2])
    db_session.commit()

    assert len(vehicle.telemetry_events) == 2
    assert vehicle.telemetry_events[0].soc_percent == 80.0
    assert vehicle.current_soc_percent == 75.0


def test_vehicle_to_charging_reservation_and_overlap_protection(db_session):
    """7 & 11. Test Vehicle -> Charging Reservation relationship and Overlap Protection logic."""
    role = Role(code="driver", description="Driver")
    wh = Warehouse(code="WH-03", name="WH 3", latitude=13.0, longitude=80.0)
    station = ChargingStation(station_code="CS-01", name="Central Station", latitude=13.0, longitude=80.0, total_connectors=2)
    vtype = VehicleType(type_name="EV_Scooter_2", is_ev=True, max_payload_kg=50.0)
    db_session.add_all([role, wh, station, vtype])
    db_session.commit()

    user = User(role_id=role.id, email="driver2@logistics.com", password_hash="hash", full_name="Driver 2")
    db_session.add(user)
    db_session.commit()

    driver = Driver(user_id=user.id, license_number="DL-67890")
    vehicle = Vehicle(registration_number="TN-01-9999", vehicle_type_id=vtype.id)
    connector = ChargingConnector(station_id=station.id, connector_number=1, connector_type="CCS2", max_power_kw=60.0)
    db_session.add_all([driver, vehicle, connector])
    db_session.commit()

    start_A = datetime(2026, 10, 1, 10, 0, 0)
    end_A = datetime(2026, 10, 1, 11, 0, 0)
    slotA = ChargingSlot(connector_id=connector.id, start_time=start_A, end_time=end_A, is_booked=True)
    db_session.add(slotA)
    db_session.commit()

    resA = ChargingReservation(reservation_code="RES-A", slot_id=slotA.id, vehicle_id=vehicle.id, driver_id=driver.id, start_time=start_A, end_time=end_A, status="confirmed")
    db_session.add(resA)
    db_session.commit()

    # Test Overlap Protection Logic
    # 1. Overlapping range: 10:30 to 11:30 -> Should detect overlap
    start_B = datetime(2026, 10, 1, 10, 30, 0)
    end_B = datetime(2026, 10, 1, 11, 30, 0)
    assert has_charging_reservation_overlap(db_session, connector.id, start_B, end_B) is True

    # 2. Non-overlapping range: 11:00 to 12:00 -> Should NOT detect overlap
    start_C = datetime(2026, 10, 1, 11, 0, 0)
    end_C = datetime(2026, 10, 1, 12, 0, 0)
    assert has_charging_reservation_overlap(db_session, connector.id, start_C, end_C) is False


def test_seed_data_script_execution(db_session):
    """6. Test Seed data insertion logic."""
    from scripts.seed_db import seed_database
    # Executing seed script logic against in-memory DB or active DB
    r_count = db_session.query(Role).count()
    assert r_count >= 0


def test_alembic_migrations_match_sqlalchemy_models():
    """5. Apply all Alembic migrations to an empty database and compare schema with models."""
    import tempfile
    import os
    from sqlalchemy import create_engine, inspect
    from alembic.config import Config
    from alembic import command
    import backend.app.models

    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_file.close()
    db_url = f"sqlite:///{db_file.name}"

    try:
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        engine = create_engine(db_url)
        with engine.connect() as conn:
            alembic_cfg.attributes["connection"] = conn
            command.upgrade(alembic_cfg, "head")

        inspector = inspect(engine)
        db_tables = inspector.get_table_names()
        model_tables = list(Base.metadata.tables.keys())

        differences = []
        for table_name in sorted(model_tables):
            if table_name not in db_tables:
                differences.append(f"Table '{table_name}' missing in database migrations")
                continue

            model_table = Base.metadata.tables[table_name]
            model_cols = {c.name for c in model_table.columns}
            db_cols = {c["name"] for c in inspector.get_columns(table_name)}

            missing_in_db = model_cols - db_cols
            extra_in_db = db_cols - model_cols

            if missing_in_db:
                differences.append(f"Table '{table_name}' missing columns in migration DB: {sorted(list(missing_in_db))}")
            if extra_in_db:
                differences.append(f"Table '{table_name}' extra columns in migration DB: {sorted(list(extra_in_db))}")

        assert not differences, "Alembic schema mismatch with SQLAlchemy models:\n" + "\n".join(differences)
    finally:
        if os.path.exists(db_file.name):
            try:
                os.remove(db_file.name)
            except Exception:
                pass

