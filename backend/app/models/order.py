from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, ForeignKey, Integer, BigInteger, Numeric, Index, Identity
from backend.app.models.types import TZDateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    order_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    customer_id: Mapped[Optional[int]] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    destination_address: Mapped[str] = mapped_column(Text, nullable=False)
    destination_lat: Mapped[float] = mapped_column(Numeric(10, 8), nullable=False)
    destination_lon: Mapped[float] = mapped_column(Numeric(11, 8), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, nullable=False)
    promised_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)

    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="orders")
    customer_user: Mapped[Optional["User"]] = relationship("User")
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    batch_association: Mapped[Optional["BatchOrder"]] = relationship("BatchOrder", back_populates="order", uselist=False)

    __table_args__ = (
        Index("idx_orders_dest_lat_lon", "destination_lat", "destination_lon"),
        Index("idx_orders_status_wh", "status", "warehouse_id"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")
