from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, ForeignKey, Integer, BigInteger, Numeric, Index, select, Identity
from backend.app.models.types import TZDateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base


class ChargingStation(Base):
    __tablename__ = "charging_stations"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    station_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(10, 8), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(11, 8), nullable=False)
    total_connectors: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="operational", nullable=False)
    warehouse_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True, index=True)
    is_depot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    connectors: Mapped[List["ChargingConnector"]] = relationship("ChargingConnector", back_populates="station", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_stations_lat_lon", "latitude", "longitude"),
    )


class ChargingConnector(Base):
    __tablename__ = "charging_connectors"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    station_id: Mapped[int] = mapped_column(Integer, ForeignKey("charging_stations.id", ondelete="CASCADE"), nullable=False)
    connector_number: Mapped[int] = mapped_column(Integer, nullable=False)
    connector_type: Mapped[str] = mapped_column(String(32), nullable=False)  # CCS2, Type2, GB_T, CHAdeMO
    max_power_kw: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    price_per_kwh: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="available", nullable=False)

    station: Mapped["ChargingStation"] = relationship("ChargingStation", back_populates="connectors")
    slots: Mapped[List["ChargingSlot"]] = relationship("ChargingSlot", back_populates="connector", cascade="all, delete-orphan")
    sessions: Mapped[List["ChargingSession"]] = relationship("ChargingSession", back_populates="connector")


class ChargingSlot(Base):
    __tablename__ = "charging_slots"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    connector_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("charging_connectors.id", ondelete="CASCADE"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    is_booked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    connector: Mapped["ChargingConnector"] = relationship("ChargingConnector", back_populates="slots")
    reservation: Mapped[Optional["ChargingReservation"]] = relationship("ChargingReservation", back_populates="slot", uselist=False)

    __table_args__ = (
        Index("idx_slots_connector_time", "connector_id", "start_time", "end_time"),
    )


class ChargingReservation(Base):
    __tablename__ = "charging_reservations"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    reservation_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    slot_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("charging_slots.id", ondelete="RESTRICT"), unique=True, nullable=False)
    vehicle_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False)
    driver_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False)
    delivery_id: Mapped[Optional[int]] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("deliveries.id", ondelete="SET NULL"), nullable=True)
    start_time: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="confirmed", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, nullable=False)

    slot: Mapped["ChargingSlot"] = relationship("ChargingSlot", back_populates="reservation")
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="charging_reservations")
    driver: Mapped["Driver"] = relationship("Driver")
    delivery: Mapped[Optional["Delivery"]] = relationship("Delivery")
    session: Mapped[Optional["ChargingSession"]] = relationship("ChargingSession", back_populates="reservation", uselist=False)


class ChargingSession(Base):
    __tablename__ = "charging_sessions"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    reservation_id: Mapped[Optional[int]] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("charging_reservations.id", ondelete="SET NULL"), unique=True, nullable=True)
    connector_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("charging_connectors.id", ondelete="RESTRICT"), nullable=False)
    vehicle_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)
    initial_soc_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    final_soc_percent: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    energy_kwh_delivered: Mapped[float] = mapped_column(Numeric(6, 2), default=0.0, nullable=False)
    total_cost: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), default=0.0, nullable=True)

    reservation: Mapped[Optional["ChargingReservation"]] = relationship("ChargingReservation", back_populates="session")
    connector: Mapped["ChargingConnector"] = relationship("ChargingConnector", back_populates="sessions")
    vehicle: Mapped["Vehicle"] = relationship("Vehicle")


def has_charging_reservation_overlap(db, connector_id: int, start_time: datetime, end_time: datetime, exclude_reservation_id: Optional[int] = None) -> bool:
    """
    Transactional Overlap Protection:
    Returns True if an active reservation already exists on the same connector
    whose time interval [start_time, end_time] overlaps with the target range.
    
    Two intervals [A_start, A_end] and [B_start, B_end] overlap if:
      A_start < B_end AND A_end > B_start
    """
    stmt = (
        select(ChargingReservation)
        .join(ChargingSlot, ChargingReservation.slot_id == ChargingSlot.id)
        .where(ChargingSlot.connector_id == connector_id)
        .where(ChargingReservation.status.in_(["confirmed", "active"]))
        .where(ChargingReservation.start_time < end_time)
        .where(ChargingReservation.end_time > start_time)
    )
    if exclude_reservation_id is not None:
        stmt = stmt.where(ChargingReservation.id != exclude_reservation_id)
    
    existing = db.execute(stmt).scalars().first()
    return existing is not None
