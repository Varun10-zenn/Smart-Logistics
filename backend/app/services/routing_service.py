"""Routing service for delivery route generation and stop sequencing."""
import json
import math
import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.app.models.delivery import Delivery, DeliveryStop, DeliveryRoute

logger = logging.getLogger(__name__)


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _interpolate_segment(lat1: float, lon1: float, lat2: float, lon2: float, step_meters: float = 25.0) -> List[Tuple[float, float]]:
    """Generates an ordered list of [lon, lat] points along a straight leg every ~step_meters."""
    dist_km = _haversine_distance(lat1, lon1, lat2, lon2)
    dist_m = dist_km * 1000.0
    num_steps = max(1, int(math.ceil(dist_m / step_meters)))

    coords = []
    for i in range(num_steps):
        t = i / float(num_steps)
        lat = lat1 + t * (lat2 - lat1)
        lon = lon1 + t * (lon2 - lon1)
        coords.append((round(lon, 6), round(lat, 6)))
    return coords


def _fetch_osrm_geometry(points: List[Tuple[float, float]]) -> Optional[List[Tuple[float, float]]]:
    """Attempts to fetch real road network geometry from OSRM public service."""
    if len(points) < 2:
        return None
    try:
        import httpx
        coords_str = ";".join([f"{lon:.6f},{lat:.6f}" for lat, lon in points])
        url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
        resp = httpx.get(url, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "Ok" and data.get("routes"):
                geom_coords = data["routes"][0]["geometry"]["coordinates"]
                if len(geom_coords) >= 2:
                    return [tuple(c) for c in geom_coords]
    except Exception as err:
        logger.warning(f"OSRM route fetch failed or timed out: {err}. Falling back to Haversine segment interpolation.")
    return None


def generate_route_for_delivery(db: Session, delivery_id: int, overwrite: bool = False):
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Delivery not found.", "details": {}})

    if delivery.route and not overwrite:
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": "Route already generated.", "details": {}})

    batch = delivery.batch
    if not batch:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "No batch associated with delivery.", "details": {}})

    warehouse = batch.warehouse
    if not warehouse:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "No warehouse associated with batch.", "details": {}})

    orders = [bo.order for bo in batch.batch_orders if bo.order]
    if not orders:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "No orders to route.", "details": {}})

    # Deterministic stop sequencing via nearest-neighbor
    unvisited = list(orders)
    current_lat = float(warehouse.latitude)
    current_lon = float(warehouse.longitude)
    total_distance = 0.0
    stops = []
    seq = 1
    
    current_time = delivery.scheduled_dispatch_time or datetime.utcnow()

    # Clear existing stops if overwriting route
    if overwrite:
        db.query(DeliveryStop).filter(DeliveryStop.delivery_id == delivery.id).delete()
        if delivery.route:
            db.delete(delivery.route)
            db.flush()

    waypoint_lat_lons = [(current_lat, current_lon)]

    while unvisited:
        nearest = None
        min_dist = float('inf')
        for o in unvisited:
            dist = _haversine_distance(current_lat, current_lon, float(o.destination_lat), float(o.destination_lon))
            if dist < min_dist:
                min_dist = dist
                nearest = o
        
        unvisited.remove(nearest)
        total_distance += min_dist
        
        travel_minutes = (min_dist / 40.0) * 60.0
        current_time += timedelta(minutes=travel_minutes)
        
        stop = DeliveryStop(
            delivery_id=delivery.id,
            order_id=nearest.id,
            stop_sequence=seq,
            status="pending",
            estimated_arrival=current_time
        )
        db.add(stop)
        stops.append(stop)
        
        seq += 1
        current_lat = float(nearest.destination_lat)
        current_lon = float(nearest.destination_lon)
        waypoint_lat_lons.append((current_lat, current_lon))
        current_time += timedelta(minutes=5.0)

    # Return to warehouse
    return_dist = _haversine_distance(current_lat, current_lon, float(warehouse.latitude), float(warehouse.longitude))
    total_distance += return_dist
    waypoint_lat_lons.append((float(warehouse.latitude), float(warehouse.longitude)))

    total_travel_minutes = (total_distance / 40.0) * 60.0 + (len(stops) * 5.0)

    # Build geometry: try OSRM first, fallback to dense Haversine segment interpolation
    osrm_coords = _fetch_osrm_geometry(waypoint_lat_lons)
    if osrm_coords:
        final_coords = osrm_coords
        route_source = "osrm"
    else:
        dense_coords = []
        for i in range(len(waypoint_lat_lons) - 1):
            p1 = waypoint_lat_lons[i]
            p2 = waypoint_lat_lons[i + 1]
            segment = _interpolate_segment(p1[0], p1[1], p2[0], p2[1], step_meters=25.0)
            dense_coords.extend(segment)
        # Append final endpoint
        last_pt = waypoint_lat_lons[-1]
        dense_coords.append((round(last_pt[1], 6), round(last_pt[0], 6)))
        final_coords = dense_coords
        route_source = "haversine_fallback"

    geometry_json = json.dumps([[c[0], c[1]] for c in final_coords])

    route = DeliveryRoute(
        delivery_id=delivery.id,
        total_distance_km=total_distance,
        estimated_travel_minutes=total_travel_minutes,
        traffic_factor=1.0,
        weather_factor=1.0,
        route_geometry=geometry_json,
        route_source=route_source
    )
    db.add(route)
    
    delivery.estimated_eta = delivery.scheduled_dispatch_time + timedelta(minutes=total_travel_minutes)
    
    db.commit()
    db.refresh(route)
    return route

