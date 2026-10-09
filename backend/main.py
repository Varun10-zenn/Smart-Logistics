"""
Smart Logistics Platform — FastAPI Application Entry Point
Phase 2: Core Platform APIs & RBAC Authentication
"""
import logging

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.middleware import RequestIDMiddleware, register_exception_handlers
from backend.app.api.v1 import api_router
from backend.app.api.v1.health import router as health_router
from backend.app.services.auto_batch_scheduler import auto_batch_scheduler_loop

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Startup validation: Ensure DEV_AUTH_BYPASS is strictly limited to local environment
if settings.DEV_AUTH_BYPASS and settings.APP_ENV != "local":
    raise RuntimeError(
        f"CRITICAL CONFIGURATION ERROR: DEV_AUTH_BYPASS=True is strictly prohibited when APP_ENV='{settings.APP_ENV}'. "
        "DEV_AUTH_BYPASS is allowed ONLY when APP_ENV='local'."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run backfill for active deliveries missing route geometry on startup
    if settings.APP_ENV != "test":
        try:
            from backend.app.core.database import SessionLocal
            from backend.app.services.delivery_service import backfill_missing_route_geometries
            db = SessionLocal()
            try:
                backfill_missing_route_geometries(db)
            finally:
                db.close()
        except Exception as ex:
            logger.warning(f"Startup route geometry backfill failed: {ex}")

    # Start auto-batching task on startup if enabled and not in test mode
    bg_task = None
    if settings.AUTO_BATCH_ENABLED and settings.APP_ENV != "test":
        bg_task = asyncio.create_task(auto_batch_scheduler_loop())
    yield
    if bg_task:
        bg_task.cancel()
        try:
            await bg_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-Driven Smart Logistics Platform for Warehouse Optimization, "
        "Delivery Safety, and EV Charging Management.\n\n"
        "**Phase 2:** Core Platform APIs & RBAC Authentication\n\n"
        "All authenticated endpoints require a Bearer JWT access token obtained from `POST /api/v1/auth/login`."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(RequestIDMiddleware)

origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global exception handlers (standardized error envelope)
# ---------------------------------------------------------------------------
register_exception_handlers(app)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
# Health at root level (preserves Phase 0/1 /health and /health/db)
app.include_router(health_router)

# All v1 routes under /api/v1/
app.include_router(api_router)


@app.get("/", tags=["Root"])
def read_root():
    return {
        "name": settings.APP_NAME,
        "version": "2.0.0",
        "phase": "Phase 2 — Core Platform APIs & RBAC Authentication",
        "docs": "/docs",
        "health": "/health",
        "api_v1": "/api/v1",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
