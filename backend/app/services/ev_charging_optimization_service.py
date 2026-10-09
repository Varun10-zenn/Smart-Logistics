import math
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.charging import ChargingStation, ChargingConnector, ChargingSlot, ChargingReservation, ChargingSession
from backend.app.models.vehicle import Vehicle, VehicleType
from backend.app.schemas.charging import ChargingRecommendRequest, ChargingRecommendResponse, ChargingCandidate
from fastapi import HTTPException

# Defaults for multi-objective optimization
DIST_WEIGHT = 0.5
WAIT_WEIGHT = 0.3
CHARGE_TIME_WEIGHT = 0.2

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))

def optimize_charging(db: Session, request: ChargingRecommendRequest) -> ChargingRecommendResponse:
    # 1. Fetch vehicle and battery details
    vehicle = db.query(Vehicle).filter(Vehicle.id == request.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"Vehicle {request.vehicle_id} not found.", "details": {}})
    
    battery_capacity_kwh = float(vehicle.vehicle_type.battery_capacity_kwh)
    current_soc = request.current_soc_percent
    target_soc = request.minimum_soc_after_charge
    
    if current_soc < 0 or current_soc > 100:
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "Invalid current SoC.", "details": {}})
    if target_soc <= current_soc:
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "Target SoC must be greater than current SoC.", "details": {}})
    if target_soc > 100:
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "Invalid target SoC.", "details": {}})
    
    energy_required_kwh = 0.0
    if battery_capacity_kwh > 0:
        energy_required_kwh = battery_capacity_kwh * (target_soc - current_soc) / 100.0
    else:
        # Fallback if no battery size known, assume default 50kWh
        energy_required_kwh = 50.0 * (target_soc - current_soc) / 100.0
    
    # 2. Find eligible stations
    stations = db.query(ChargingStation).filter(ChargingStation.status == "operational").all()
    if not stations:
        raise HTTPException(status_code=503, detail={"code": "SERVICE_UNAVAILABLE", "message": "No operational charging stations available.", "details": {}})
    
    now = request.preferred_start or datetime.now(timezone.utc)
    
    def _ensure_aware(dt):
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    
    now_aware = _ensure_aware(now)
    
    candidates = []
    
    for station in stations:
        dist_km = _haversine_km(request.current_lat, request.current_lon, float(station.latitude), float(station.longitude))

        # Check reachability with 10% reserve
        cons_per_km = float(vehicle.vehicle_type.consumption_kwh_per_km) if (vehicle.vehicle_type and float(vehicle.vehicle_type.consumption_kwh_per_km) > 0) else 0.04
        current_kwh = (current_soc / 100.0) * battery_capacity_kwh if battery_capacity_kwh > 0 else 3.5
        max_reachable_dist_km = (current_kwh / cons_per_km) if cons_per_km > 0 else 9999.0

        # Must reach station with at least 10% battery reserve left
        reserve_kwh = 0.10 * battery_capacity_kwh
        usable_kwh = max(0.0, current_kwh - reserve_kwh)
        reachable_dist_km = usable_kwh / cons_per_km if cons_per_km > 0 else 9999.0

        if dist_km > reachable_dist_km:
            continue

        # Filter connectors by compatibility
        veh_conn_type = vehicle.connector_type or "CCS2"
        connectors = [
            c for c in station.connectors
            if c.status != "offline" and c.status != "maintenance"
            and (c.connector_type == veh_conn_type or not vehicle.connector_type or vehicle.connector_type == "CCS2")
        ]
        if not connectors:
            continue

        best_connector = None
        best_connector_wait = float('inf')
        best_connector_charge_time = float('inf')
        best_slot_id = None

        for conn in connectors:
            power_kw = float(conn.max_power_kw)
            if power_kw <= 0:
                continue

            # Vehicle max charge power limit (use 1.5 kW only for scooters with small battery <= 10 kWh)
            veh_max_charge_kw = 1.5 if (battery_capacity_kwh > 0 and battery_capacity_kwh <= 10.0) else power_kw
            effective_power_kw = min(power_kw, veh_max_charge_kw)
            charge_time_hours = energy_required_kwh / effective_power_kw
            charge_time_mins = charge_time_hours * 60.0

            free_slots = [s for s in conn.slots if not s.is_booked and _ensure_aware(s.end_time) > now_aware]
            free_slots.sort(key=lambda x: x.start_time)

            valid_slot = None
            for s in free_slots:
                start_time = max(_ensure_aware(s.start_time), now_aware)
                slot_duration_mins = (_ensure_aware(s.end_time) - start_time).total_seconds() / 60.0
                if slot_duration_mins >= charge_time_mins:
                    valid_slot = s
                    break

            if valid_slot:
                start_avail = max(_ensure_aware(valid_slot.start_time), now_aware)
                wait_mins = max(0.0, (start_avail - now_aware).total_seconds() / 60.0)

                if wait_mins < best_connector_wait:
                    best_connector_wait = wait_mins
                    best_connector = conn
                    best_connector_charge_time = charge_time_mins
                    best_slot_id = valid_slot.id

        if best_connector is not None:
            score = (DIST_WEIGHT * dist_km) + (WAIT_WEIGHT * best_connector_wait) + (CHARGE_TIME_WEIGHT * best_connector_charge_time)
            candidates.append({
                "station": station,
                "connector": best_connector,
                "slot_id": best_slot_id,
                "dist_km": dist_km,
                "wait_mins": best_connector_wait,
                "charge_mins": best_connector_charge_time,
                "score": score
            })

    if not candidates:
        # Stranded risk alert generation
        from backend.app.models.safety import SafetyAlert
        alert_msg = f"STRANDED RISK: Vehicle #{vehicle.id} at SoC {current_soc:.1f}% cannot reach any compatible operational charging station with 10% reserve."
        db.add(SafetyAlert(
            delivery_id=None,
            alert_type="stranded_risk",
            severity="critical",
            message=alert_msg,
            created_at=datetime.utcnow()
        ))
        db.commit()
        raise HTTPException(status_code=409, detail={"code": "STRANDED_RISK", "message": "No compatible station reachable with required battery reserve.", "details": {}})

    candidates.sort(key=lambda x: x["score"])
    candidates = candidates[:3]  # Return top 3 candidates
        
    # Rank
    candidates.sort(key=lambda x: x["score"])
    best = candidates[0]
    
    explanation = (
        f"Station '{best['station'].name}' selected. "
        f"Distance: {best['dist_km']:.1f}km. "
        f"Est. Wait: {best['wait_mins']:.1f}m. "
        f"Est. Charge: {best['charge_mins']:.1f}m."
    )
    
    candidate_list = []
    for c in candidates:
        candidate_list.append(ChargingCandidate(
            station_id=c['station'].id,
            connector_id=c['connector'].id,
            slot_id=c['slot_id'],
            estimated_wait_minutes=c['wait_mins'],
            estimated_charge_minutes=c['charge_mins'],
            route_detour_km=c['dist_km'],
            station_score=c['score']
        ))
    
    return ChargingRecommendResponse(
        recommended_station_id=best['station'].id,
        recommended_connector_id=best['connector'].id,
        recommended_slot_id=best['slot_id'],
        estimated_wait_minutes=best['wait_mins'],
        estimated_charge_minutes=best['charge_mins'],
        route_detour_km=best['dist_km'],
        station_score=best['score'],
        explanation=explanation,
        algorithm="multi_objective_v1",
        fallback_used=False,
        candidate_stations=candidate_list,
        optimization_metadata={
            "energy_required_kwh": round(energy_required_kwh, 2),
            "target_soc": target_soc,
            "current_soc": current_soc
        }
    )
