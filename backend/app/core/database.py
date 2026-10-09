import logging
import time
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Determine engine from settings
db_url = settings.DATABASE_URL

if db_url.startswith("sqlite"):
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    """FastAPI Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connectivity() -> dict:
    """
    Check database connectivity against configured engine.
    Does NOT silently fall back to SQLite when the primary database fails.
    """
    start_time = time.time()
    active_url = str(engine.url)

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.time() - start_time) * 1000, 2)
        dialect = engine.dialect.name
        return {
            "status": "connected",
            "database_type": dialect,
            "url": active_url.split("@")[-1] if "@" in active_url else active_url,
            "latency_ms": latency_ms,
            "error": None
        }
    except Exception as err:
        logger.error(f"Database connection failed: {err}")
        return {
            "status": "disconnected",
            "database_type": engine.dialect.name,
            "url": active_url.split("@")[-1] if "@" in active_url else active_url,
            "latency_ms": None,
            "error": str(err)
        }

