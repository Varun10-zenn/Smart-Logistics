from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, BigInteger, Integer, Numeric, Index, Identity
from backend.app.models.types import TZDateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base


class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    delivery_id: Mapped[Optional[int]] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("deliveries.id", ondelete="SET NULL"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(10, 8), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(11, 8), nullable=False)
    speed_kmh: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    acceleration_mpss: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    soc_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    heading_degrees: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="telemetry_events")
    delivery: Mapped[Optional["Delivery"]] = relationship("Delivery")

    __table_args__ = (
        Index("idx_telemetry_vehicle_time", "vehicle_id", "timestamp"),
        Index("idx_telemetry_lat_lon", "latitude", "longitude"),
    )
