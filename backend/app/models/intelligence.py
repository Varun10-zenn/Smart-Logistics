from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Boolean, ForeignKey, Integer, BigInteger, Numeric, JSON, Identity
from backend.app.models.types import TZDateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    forecast_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # demand_hourly, charging_queue
    warehouse_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    station_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("charging_stations.id", ondelete="SET NULL"), nullable=True)
    target_timestamp: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, index=True)
    predicted_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    lower_bound: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    upper_bound: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, nullable=False)

    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    station: Mapped[Optional["ChargingStation"]] = relationship("ChargingStation")


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # warehouse_agent, ev_charging_agent, delivery_agent
    recommendation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 3), nullable=True)  # 0.000 to 1.000
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, nullable=False, index=True)
