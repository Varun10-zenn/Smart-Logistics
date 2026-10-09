"""
Dev Database Cleanup Script.
Resets the local development database by dropping all tables, running Alembic migration head,
and seeding ONLY the 6 core roles and 1 admin user.
"""
import sys
import os
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic.config import Config
from alembic import command
from backend.app.core.config import settings
from backend.app.core.database import engine, Base, SessionLocal
from backend.app.models.user import Role, User
from backend.app.core.security import hash_password

ROLES_TO_SEED = [
    ("admin", "Administrator with full system access"),
    ("warehouse_operator", "Warehouse Operator managing inventory and picking"),
    ("fleet_manager", "Fleet Manager managing vehicles and drivers"),
    ("driver", "Delivery Driver handling shipments"),
    ("station_admin", "EV Charging Station Administrator"),
    ("customer", "Customer browsing shop and placing orders"),
]


def reset_dev_db(force: bool = False):
    # Guard: APP_ENV must be 'local'
    if getattr(settings, "APP_ENV", "").lower() != "local":
        print(f"ERROR: Cannot reset database when APP_ENV is '{settings.APP_ENV}'. Must be 'local'.")
        sys.exit(1)

    print("==================================================")
    print("DEV DATABASE CLEANUP UTILITY")
    print(f"Target Database URL: {settings.DATABASE_URL}")
    print("==================================================")
    print("\nWARNING: This script will delete ALL data in the target database:")
    print(" - ALL Warehouses, Nodes, Edges, Locations")
    print(" - ALL Products, Inventory, Orders, Batches")
    print(" - ALL Vehicles, Drivers, Deliveries, Telemetry, Safety Alerts")
    print(" - ALL Users (except the newly created Admin user)")
    print("==================================================")

    if not force:
        print("Error: Confirmation flag --yes is required to execute dev DB reset.")
        print("Usage: python scripts/reset_dev_db.py --yes")
        sys.exit(1)

    print("\n[1/3] Dropping all tables...")
    Base.metadata.drop_all(bind=engine)

    print("[2/3] Re-creating table schema and stamping Alembic version...")
    Base.metadata.create_all(bind=engine)
    alembic_cfg = Config(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alembic.ini"))
    command.stamp(alembic_cfg, "head")

    print("[3/3] Seeding roles and initial admin user...")
    db = SessionLocal()
    try:
        role_objs = {}
        for code, desc in ROLES_TO_SEED:
            role = Role(code=code, description=desc)
            db.add(role)
            db.flush()
            role_objs[code] = role
        db.commit()

        # Admin user credentials
        admin_email = os.getenv("ADMIN_EMAIL", "admin@smartlogistics.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "test1234")
        admin_name = os.getenv("ADMIN_NAME", "System Admin")

        pwd_hash = hash_password(admin_password)
        admin_user = User(
            email=admin_email,
            full_name=admin_name,
            password_hash=pwd_hash,
            role_id=role_objs["admin"].id,
            is_active=True
        )
        db.add(admin_user)
        db.commit()

        print(f"\nSUCCESS! Database reset complete.")
        print(f"Created {len(ROLES_TO_SEED)} roles: {[r[0] for r in ROLES_TO_SEED]}")
        print(f"Created Admin User: {admin_email}")

    except Exception as err:
        db.rollback()
        print(f"ERROR during seeding: {err}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset dev database and seed initial admin user.")
    parser.add_argument("--yes", action="store_true", help="Confirm resetting the dev database.")
    args = parser.parse_args()

    reset_dev_db(force=args.yes)
