from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, ForeignKey, Integer, BigInteger, Numeric, Identity
from backend.app.models.types import TZDateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    batch_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    assigned_picker_id: Mapped[Optional[int]] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    max_orders: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    total_weight_kg: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="created", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)

    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    assigned_picker: Mapped[Optional["User"]] = relationship("User")
    batch_orders: Mapped[List["BatchOrder"]] = relationship("BatchOrder", back_populates="batch", cascade="all, delete-orphan")
    pick_route: Mapped[Optional["PickRoute"]] = relationship("PickRoute", back_populates="batch", uselist=False)
    delivery: Mapped[Optional["Delivery"]] = relationship("Delivery", back_populates="batch", uselist=False)


class BatchOrder(Base):
    __tablename__ = "batch_orders"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    batch_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("orders.id", ondelete="RESTRICT"), unique=True, nullable=False)

    batch: Mapped["Batch"] = relationship("Batch", back_populates="batch_orders")
    order: Mapped["Order"] = relationship("Order", back_populates="batch_association")


class PickRoute(Base):
    __tablename__ = "pick_routes"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    batch_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("batches.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_distance_meters: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    estimated_duration_minutes: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    algorithm_used: Mapped[str] = mapped_column(String(64), default="a_star", nullable=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, nullable=False)

    batch: Mapped["Batch"] = relationship("Batch", back_populates="pick_route")
    steps: Mapped[List["PickRouteStep"]] = relationship("PickRouteStep", back_populates="pick_route", cascade="all, delete-orphan")


class PickRouteStep(Base):
    __tablename__ = "pick_route_steps"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    pick_route_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("pick_routes.id", ondelete="CASCADE"), nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    location_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("storage_locations.id", ondelete="RESTRICT"), nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity_to_pick: Mapped[int] = mapped_column(Integer, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    pick_route: Mapped["PickRoute"] = relationship("PickRoute", back_populates="steps")
    location: Mapped["StorageLocation"] = relationship("StorageLocation")
    product: Mapped["Product"] = relationship("Product")
