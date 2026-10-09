from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, ForeignKey, Integer, BigInteger, Numeric, Index, Identity
from backend.app.models.types import TZDateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    warehouse_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True, index=True)
    license_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=5.00, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="available", nullable=False, index=True)

    user: Mapped["User"] = relationship("User", back_populates="driver")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    deliveries: Mapped[List["Delivery"]] = relationship("Delivery", back_populates="driver")


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    delivery_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    batch_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False)
    driver_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False)
    vehicle_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="assigned", nullable=False, index=True)
    scheduled_dispatch_time: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    actual_dispatch_time: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)
    estimated_eta: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    actual_completion_time: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)
    charging_recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, nullable=False)

    batch: Mapped["Batch"] = relationship("Batch", back_populates="delivery")
    driver: Mapped["Driver"] = relationship("Driver", back_populates="deliveries")
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="deliveries")
    stops: Mapped[List["DeliveryStop"]] = relationship("DeliveryStop", back_populates="delivery", cascade="all, delete-orphan")
    route: Mapped[Optional["DeliveryRoute"]] = relationship("DeliveryRoute", back_populates="delivery", uselist=False)
    safety_events: Mapped[List["SafetyEvent"]] = relationship("SafetyEvent", back_populates="delivery", cascade="all, delete-orphan")
    safety_score: Mapped[Optional["SafetyScore"]] = relationship("SafetyScore", back_populates="delivery", uselist=False)
    safety_alerts: Mapped[List["SafetyAlert"]] = relationship("SafetyAlert", back_populates="delivery", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_deliveries_status_driver", "status", "driver_id"),
    )


class DeliveryStop(Base):
    __tablename__ = "delivery_stops"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    delivery_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False)
    stop_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    estimated_arrival: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    actual_arrival: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)

    delivery: Mapped["Delivery"] = relationship("Delivery", back_populates="stops")
    order: Mapped["Order"] = relationship("Order")


class DeliveryRoute(Base):
    __tablename__ = "delivery_routes"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    delivery_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("deliveries.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_distance_km: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    estimated_travel_minutes: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    traffic_factor: Mapped[float] = mapped_column(Numeric(4, 2), default=1.00, nullable=False)
    weather_factor: Mapped[float] = mapped_column(Numeric(4, 2), default=1.00, nullable=False)
    route_geometry: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    route_source: Mapped[Optional[str]] = mapped_column(String(32), default="haversine_fallback", nullable=True)

    delivery: Mapped["Delivery"] = relationship("Delivery", back_populates="route")

