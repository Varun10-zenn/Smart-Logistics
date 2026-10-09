"""Dashboard summary schemas."""
from datetime import datetime
from pydantic import BaseModel


class WarehouseDashboard(BaseModel):
    active_warehouses: int
    pending_orders: int
    active_batches: int
    orders_completed_today: int
    avg_picking_distance_m: float
    batch_utilization_pct: float
    low_stock_alerts: int


class DeliveryDashboard(BaseModel):
    active_deliveries: int
    deliveries_completed_today: int
    avg_safety_score: float
    active_alerts: int
    avg_eta_error_minutes: float
    speeding_events_today: int
    harsh_braking_events_today: int


class ChargingDashboard(BaseModel):
    operational_stations: int
    total_connectors: int
    available_connectors: int
    active_sessions: int
    reservations_today: int
    avg_wait_minutes: float
    utilization_pct: float


class OverviewDashboard(BaseModel):
    warehouse: WarehouseDashboard
    delivery: DeliveryDashboard
    charging: ChargingDashboard
    generated_at: datetime
