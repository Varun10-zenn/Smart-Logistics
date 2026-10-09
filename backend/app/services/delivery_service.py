"""Delivery service."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.delivery import Delivery, Driver, DeliveryRoute
from backend.app.models.batch import Batch
from backend.app.schemas.common import make_page
from backend.app.schemas.delivery import DeliveryCreate, DeliveryRead, DeliveryStatusUpdate, ETAResponse


def _to_read(d: Delivery) -> DeliveryRead:
    return DeliveryRead(
        id=d.id,
        delivery_code=d.delivery_code,
        batch_id=d.batch_id,
        driver_id=d.driver_id,
        vehicle_id=d.vehicle_id,
        status=d.status,
        scheduled_dispatch_time=d.scheduled_dispatch_time,
        estimated_eta=d.estimated_eta,
        created_at=d.created_at,
    )


def list_deliveries(db: Session, page: int = 1, page_size: int = 20,
                    driver_id: int = None, status: str = None):
    q = db.query(Delivery)
    if driver_id:
        q = q.filter(Delivery.driver_id == driver_id)
    if status:
        q = q.filter(Delivery.status == status)
    total = q.count()
    deliveries = q.order_by(Delivery.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_to_read(d) for d in deliveries], total, page, page_size)


def create_delivery(db: Session, data: DeliveryCreate) -> DeliveryRead:
    batch = db.query(Batch).filter(Batch.id == data.batch_id).first()
    if batch is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Batch not found.", "details": {}})
    driver = db.query(Driver).filter(Driver.id == data.driver_id).first()
    if driver is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Driver not found.", "details": {}})
    if driver.status != "available":
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": "Driver is not available.", "details": {}})
        
    from backend.app.models.vehicle import Vehicle
    vehicle = db.query(Vehicle).filter(Vehicle.id == data.vehicle_id).first()
    if vehicle is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Vehicle not found.", "details": {}})
        
    active_delivery = db.query(Delivery).filter(Delivery.vehicle_id == vehicle.id, Delivery.status.in_(["assigned", "dispatched", "in_transit", "charging_stop"])).first()
    if active_delivery:
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": "Vehicle is already in use.", "details": {}})

    driver.status = "assigned"

    now = datetime.now(timezone.utc)
    dispatch_time = data.scheduled_dispatch_time or now
    eta = dispatch_time + timedelta(hours=2)  # placeholder ETA

    code = f"DEL-{uuid.uuid4().hex[:8].upper()}"
    delivery = Delivery(
        delivery_code=code,
        batch_id=data.batch_id,
        driver_id=data.driver_id,
        vehicle_id=data.vehicle_id,
        status="assigned",
        scheduled_dispatch_time=dispatch_time,
        estimated_eta=eta,
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    return _to_read(delivery)


def get_delivery(db: Session, delivery_id: int) -> DeliveryRead:
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if d is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Delivery not found.", "details": {}})
    return _to_read(d)


def update_delivery_status(db: Session, delivery_id: int, data: DeliveryStatusUpdate) -> DeliveryRead:
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if d is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Delivery not found.", "details": {}})
    d.status = data.status
    if data.status in ("completed", "failed"):
        d.actual_completion_time = datetime.now(timezone.utc)
        if d.driver:
            d.driver.status = "available"
        if d.vehicle:
            from backend.app.core.config import settings
            low_soc_threshold = getattr(settings, "LOW_SOC_THRESHOLD", 25.0)
            is_ev = d.vehicle.vehicle_type and d.vehicle.vehicle_type.is_ev
            if is_ev and float(d.vehicle.current_soc_percent) < low_soc_threshold:
                d.vehicle.status = "needs_charging"
            else:
                d.vehicle.status = "available"
    # Update route factors if provided
    if d.route and (data.traffic_factor or data.weather_factor):
        if data.traffic_factor:
            d.route.traffic_factor = data.traffic_factor
        if data.weather_factor:
            d.route.weather_factor = data.weather_factor
    db.commit()
    db.refresh(d)
    return _to_read(d)


def get_eta(db: Session, delivery_id: int) -> ETAResponse:
    """Return ETA based on generated route and live telemetry or time-of-day traffic factors."""
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if d is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Delivery not found.", "details": {}})

    route = d.route
    if route is None:
        raise HTTPException(
            status_code=409,
            detail={"code": "ROUTE_NOT_GENERATED", "message": "Route not generated yet", "details": {}}
        )

    base_minutes = float(route.estimated_travel_minutes)
    total_distance_km = float(route.total_distance_km)

    # Check recent telemetry for live average speed
    from backend.app.models.telemetry import TelemetryEvent
    recent_events = (
        db.query(TelemetryEvent)
        .filter(TelemetryEvent.delivery_id == delivery_id)
        .order_by(TelemetryEvent.timestamp.desc())
        .limit(10)
        .all()
    )

    algorithm_name = "time_of_day_traffic_v1"
    traffic_factor = float(route.traffic_factor)
    weather_factor = float(route.weather_factor)

    if recent_events and len(recent_events) >= 2:
        valid_speeds = [float(e.speed_kmh) for e in recent_events if float(e.speed_kmh) > 0.0]
        if valid_speeds:
            avg_speed_kmh = sum(valid_speeds) / len(valid_speeds)
            speed_floor = 15.0  # minimum speed floor km/h
            effective_speed = max(avg_speed_kmh, speed_floor)
            # Estimate remaining travel minutes
            remaining_minutes = (total_distance_km / effective_speed) * 60.0 * weather_factor
            algorithm_name = "live_telemetry_v1"
            now_time = datetime.utcnow()
            eta = now_time + timedelta(minutes=remaining_minutes)
            return ETAResponse(
                delivery_id=delivery_id,
                eta=eta,
                base_route_minutes=base_minutes,
                traffic_factor=traffic_factor,
                weather_factor=weather_factor,
                algorithm=algorithm_name,
                confidence=0.9,
            )

    # Before telemetry: use time-of-day traffic factor
    from backend.app.core.config import settings
    now_hour = datetime.utcnow().hour
    am_start, am_end = getattr(settings, "PEAK_HOURS_AM", (8, 10))
    pm_start, pm_end = getattr(settings, "PEAK_HOURS_PM", (17, 20))
    if (am_start <= now_hour < am_end) or (pm_start <= now_hour < pm_end):
        tod_factor = getattr(settings, "PEAK_TRAFFIC_FACTOR", 1.4)
    else:
        tod_factor = getattr(settings, "OFF_PEAK_TRAFFIC_FACTOR", 1.1)

    traffic_factor = tod_factor
    adjusted_minutes = base_minutes * traffic_factor * weather_factor

    dispatch = d.actual_dispatch_time or d.scheduled_dispatch_time or datetime.utcnow()
    eta = dispatch + timedelta(minutes=adjusted_minutes)

    return ETAResponse(
        delivery_id=delivery_id,
        eta=eta,
        base_route_minutes=base_minutes,
        traffic_factor=traffic_factor,
        weather_factor=weather_factor,
        algorithm=algorithm_name,
        confidence=0.75,
    )


# ─── FLEET GENERATION PER STORE ──────────────────────────────────────────────
def generate_store_fleet(db: Session, warehouse_id: int, riders_count: int, ev_count: int) -> dict:
    from backend.app.models.warehouse import Warehouse
    from backend.app.models.user import User, Role
    from backend.app.models.vehicle import Vehicle, VehicleType

    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Warehouse not found.", "details": {}})

    driver_role = db.query(Role).filter(Role.code == "driver").first()
    if not driver_role:
        driver_role = Role(code="driver", description="Driver Role")
        db.add(driver_role)
        db.flush()

    # Get or create vehicle types
    ev_type = db.query(VehicleType).filter(VehicleType.is_ev == True).first()
    if not ev_type:
        ev_type = VehicleType(type_name="EV Scooter", is_ev=True, max_payload_kg=50.0, battery_capacity_kwh=3.5, consumption_kwh_per_km=0.04)
        db.add(ev_type)
        db.flush()

    ice_type = db.query(VehicleType).filter(VehicleType.is_ev == False).first()
    if not ice_type:
        ice_type = VehicleType(type_name="ICE Bike", is_ev=False, max_payload_kg=60.0, battery_capacity_kwh=0.0, consumption_kwh_per_km=0.0)
        db.add(ice_type)
        db.flush()

    from backend.app.core.security import hash_password
    created_riders = []

    # 1. Create Drivers/Riders
    for i in range(1, riders_count + 1):
        clean_code = wh.code.lower().replace('-', '').replace('_', '')
        email = f"rider{i}.{clean_code}@fleet.com"
        password = f"Fleet#{uuid.uuid4().hex[:8]}"

        user = User(
            email=email,
            full_name=f"Rider {i} ({wh.code})",
            password_hash=hash_password(password),
            role_id=driver_role.id,
            is_active=True
        )
        db.add(user)
        db.flush()

        driver = Driver(
            user_id=user.id,
            warehouse_id=wh.id,
            license_number=f"LIC-{wh.code}-{uuid.uuid4().hex[:6].upper()}",
            rating=5.0,
            status="available"
        )
        db.add(driver)
        created_riders.append({
            "email": email,
            "password": password,
            "full_name": user.full_name,
            "driver_id": driver.id,
            "user_id": user.id
        })

    # 2. Create Vehicles
    created_vehicles_count = 0
    total_vehicles_requested = max(riders_count, ev_count)
    for i in range(1, total_vehicles_requested + 1):
        is_ev = (i <= ev_count)
        v_type = ev_type if is_ev else ice_type
        reg_no = f"{wh.code}-V{i}-{uuid.uuid4().hex[:4].upper()}"

        vehicle = Vehicle(
            registration_number=reg_no,
            vehicle_type_id=v_type.id,
            warehouse_id=wh.id,
            current_soc_percent=100.0 if is_ev else 0.0,
            status="available"
        )
        db.add(vehicle)
        created_vehicles_count += 1

    db.commit()

    # Automatically generate depot chargers for store
    try:
        from backend.app.services import charging_service
        charging_service.generate_depot_chargers(db, wh.id, connectors_count=2, max_power_kw=50.0, price_per_kwh=0.0)
    except Exception as ex:
        pass

    return {
        "warehouse_id": wh.id,
        "warehouse_code": wh.code,
        "riders_created": len(created_riders),
        "vehicles_created": created_vehicles_count,
        "ev_count": ev_count,
        "riders": created_riders
    }


# ─── AUTO HANDOFF & BATCH COMPLETION LOGIC ───────────────────────────────────
def auto_handoff_batch_to_delivery(db: Session, batch_id: int) -> Optional[Delivery]:
    """
    Creates ONE delivery for a completed batch, assigns driver & vehicle,
    and generates the route with per-order delivery stops.
    If no driver/vehicle is free, leaves delivery status as "pending_assignment".
    Idempotent: skips if delivery already exists for this batch.
    """
    from backend.app.models.delivery import DeliveryStop
    from backend.app.models.vehicle import Vehicle
    from backend.app.services import routing_service
    from sqlalchemy import func

    # Check for existing delivery
    existing = db.query(Delivery).filter(Delivery.batch_id == batch_id).first()
    if existing:
        return existing

    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return None

    wh = batch.warehouse
    if not wh:
        return None

    # Calculate estimated distance for EV SoC check
    orders = [bo.order for bo in batch.batch_orders if bo.order]
    if not orders:
        return None

    # Estimate distance (Warehouse depot -> orders -> Warehouse depot)
    curr_lat, curr_lon = float(wh.latitude), float(wh.longitude)
    total_est_dist_km = 0.0
    for o in orders:
        from backend.app.services.routing_service import _haversine_distance
        total_est_dist_km += _haversine_distance(curr_lat, curr_lon, float(o.destination_lat), float(o.destination_lon))
        curr_lat, curr_lon = float(o.destination_lat), float(o.destination_lon)
    total_est_dist_km += _haversine_distance(curr_lat, curr_lon, float(wh.latitude), float(wh.longitude))

    # Find available driver of warehouse with fewest completed deliveries today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    driver_subq = (
        db.query(
            Driver.id,
            func.count(Delivery.id).label("completed_count")
        )
        .outerjoin(Delivery, (Delivery.driver_id == Driver.id) & (Delivery.actual_completion_time >= today_start))
        .filter(Driver.warehouse_id == wh.id, Driver.status == "available")
        .group_by(Driver.id)
        .order_by(func.count(Delivery.id).asc(), Driver.id.asc())
        .first()
    )

    available_driver = db.query(Driver).filter(Driver.id == driver_subq[0]).first() if driver_subq else None

    # Find available vehicle
    available_vehicles = db.query(Vehicle).filter(
        Vehicle.warehouse_id == wh.id,
        Vehicle.status == "available"
    ).order_by(Vehicle.id.asc()).all()

    selected_vehicle = None
    if available_vehicles:
        # Check EV vehicles first
        for v in available_vehicles:
            if v.vehicle_type and v.vehicle_type.is_ev:
                cons_per_km = float(v.vehicle_type.consumption_kwh_per_km) or 0.04
                battery_cap = float(v.vehicle_type.battery_capacity_kwh) or 3.5
                needed_kwh = total_est_dist_km * cons_per_km
                needed_soc_percent = (needed_kwh / battery_cap) * 100.0 if battery_cap > 0 else 0.0

                # Must cover trip + 15% reserve
                if float(v.current_soc_percent) >= (needed_soc_percent + 15.0):
                    selected_vehicle = v
                    break

        # If no EV satisfies range requirement, pick an available ICE vehicle
        if not selected_vehicle:
            for v in available_vehicles:
                if not (v.vehicle_type and v.vehicle_type.is_ev):
                    selected_vehicle = v
                    break

        # If still none, fallback to any available vehicle
        if not selected_vehicle and available_vehicles:
            selected_vehicle = available_vehicles[0]

    code = f"DEL-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.utcnow()

    if available_driver and selected_vehicle:
        available_driver.status = "busy"
        selected_vehicle.status = "busy"
        delivery_status = "assigned"
        driver_id_val = available_driver.id
        vehicle_id_val = selected_vehicle.id
    else:
        delivery_status = "pending_assignment"
        fallback_driver = available_driver or db.query(Driver).filter(Driver.warehouse_id == wh.id).first() or db.query(Driver).first()
        fallback_vehicle = selected_vehicle or db.query(Vehicle).filter(Vehicle.warehouse_id == wh.id).first() or db.query(Vehicle).first()
        driver_id_val = fallback_driver.id if fallback_driver else 1
        vehicle_id_val = fallback_vehicle.id if fallback_vehicle else 1

    delivery = Delivery(
        delivery_code=code,
        batch_id=batch.id,
        driver_id=driver_id_val,
        vehicle_id=vehicle_id_val,
        status=delivery_status,
        scheduled_dispatch_time=now,
        estimated_eta=now + timedelta(minutes=60),
    )
    db.add(delivery)
    db.flush()

    if delivery_status == "assigned":
        routing_service.generate_route_for_delivery(db, delivery.id)

    return delivery


def backfill_missing_route_geometries(db: Session):
    """Backfill worker: regenerate route geometry for assigned and in_transit deliveries missing geometry."""
    from backend.app.models.delivery import DeliveryRoute
    from backend.app.services import routing_service

    active_deliveries = db.query(Delivery).filter(
        Delivery.status.in_(["assigned", "in_transit", "dispatched"])
    ).all()

    for d in active_deliveries:
        route = db.query(DeliveryRoute).filter(DeliveryRoute.delivery_id == d.id).first()
        if not route or not route.route_geometry:
            try:
                routing_service.generate_route_for_delivery(db, d.id, overwrite=True)
            except Exception as err:
                print(f"[Backfill] Warning: Failed to generate route for Delivery #{d.id}: {err}")


def retry_pending_assignments(db: Session):
    """Backfill worker: process unassigned completed batches without duplicates and retry EV charging reservations."""
    from backend.app.models.vehicle import Vehicle
    from backend.app.models.warehouse import Warehouse
    from backend.app.services import charging_service

    # 0. Backfill depot chargers for all existing warehouses
    warehouses = db.query(Warehouse).all()
    for wh in warehouses:
        try:
            charging_service.generate_depot_chargers(db, wh.id, connectors_count=2, max_power_kw=50.0, price_per_kwh=0.0)
        except Exception:
            pass

    # 1. Retry charging reservations for vehicles needing charging without active reservations
    needs_charging_vehicles = db.query(Vehicle).filter(Vehicle.status == "needs_charging").all()
    for v in needs_charging_vehicles:
        from backend.app.models.charging import ChargingReservation
        active_res = (
            db.query(ChargingReservation)
            .filter(ChargingReservation.vehicle_id == v.id, ChargingReservation.status.in_(["confirmed", "active"]))
            .first()
        )
        if not active_res:
            charging_service.auto_reserve_depot_charging(db, v.id)

    # 2. Handoff pending batches
    completed_batches = db.query(Batch).filter(Batch.status == "completed").all()
    for b in completed_batches:
        existing = db.query(Delivery).filter(Delivery.batch_id == b.id).first()
        if not existing:
            auto_handoff_batch_to_delivery(db, b.id)
        elif existing.status == "pending_assignment":
            # Retry driver/vehicle assignment for pending deliveries
            wh = b.warehouse
            if not wh:
                continue

            avail_driver = db.query(Driver).filter(Driver.warehouse_id == wh.id, Driver.status == "available").first()
            avail_vehicle = db.query(Vehicle).filter(Vehicle.warehouse_id == wh.id, Vehicle.status == "available").first()
            if avail_driver and avail_vehicle:
                avail_driver.status = "busy"
                avail_vehicle.status = "busy"
                existing.driver_id = avail_driver.id
                existing.vehicle_id = avail_vehicle.id
                existing.status = "assigned"
                from backend.app.services import routing_service
                routing_service.generate_route_for_delivery(db, existing.id)
                db.commit()
    backfill_missing_route_geometries(db)


# ─── RIDER FLOW API ──────────────────────────────────────────────────────────
def get_rider_deliveries(db: Session, current_user) -> list:
    from backend.app.models.delivery import DeliveryStop, DeliveryRoute
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
        return []

    deliveries = db.query(Delivery).filter(
        Delivery.driver_id == driver.id,
        Delivery.status.in_(["assigned", "in_transit", "dispatched"])
    ).order_by(Delivery.created_at.desc()).all()

    res = []
    for d in deliveries:
        stops = db.query(DeliveryStop).filter(DeliveryStop.delivery_id == d.id).order_by(DeliveryStop.stop_sequence).all()
        route = db.query(DeliveryRoute).filter(DeliveryRoute.delivery_id == d.id).first()
        res.append({
            "id": d.id,
            "delivery_code": d.delivery_code,
            "status": d.status,
            "scheduled_dispatch_time": d.scheduled_dispatch_time,
            "estimated_eta": d.estimated_eta,
            "total_distance_km": float(route.total_distance_km) if route else 0.0,
            "estimated_travel_minutes": float(route.estimated_travel_minutes) if route else 0.0,
            "stops": [
                {
                    "id": s.id,
                    "order_id": s.order_id,
                    "order_number": s.order.order_number if s.order else "",
                    "customer_name": s.order.customer_name if s.order else "",
                    "destination_address": s.order.destination_address if s.order else "",
                    "destination_lat": float(s.order.destination_lat) if s.order else 0.0,
                    "destination_lon": float(s.order.destination_lon) if s.order else 0.0,
                    "stop_sequence": s.stop_sequence,
                    "status": s.status,
                    "estimated_arrival": s.estimated_arrival,
                    "actual_arrival": s.actual_arrival,
                }
                for s in stops
            ]
        })
    return res


def start_delivery(db: Session, delivery_id: int, current_user):
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not d:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Delivery not found.", "details": {}})

    # Own-record enforcement
    if current_user.role.code == "driver":
        dr = db.query(Driver).filter(Driver.user_id == current_user.id).first()
        if not dr or d.driver_id != dr.id:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Rider can only manage own deliveries.", "details": {}})

    d.status = "in_transit"
    d.actual_dispatch_time = datetime.utcnow()

    # Set order statuses to out_for_delivery
    from backend.app.models.delivery import DeliveryStop
    stops = db.query(DeliveryStop).filter(DeliveryStop.delivery_id == d.id).all()
    for s in stops:
        if s.order:
            s.order.status = "out_for_delivery"

    db.commit()
    db.refresh(d)
    return {"message": "Delivery started", "delivery_id": d.id, "status": d.status}


def deliver_stop(db: Session, delivery_id: int, stop_id: int, current_user=None):
    from backend.app.models.delivery import DeliveryStop
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not d:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Delivery not found.", "details": {}})

    if current_user and getattr(current_user, "role", None) and current_user.role.code == "driver":
        dr = db.query(Driver).filter(Driver.user_id == current_user.id).first()
        if not dr or d.driver_id != dr.id:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Rider can only manage own deliveries.", "details": {}})

    stop = db.query(DeliveryStop).filter(DeliveryStop.id == stop_id, DeliveryStop.delivery_id == d.id).first()
    if not stop:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Stop not found.", "details": {}})

    stop.status = "delivered"
    stop.actual_arrival = datetime.utcnow()
    if stop.order:
        stop.order.status = "delivered"

    # Check if all stops delivered
    all_stops = db.query(DeliveryStop).filter(DeliveryStop.delivery_id == d.id).all()
    if all(s.status == "delivered" for s in all_stops):
        d.status = "completed"
        d.actual_completion_time = datetime.utcnow()
        if d.driver:
            d.driver.status = "available"
        if d.vehicle:
            from backend.app.core.config import settings
            low_soc_threshold = getattr(settings, "LOW_SOC_THRESHOLD", 25.0)
            is_ev = d.vehicle.vehicle_type and d.vehicle.vehicle_type.is_ev
            if is_ev and float(d.vehicle.current_soc_percent) < low_soc_threshold:
                d.vehicle.status = "needs_charging"
                from backend.app.services import charging_service
                charging_service.auto_reserve_depot_charging(db, d.vehicle.id)
            else:
                d.vehicle.status = "available"

    db.commit()
    return {"message": "Stop delivered", "stop_id": stop.id, "delivery_completed": d.status == "completed"}

