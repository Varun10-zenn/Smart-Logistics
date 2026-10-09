from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Boolean, ForeignKey, BigInteger, Integer, Numeric, Index, Identity
from backend.app.models.types import TZDateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base


class SafetyEvent(Base):
    __tablename__ = "safety_events"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    delivery_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)  # speeding, harsh_braking, harsh_acceleration, route_deviation
    severity: Mapped[str] = mapped_column(String(16), nullable=False)    # low, medium, high, critical
    timestamp: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(10, 8), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(11, 8), nullable=False)
    observed_value: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    threshold_value: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    penalty_points: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    delivery: Mapped["Delivery"] = relationship("Delivery", back_populates="safety_events")

    __table_args__ = (
        Index("idx_safety_events_delivery_time", "delivery_id", "timestamp"),
    )


class SafetyScore(Base):
    __tablename__ = "safety_scores"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    delivery_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("deliveries.id", ondelete="CASCADE"), unique=True, nullable=False)
    final_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)  # 100 - penalties
    speed_compliance_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    braking_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    acceleration_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    route_adherence_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, nullable=False)

    delivery: Mapped["Delivery"] = relationship("Delivery", back_populates="safety_score")


class SafetyAlert(Base):
    __tablename__ = "safety_alerts"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    delivery_id: Mapped[Optional[int]] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, nullable=False)

    delivery: Mapped["Delivery"] = relationship("Delivery", back_populates="safety_alerts")
