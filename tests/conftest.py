import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.main import app
from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.models.user import Role, User
from backend.app.core.security import hash_password, create_access_token
from backend.app.models.delivery import Driver
from backend.app.models.warehouse import Warehouse, WarehouseNode
from backend.app.models.batch import Batch
from backend.app.models.order import Order
from backend.app.models.vehicle import Vehicle, VehicleType
from backend.app.models.delivery import Delivery, DeliveryRoute, DeliveryStop
from backend.app.models.telemetry import TelemetryEvent
from backend.app.models.safety import SafetyEvent, SafetyScore, SafetyAlert
from backend.app.models.intelligence import AIRecommendation
from datetime import datetime
from sqlalchemy.pool import StaticPool

# 1. Override settings.DATABASE_URL so code under test NEVER accesses dev DB
TEST_DB_FILE = os.path.join(os.path.dirname(__file__), "test.db")
TEST_DB_FILE_POSIX = TEST_DB_FILE.replace("\\", "/")
TEST_SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_FILE_POSIX}"
settings.DATABASE_URL = TEST_SQLALCHEMY_DATABASE_URL

test_engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

import backend.app.core.database
backend.app.core.database.SessionLocal = TestingSessionLocal


def override_get_db():
    """Dependency override to force FastAPI endpoints to use the test database session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Globally apply get_db override for all test executions
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def guard_and_setup_test_db():
    # Guard check: Ensure active DB URL contains "test"
    active_url = settings.DATABASE_URL
    if "test" not in active_url.lower():
        pytest.exit(f"ABORTING TEST RUN: Active DATABASE_URL '{active_url}' does not contain 'test'!", returncode=1)

    # Clean previous test.db if exists
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

    Base.metadata.create_all(bind=test_engine)
    yield
    test_engine.dispose()
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass


@pytest.fixture(scope="function")
def db_session():
    """Provides a fresh database transaction context for each test function."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()

    # Seed base roles
    roles = ["admin", "warehouse_operator", "fleet_manager", "driver", "station_admin", "customer"]
    role_objs = {}
    for r in roles:
        role = Role(code=r, description=f"{r} role")
        db.add(role)
        role_objs[r] = role
    db.commit()

    # Seed base users
    users = {
        "admin": ("admin@smartlogistics.com", "Test Admin"),
        "warehouse_operator": ("warehouse@smartlogistics.com", "Test Warehouse Op"),
        "fleet_manager": ("fleet@smartlogistics.com", "Test Fleet Mgr"),
        "driver": ("driver@smartlogistics.com", "Test Driver"),
        "station_admin": ("station@smartlogistics.com", "Test Station Admin"),
    }

    user_objs = {}
    pwd = hash_password("test1234")
    for r, (email, name) in users.items():
        user = User(
            email=email,
            full_name=name,
            password_hash=pwd,
            role_id=role_objs[r].id,
            is_active=True
        )
        db.add(user)
        user_objs[r] = user
    db.commit()

    driver_user = user_objs["driver"]
    driver = Driver(user_id=driver_user.id, license_number="DL-TEST-001", status="available")
    db.add(driver)

    # Seed initial test warehouse, node (depot), order, vehicle
    warehouse = Warehouse(code="WH-PH4", name="Phase 4 Warehouse", latitude=13.0, longitude=80.0, status="active")
    db.add(warehouse)
    db.flush()

    user_objs["warehouse_operator"].warehouse_id = warehouse.id
    db.flush()

    depot_node = WarehouseNode(warehouse_id=warehouse.id, node_code="N-DEPOT-PH4", x_coord=0.0, y_coord=0.0, is_depot=True)
    db.add(depot_node)
    db.flush()

    batch = Batch(batch_code="B-001", warehouse_id=warehouse.id)
    db.add(batch)
    db.flush()

    order = Order(
        order_number="ORD-001",
        warehouse_id=warehouse.id,
        destination_address="Test Address",
        destination_lat=13.1,
        destination_lon=80.1,
        status="pending",
        promised_at=datetime.utcnow()
    )
    db.add(order)
    db.flush()

    from backend.app.models.batch import BatchOrder
    batch_order = BatchOrder(batch_id=batch.id, order_id=order.id)
    db.add(batch_order)
    db.flush()

    vtype = VehicleType(type_name="EV-Van", is_ev=True, max_payload_kg=500.0)
    db.add(vtype)
    db.flush()

    vehicle = Vehicle(registration_number="TN-99-9999", vehicle_type_id=vtype.id, current_soc_percent=100.0)
    db.add(vehicle)

    db.commit()

    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    yield TestClient(app)


def _get_token(db, role_code):
    user = db.query(User).join(Role).filter(Role.code == role_code).first()
    return create_access_token(data={"sub": str(user.id), "role": role_code})


@pytest.fixture
def admin_headers(db_session):
    token = _get_token(db_session, "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def warehouse_op_headers(db_session):
    token = _get_token(db_session, "warehouse_operator")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def fleet_manager_headers(db_session):
    token = _get_token(db_session, "fleet_manager")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def driver_headers(db_session):
    token = _get_token(db_session, "driver")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def station_admin_headers(db_session):
    token = _get_token(db_session, "station_admin")
    return {"Authorization": f"Bearer {token}"}

