from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, ForeignKey, Integer, BigInteger, Numeric, Index, Identity
from backend.app.models.types import TZDateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base


class VehicleType(Base):
    __tablename__ = "vehicle_types"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    type_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    is_ev: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_payload_kg: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    battery_capacity_kwh: Mapped[float] = mapped_column(Numeric(6, 2), default=0.0, nullable=False)
    consumption_kwh_per_km: Mapped[float] = mapped_column(Numeric(5, 3), default=0.0, nullable=False)

    vehicles: Mapped[List["Vehicle"]] = relationship("Vehicle", back_populates="vehicle_type")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    registration_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    vehicle_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("vehicle_types.id", ondelete="RESTRICT"), nullable=False)
    warehouse_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True, index=True)
    connector_type: Mapped[Optional[str]] = mapped_column(String(32), default="CCS2", nullable=True)
    current_soc_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=100.00, nullable=False)  # 0.00 to 100.00
    status: Mapped[str] = mapped_column(String(32), default="available", nullable=False, index=True)
    last_telemetry_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)

    vehicle_type: Mapped["VehicleType"] = relationship("VehicleType", back_populates="vehicles")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    deliveries: Mapped[List["Delivery"]] = relationship("Delivery", back_populates="vehicle")
    telemetry_events: Mapped[List["TelemetryEvent"]] = relationship("TelemetryEvent", back_populates="vehicle", cascade="all, delete-orphan")
    charging_reservations: Mapped[List["ChargingReservation"]] = relationship("ChargingReservation", back_populates="vehicle")

    __table_args__ = (
        Index("idx_vehicles_soc_status", "status", "current_soc_percent"),
    )
