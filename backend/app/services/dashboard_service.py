"""Dashboard aggregation service."""
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.warehouse import Warehouse, Inventory
from backend.app.models.order import Order
from backend.app.models.batch import Batch, PickRoute
from backend.app.models.delivery import Delivery
from backend.app.models.safety import SafetyScore, SafetyAlert, SafetyEvent
from backend.app.models.charging import (
    ChargingStation, ChargingConnector, ChargingSession, ChargingReservation
)
from backend.app.schemas.dashboard import (
    WarehouseDashboard, DeliveryDashboard, ChargingDashboard, OverviewDashboard
)


def _today_start():
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def get_warehouse_dashboard(db: Session) -> WarehouseDashboard:
    today = _today_start()
    active_warehouses = db.query(Warehouse).filter(Warehouse.status == "active").count()
    pending_orders = db.query(Order).filter(Order.status == "pending").count()
    active_batches = db.query(Batch).filter(Batch.status.in_(["created", "assigned", "in_progress"])).count()
    orders_completed_today = db.query(Order).filter(
        Order.status == "delivered",
        Order.created_at >= today,
    ).count()

    # Average picking distance
    avg_dist_result = db.query(func.avg(PickRoute.total_distance_meters)).scalar()
    avg_picking_distance = float(avg_dist_result) if avg_dist_result else 0.0

    # Low stock alerts: inventory below reorder_threshold
    low_stock = db.query(Inventory).filter(Inventory.quantity <= Inventory.reorder_threshold).count()

    return WarehouseDashboard(
        active_warehouses=active_warehouses,
        pending_orders=pending_orders,
        active_batches=active_batches,
        orders_completed_today=orders_completed_today,
        avg_picking_distance_m=round(avg_picking_distance, 2),
        batch_utilization_pct=0.0,  # Requires order capacity data — Phase 3
        low_stock_alerts=low_stock,
    )


def get_delivery_dashboard(db: Session) -> DeliveryDashboard:
    today = _today_start()
    active_deliveries = db.query(Delivery).filter(
        Delivery.status.in_(["assigned", "dispatched", "in_transit"])
    ).count()
    completed_today = db.query(Delivery).filter(
        Delivery.status == "completed",
        Delivery.actual_completion_time >= today,
    ).count()

    avg_score_result = db.query(func.avg(SafetyScore.final_score)).scalar()
    avg_safety_score = float(avg_score_result) if avg_score_result else 0.0

    active_alerts = db.query(SafetyAlert).filter(SafetyAlert.is_acknowledged == False).count()

    speeding_today = db.query(SafetyEvent).filter(
        SafetyEvent.event_type == "speeding",
        SafetyEvent.timestamp >= today,
    ).count()
    harsh_braking_today = db.query(SafetyEvent).filter(
        SafetyEvent.event_type == "harsh_braking",
        SafetyEvent.timestamp >= today,
    ).count()

    return DeliveryDashboard(
        active_deliveries=active_deliveries,
        deliveries_completed_today=completed_today,
        avg_safety_score=round(avg_safety_score, 2),
        active_alerts=active_alerts,
        avg_eta_error_minutes=0.0,  # Requires ETA tracking — Phase 3
        speeding_events_today=speeding_today,
        harsh_braking_events_today=harsh_braking_today,
    )


def get_charging_dashboard(db: Session) -> ChargingDashboard:
    today = _today_start()
    operational_stations = db.query(ChargingStation).filter(ChargingStation.status == "operational").count()
    total_connectors = db.query(ChargingConnector).count()
    available_connectors = db.query(ChargingConnector).filter(ChargingConnector.status == "available").count()
    active_sessions = db.query(ChargingSession).filter(ChargingSession.end_time == None).count()
    reservations_today = db.query(ChargingReservation).filter(
        ChargingReservation.created_at >= today,
        ChargingReservation.status != "cancelled",
    ).count()

    utilization_pct = (
        round(100.0 * (total_connectors - available_connectors) / total_connectors, 2)
        if total_connectors > 0 else 0.0
    )

    return ChargingDashboard(
        operational_stations=operational_stations,
        total_connectors=total_connectors,
        available_connectors=available_connectors,
        active_sessions=active_sessions,
        reservations_today=reservations_today,
        avg_wait_minutes=0.0,  # Requires queue prediction — Phase 3
        utilization_pct=utilization_pct,
    )


def get_overview_dashboard(db: Session) -> OverviewDashboard:
    return OverviewDashboard(
        warehouse=get_warehouse_dashboard(db),
        delivery=get_delivery_dashboard(db),
        charging=get_charging_dashboard(db),
        generated_at=datetime.now(timezone.utc),
    )
