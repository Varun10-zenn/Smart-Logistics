"""
Delivery Rider Simulation Service.

Provides background asyncio task per active delivery run to simulate vehicle movement along
the saved route geometry, emitting real telemetry events via telemetry_service.ingest_event.
Drains EV battery SoC in proportion to distance driven. Triggers low-SoC alert and charging recommendation.
"""
import asyncio
import json
import math
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.core.config import settings
from backend.app.models.delivery import Delivery, DeliveryRoute
from backend.app.schemas.telemetry import TelemetryEventCreate
from backend.app.services import telemetry_service, safety_service, ev_charging_optimization_service
from backend.app.schemas.charging import ChargingRecommendRequest

logger = logging.getLogger(__name__)

# Active background simulation tasks keyed by delivery_id
_ACTIVE_SIMULATIONS: Dict[int, Dict[str, Any]] = {}


def _haversine_dist_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


async def _run_delivery_simulation(delivery_id: int, profile: str):
    logger.info(f"[SIMULATOR] Starting delivery simulation for Delivery #{delivery_id} [Profile: {profile}]")
    db: Session = SessionLocal()
    try:
        delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
        if not delivery or not delivery.route or not delivery.route.route_geometry:
            msg = f"Cannot run simulation for Delivery #{delivery_id}: No route geometry."
            logger.error(f"[SIMULATOR] {msg}")
            if delivery_id in _ACTIVE_SIMULATIONS:
                _ACTIVE_SIMULATIONS[delivery_id]["status"] = "failed"
                _ACTIVE_SIMULATIONS[delivery_id]["error"] = msg
            return

        try:
            route_coords = json.loads(delivery.route.route_geometry)
        except Exception as e:
            msg = f"Invalid route_geometry JSON for Delivery #{delivery_id}: {e}"
            logger.error(f"[SIMULATOR] {msg}")
            if delivery_id in _ACTIVE_SIMULATIONS:
                _ACTIVE_SIMULATIONS[delivery_id]["status"] = "failed"
                _ACTIVE_SIMULATIONS[delivery_id]["error"] = msg
            return

        if not route_coords or len(route_coords) < 2:
            msg = f"Route geometry has fewer than 2 coordinates for Delivery #{delivery_id}"
            logger.error(f"[SIMULATOR] {msg}")
            if delivery_id in _ACTIVE_SIMULATIONS:
                _ACTIVE_SIMULATIONS[delivery_id]["status"] = "failed"
                _ACTIVE_SIMULATIONS[delivery_id]["error"] = msg
            return

        vehicle = delivery.vehicle
        is_ev = vehicle.vehicle_type and vehicle.vehicle_type.is_ev if vehicle else False
        battery_cap = float(vehicle.vehicle_type.battery_capacity_kwh) if (vehicle and vehicle.vehicle_type and vehicle.vehicle_type.battery_capacity_kwh) else 3.5
        current_soc = float(vehicle.current_soc_percent) if vehicle else 100.0

        interval = float(getattr(settings, "SIM_INTERVAL_SECONDS", 2))
        speed_mult = float(getattr(settings, "SIM_SPEED_MULTIPLIER", 10.0))
        consumption_kwh_per_km = float(getattr(settings, "EV_CONSUMPTION_KWH_PER_KM", 0.12))
        low_soc_thresh = float(getattr(settings, "LOW_SOC_THRESHOLD", 25.0))

        step_idx = 0
        total_steps = len(route_coords)
        low_soc_recommendation_triggered = False

        while step_idx < total_steps:
            sim_info = _ACTIVE_SIMULATIONS.get(delivery_id)
            if not sim_info or sim_info.get("status") != "running":
                logger.info(f"[SIMULATOR] Simulation stopped for Delivery #{delivery_id}")
                break

            curr_point = route_coords[step_idx]
            lat, lon = float(curr_point[0]), float(curr_point[1])

            # Calculate speed and acceleration based on profile
            speed_kmh = 35.0
            accel_ms2 = 0.0

            if profile == "aggressive":
                if step_idx % 4 == 1:
                    speed_kmh = 95.0
                    accel_ms2 = 1.5
                elif step_idx % 4 == 2:
                    speed_kmh = 45.0
                    accel_ms2 = -4.5
                elif step_idx % 4 == 3:
                    speed_kmh = 105.0
                    accel_ms2 = 4.5
            else:
                speed_kmh = 35.0 + (step_idx % 3) * 2.0
                accel_ms2 = 0.2

            dist_km = 0.0
            if step_idx > 0:
                prev_point = route_coords[step_idx - 1]
                dist_km = _haversine_dist_km(float(prev_point[0]), float(prev_point[1]), lat, lon)

            if vehicle and is_ev and dist_km > 0:
                # 1) Vehicle consumption & capacity with config fallbacks
                cons_kwh_km = (
                    float(vehicle.vehicle_type.consumption_kwh_per_km)
                    if (vehicle.vehicle_type and float(vehicle.vehicle_type.consumption_kwh_per_km) > 0)
                    else consumption_kwh_per_km
                )
                v_cap = (
                    float(vehicle.vehicle_type.battery_capacity_kwh)
                    if (vehicle.vehicle_type and float(vehicle.vehicle_type.battery_capacity_kwh) > 0)
                    else battery_cap
                )

                kwh_used = dist_km * cons_kwh_km
                soc_drain_pct = (kwh_used / v_cap) * 100.0 if v_cap > 0 else 1.0
                current_soc = max(0.0, current_soc - soc_drain_pct)
                vehicle.current_soc_percent = current_soc
                db.commit()

            if vehicle:
                event_in = TelemetryEventCreate(
                    vehicle_id=vehicle.id,
                    delivery_id=delivery.id,
                    timestamp=datetime.now(timezone.utc),
                    latitude=lat,
                    longitude=lon,
                    speed_kmh=speed_kmh,
                    acceleration_ms2=accel_ms2,
                    soc_percent=current_soc if is_ev else None,
                    heading_degrees=0.0
                )
                telemetry_service.ingest_event(db, event_in)

            if vehicle and is_ev and current_soc < low_soc_thresh and not low_soc_recommendation_triggered:
                low_soc_recommendation_triggered = True
                try:
                    next_stop_lat, next_stop_lon = lat, lon
                    if delivery.stops:
                        first_pending = next((s for s in delivery.stops if s.status != "delivered"), None)
                        if first_pending and first_pending.order:
                            next_stop_lat = float(first_pending.order.destination_lat)
                            next_stop_lon = float(first_pending.order.destination_lon)

                    rec_req = ChargingRecommendRequest(
                        vehicle_id=vehicle.id,
                        current_soc_percent=current_soc,
                        current_lat=lat,
                        current_lon=lon,
                        destination_lat=next_stop_lat,
                        destination_lon=next_stop_lon,
                        minimum_soc_after_charge=80.0
                    )
                    rec_resp = ev_charging_optimization_service.optimize_charging(db, rec_req)
                    delivery.charging_recommendation = rec_resp.model_dump_json()

                    # Auto reserve charger slot for this exact vehicle & delivery
                    from backend.app.services import charging_service
                    res = charging_service.auto_reserve_depot_charging(db, vehicle.id)
                    if res:
                        logger.info(f"[SIMULATOR] Auto-reserved charging slot #{res.slot_id} for Vehicle #{vehicle.id}")
                        # Auto start charging session
                        session_resp = charging_service.start_charging_session(db, res.id)
                        start_charging_simulation(db, res.id)

                    from backend.app.models.safety import SafetyAlert
                    alert_msg = f"Low battery warning: SoC at {current_soc:.1f}% (below threshold {low_soc_thresh:.1f}%). Recommended Station #{rec_resp.recommended_station_id}."
                    safety_alert = SafetyAlert(
                        delivery_id=delivery.id,
                        alert_type="low_battery",
                        severity="high",
                        message=alert_msg,
                        created_at=datetime.utcnow()
                    )
                    db.add(safety_alert)
                    db.commit()
                    logger.info(f"[SIMULATOR] Generated low battery recommendation & alert for Delivery #{delivery_id}")
                except Exception as ex:
                    logger.warning(f"[SIMULATOR] Could not generate low battery recommendation: {ex}")

            step_idx += 1
            sim_info["current_step"] = step_idx
            sim_info["total_steps"] = total_steps
            logger.debug(f"[SIMULATOR] Delivery #{delivery_id} step {step_idx}/{total_steps} (lat={lat:.5f}, lon={lon:.5f})")

            sleep_duration = interval / max(1.0, speed_mult)
            await asyncio.sleep(sleep_duration)

        sim_info = _ACTIVE_SIMULATIONS.get(delivery_id)
        if sim_info and sim_info.get("status") == "running":
            sim_info["status"] = "completed" if step_idx >= total_steps else "stopped"
            logger.info(f"[SIMULATOR] Simulation finished for Delivery #{delivery_id} with status '{sim_info['status']}'")

    except asyncio.CancelledError:
        logger.info(f"[SIMULATOR] Simulation task cancelled for Delivery #{delivery_id}")
        if delivery_id in _ACTIVE_SIMULATIONS:
            _ACTIVE_SIMULATIONS[delivery_id]["status"] = "stopped"
        raise
    except Exception as err:
        logger.error(f"[SIMULATOR] Error in simulation loop for Delivery #{delivery_id}: {err}", exc_info=True)
        if delivery_id in _ACTIVE_SIMULATIONS:
            _ACTIVE_SIMULATIONS[delivery_id]["status"] = "failed"
            _ACTIVE_SIMULATIONS[delivery_id]["error"] = str(err)
    finally:
        db.close()


def start_simulation(db: Session, delivery_id: int, profile: str = "normal") -> Dict[str, Any]:
    if not settings.is_simulator_enabled:
        raise HTTPException(
            status_code=403,
            detail={"code": "SIMULATOR_DISABLED", "message": "Rider simulator is disabled in this environment.", "details": {}}
        )

    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Delivery not found.", "details": {}})

    if not delivery.route or not delivery.route.route_geometry:
        raise HTTPException(
            status_code=409,
            detail={"code": "NO_ROUTE_GEOMETRY", "message": "No route geometry", "details": {}}
        )

    try:
        coords = json.loads(delivery.route.route_geometry)
    except Exception:
        coords = []

    if not coords or len(coords) < 2:
        raise HTTPException(
            status_code=409,
            detail={"code": "NO_ROUTE_GEOMETRY", "message": "No route geometry", "details": {}}
        )

    existing = _ACTIVE_SIMULATIONS.get(delivery_id)
    if existing:
        task = existing.get("_task")
        if existing.get("status") == "running" and task and not task.done():
            raise HTTPException(
                status_code=409,
                detail={"code": "CONFLICT", "message": "A simulation is already running for this delivery.", "details": {}}
            )

    if profile not in ("normal", "aggressive"):
        profile = "normal"

    total_steps = len(coords)

    # Use asyncio.create_task on the running event loop
    loop = asyncio.get_running_loop()
    task = loop.create_task(_run_delivery_simulation(delivery_id, profile))

    sim_info = {
        "delivery_id": delivery_id,
        "profile": profile,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "current_step": 0,
        "total_steps": total_steps,
        "_task": task,
    }

    _ACTIVE_SIMULATIONS[delivery_id] = sim_info
    logger.info(f"[SIMULATOR] Created and launched simulation background task for Delivery #{delivery_id}")
    return {k: v for k, v in sim_info.items() if k != "_task"}


def stop_simulation(delivery_id: int) -> Dict[str, Any]:
    if not settings.is_simulator_enabled:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Rider simulator is disabled in this environment.", "details": {}}
        )

    sim_info = _ACTIVE_SIMULATIONS.get(delivery_id)
    if not sim_info:
        return {"delivery_id": delivery_id, "status": "stopped", "message": "No active simulation."}

    sim_info["status"] = "stopped"
    task = sim_info.get("_task")
    if task and not task.done():
        task.cancel()

    return {"delivery_id": delivery_id, "status": "stopped", "message": "Simulation stopped."}


def get_simulation_status(delivery_id: int) -> Dict[str, Any]:
    if not settings.is_simulator_enabled:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Rider simulator is disabled in this environment.", "details": {}}
        )

    sim_info = _ACTIVE_SIMULATIONS.get(delivery_id)
    if not sim_info:
        return {"delivery_id": delivery_id, "status": "stopped", "profile": "none", "current_step": 0, "total_steps": 0}

    task = sim_info.get("_task")
    # Make "running" mean the task is alive: if status says running but task is dead/missing, report stopped
    if sim_info.get("status") == "running" and (task is None or task.done()):
        sim_info["status"] = "stopped"

    res = {
        "delivery_id": delivery_id,
        "status": sim_info.get("status", "stopped"),
        "profile": sim_info.get("profile", "normal"),
        "started_at": sim_info.get("started_at"),
        "current_step": sim_info.get("current_step", 0),
        "total_steps": sim_info.get("total_steps", 0),
    }
    if sim_info.get("error"):
        res["error"] = sim_info.get("error")
    return res

_ACTIVE_CHARGING_SIMULATIONS: Dict[int, Dict[str, Any]] = {}


async def _run_charging_session_simulation(reservation_id: int):
    """
    Background asyncio simulator for active EV charging sessions.
    Raises SoC every SIM_INTERVAL_SECONDS until target SoC (default 90%) is reached.
    """
    logger.info(f"[CHARGING_SIMULATOR] Starting charging session simulation for Reservation #{reservation_id}")
    db: Session = SessionLocal()
    try:
        from backend.app.models.charging import ChargingReservation, ChargingSession, ChargingConnector
        from backend.app.models.vehicle import Vehicle
        from backend.app.services import charging_service

        res = db.query(ChargingReservation).filter(ChargingReservation.id == reservation_id).first()
        if not res or res.status != "active":
            logger.warning(f"[CHARGING_SIMULATOR] Reservation #{reservation_id} is not active.")
            if reservation_id in _ACTIVE_CHARGING_SIMULATIONS:
                _ACTIVE_CHARGING_SIMULATIONS[reservation_id]["status"] = "stopped"
            return

        session = db.query(ChargingSession).filter(ChargingSession.reservation_id == res.id).first()
        vehicle = db.query(Vehicle).filter(Vehicle.id == res.vehicle_id).first()
        connector = db.query(ChargingConnector).filter(ChargingConnector.id == res.slot.connector_id).first() if (res and res.slot) else None

        if not session or not vehicle or not connector:
            logger.error(f"[CHARGING_SIMULATOR] Missing session/vehicle/connector for Reservation #{reservation_id}")
            if reservation_id in _ACTIVE_CHARGING_SIMULATIONS:
                _ACTIVE_CHARGING_SIMULATIONS[reservation_id]["status"] = "failed"
            return

        conn_power_kw = float(connector.max_power_kw) if connector.max_power_kw else 50.0
        # Vehicle max charge power default 1.5 kW
        veh_max_charge_kw = 1.5
        effective_power_kw = min(conn_power_kw, veh_max_charge_kw)

        speedup = float(getattr(settings, "CHARGE_SIM_SPEEDUP", 20.0))
        interval = float(getattr(settings, "SIM_INTERVAL_SECONDS", 2.0))
        target_soc = float(getattr(settings, "CHARGE_TARGET_SOC", 90.0))

        battery_cap = float(vehicle.vehicle_type.battery_capacity_kwh) if (vehicle.vehicle_type and vehicle.vehicle_type.battery_capacity_kwh) else 3.5
        if battery_cap <= 0:
            battery_cap = 3.5

        while float(vehicle.current_soc_percent) < target_soc:
            sim_info = _ACTIVE_CHARGING_SIMULATIONS.get(reservation_id)
            if not sim_info or sim_info.get("status") != "running":
                logger.info(f"[CHARGING_SIMULATOR] Charging session stopped for Reservation #{reservation_id}")
                break

            # Energy delivered in this step interval (hours * speedup)
            hours_elapsed = (interval / 3600.0) * speedup
            kwh_added = effective_power_kw * hours_elapsed
            soc_gain_pct = (kwh_added / battery_cap) * 100.0

            new_soc = min(target_soc, float(vehicle.current_soc_percent) + soc_gain_pct)
            vehicle.current_soc_percent = new_soc
            session.energy_kwh_delivered = round(float(session.energy_kwh_delivered or 0.0) + kwh_added, 2)
            db.commit()

            sim_info["current_soc"] = new_soc
            logger.debug(f"[CHARGING_SIMULATOR] Reservation #{reservation_id} vehicle #{vehicle.id} SoC={new_soc:.1f}%")

            if new_soc >= target_soc:
                break

            await asyncio.sleep(interval)

        # Session completion
        charging_service.complete_charging_session(db, reservation_id, target_soc=target_soc)
        sim_info = _ACTIVE_CHARGING_SIMULATIONS.get(reservation_id)
        if sim_info:
            sim_info["status"] = "completed"
            sim_info["current_soc"] = target_soc

    except asyncio.CancelledError:
        logger.info(f"[CHARGING_SIMULATOR] Charging task cancelled for Reservation #{reservation_id}")
        if reservation_id in _ACTIVE_CHARGING_SIMULATIONS:
            _ACTIVE_CHARGING_SIMULATIONS[reservation_id]["status"] = "stopped"
        raise
    except Exception as err:
        logger.error(f"[CHARGING_SIMULATOR] Error in charging loop for Reservation #{reservation_id}: {err}", exc_info=True)
        if reservation_id in _ACTIVE_CHARGING_SIMULATIONS:
            _ACTIVE_CHARGING_SIMULATIONS[reservation_id]["status"] = "failed"
            _ACTIVE_CHARGING_SIMULATIONS[reservation_id]["error"] = str(err)
    finally:
        db.close()


def start_charging_simulation(db: Session, reservation_id: int) -> Dict[str, Any]:
    if not settings.is_simulator_enabled:
        raise HTTPException(
            status_code=403,
            detail={"code": "SIMULATOR_DISABLED", "message": "Simulator is disabled in this environment.", "details": {}}
        )

    from backend.app.models.charging import ChargingReservation
    res = db.query(ChargingReservation).filter(ChargingReservation.id == reservation_id).first()
    if not res:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Reservation not found.", "details": {}})

    existing = _ACTIVE_CHARGING_SIMULATIONS.get(reservation_id)
    if existing:
        task = existing.get("_task")
        if existing.get("status") == "running" and task and not task.done():
            return {k: v for k, v in existing.items() if k != "_task"}

    loop = asyncio.get_running_loop()
    task = loop.create_task(_run_charging_session_simulation(reservation_id))

    sim_info = {
        "reservation_id": reservation_id,
        "vehicle_id": res.vehicle_id,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "current_soc": float(res.vehicle.current_soc_percent) if res.vehicle else 0.0,
        "_task": task,
    }
    _ACTIVE_CHARGING_SIMULATIONS[reservation_id] = sim_info
    return {k: v for k, v in sim_info.items() if k != "_task"}


def stop_charging_simulation(reservation_id: int) -> Dict[str, Any]:
    sim_info = _ACTIVE_CHARGING_SIMULATIONS.get(reservation_id)
    if not sim_info:
        return {"reservation_id": reservation_id, "status": "stopped", "message": "No active simulation."}

    sim_info["status"] = "stopped"
    task = sim_info.get("_task")
    if task and not task.done():
        task.cancel()
    return {"reservation_id": reservation_id, "status": "stopped", "message": "Charging simulation stopped."}


