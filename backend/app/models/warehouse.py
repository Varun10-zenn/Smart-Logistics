from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Boolean, ForeignKey, Integer, BigInteger, Numeric, Index, Identity
from backend.app.models.types import TZDateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(10, 8), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(11, 8), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    zones: Mapped[List["WarehouseZone"]] = relationship("WarehouseZone", back_populates="warehouse", cascade="all, delete-orphan")
    nodes: Mapped[List["WarehouseNode"]] = relationship("WarehouseNode", back_populates="warehouse", cascade="all, delete-orphan")
    edges: Mapped[List["WarehouseEdge"]] = relationship("WarehouseEdge", back_populates="warehouse", cascade="all, delete-orphan")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="warehouse")

    __table_args__ = (
        Index("idx_warehouses_lat_lon", "latitude", "longitude"),
    )


class WarehouseZone(Base):
    __tablename__ = "warehouse_zones"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    zone_code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(32), default="standard", nullable=False)

    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="zones")
    nodes: Mapped[List["WarehouseNode"]] = relationship("WarehouseNode", back_populates="zone")


class WarehouseNode(Base):
    __tablename__ = "warehouse_nodes"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    zone_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("warehouse_zones.id", ondelete="SET NULL"), nullable=True)
    node_code: Mapped[str] = mapped_column(String(32), nullable=False)
    x_coord: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    y_coord: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    z_coord: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_depot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="nodes")
    zone: Mapped[Optional["WarehouseZone"]] = relationship("WarehouseZone", back_populates="nodes")
    storage_locations: Mapped[List["StorageLocation"]] = relationship("StorageLocation", back_populates="node")


class WarehouseEdge(Base):
    __tablename__ = "warehouse_edges"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    from_node_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("warehouse_nodes.id", ondelete="CASCADE"), nullable=False)
    to_node_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("warehouse_nodes.id", ondelete="CASCADE"), nullable=False)
    distance_meters: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    is_bidirectional: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="edges")


class StorageLocation(Base):
    __tablename__ = "storage_locations"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    node_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("warehouse_nodes.id", ondelete="CASCADE"), nullable=False)
    location_code: Mapped[str] = mapped_column(String(32), unique=False, nullable=False, index=True)
    aisle: Mapped[str] = mapped_column(String(16), nullable=False)
    shelf: Mapped[str] = mapped_column(String(16), nullable=False)
    bin: Mapped[str] = mapped_column(String(16), nullable=False)
    max_weight_kg: Mapped[float] = mapped_column(Numeric(8, 2), default=100.0, nullable=False)

    node: Mapped["WarehouseNode"] = relationship("WarehouseNode", back_populates="storage_locations")
    inventory_items: Mapped[List["Inventory"]] = relationship("Inventory", back_populates="location")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    unit_weight_kg: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    unit_volume_cbm: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, nullable=False)

    inventory_items: Mapped[List["Inventory"]] = relationship("Inventory", back_populates="product")
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="product")


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    location_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("storage_locations.id", ondelete="RESTRICT"), nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reorder_threshold: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    location: Mapped["StorageLocation"] = relationship("StorageLocation", back_populates="inventory_items")
    product: Mapped["Product"] = relationship("Product", back_populates="inventory_items")
