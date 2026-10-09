"""
Phase 2 API v1 router — aggregates all domain sub-routers.
All application endpoints live under /api/v1/
"""
from fastapi import APIRouter

from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.users import router as users_router
from backend.app.api.v1.warehouses import router as warehouses_router
from backend.app.api.v1.products import router as products_router
from backend.app.api.v1.inventory import router as inventory_router
from backend.app.api.v1.orders import router as orders_router
from backend.app.api.v1.batches import router as batches_router
from backend.app.api.v1.picking import router as picking_router, steps_router as pick_steps_router
from backend.app.api.v1.shop import router as shop_router
from backend.app.api.v1.deliveries import router as deliveries_router
from backend.app.api.v1.drivers import router as drivers_router
from backend.app.api.v1.vehicles import router as vehicles_router
from backend.app.api.v1.telemetry import router as telemetry_router
from backend.app.api.v1.safety import router as safety_router
from backend.app.api.v1.charging import router as charging_router
from backend.app.api.v1.intelligence import router as intelligence_router
from backend.app.api.v1.audit import router as audit_router
from backend.app.api.v1.dashboard import router as dashboard_router

api_router = APIRouter(prefix="/api/v1")

# Health (also mounted at root /health in main.py)
api_router.include_router(health_router)

# Auth
api_router.include_router(auth_router)

# Platform
api_router.include_router(users_router)

# Warehouse & Shop
api_router.include_router(warehouses_router)
api_router.include_router(products_router)
api_router.include_router(inventory_router)
api_router.include_router(orders_router)
api_router.include_router(batches_router)
api_router.include_router(picking_router)
api_router.include_router(pick_steps_router)
api_router.include_router(shop_router)

# Delivery & Fleet
api_router.include_router(deliveries_router)
api_router.include_router(drivers_router)
api_router.include_router(vehicles_router)
api_router.include_router(telemetry_router)
api_router.include_router(safety_router)

# EV Charging
api_router.include_router(charging_router)

# Intelligence & Audit
api_router.include_router(intelligence_router)
api_router.include_router(audit_router)
api_router.include_router(dashboard_router)
