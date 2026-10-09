"""Vehicle service."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.vehicle import Vehicle, VehicleType
from backend.app.schemas.common import make_page
from backend.app.schemas.vehicle import VehicleCreate, VehicleRead, SoCUpdate


def _to_read(v: Vehicle) -> VehicleRead:
    vtype = v.vehicle_type
    is_ev = vtype.is_ev if vtype else False
    bat_cap = float(vtype.battery_capacity_kwh) if vtype and is_ev else None
    consumption = float(vtype.consumption_kwh_per_km) if vtype and is_ev else None
    return VehicleRead(
        id=v.id,
        registration_number=v.registration_number,
        is_ev=is_ev,
        battery_capacity_kwh=bat_cap,
        soc_percent=float(v.current_soc_percent),
        consumption_kwh_per_km=consumption,
        status=v.status,
    )


def list_vehicles(db: Session, page: int = 1, page_size: int = 20,
                  is_ev: bool = None, status: str = None):
    q = db.query(Vehicle)
    if is_ev is not None:
        q = q.join(VehicleType).filter(VehicleType.is_ev == is_ev)
    if status:
        q = q.filter(Vehicle.status == status)
    total = q.count()
    vehicles = q.offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_to_read(v) for v in vehicles], total, page, page_size)


def create_vehicle(db: Session, data: VehicleCreate) -> VehicleRead:
    existing = db.query(Vehicle).filter(Vehicle.registration_number == data.registration_no).first()
    if existing:
        raise HTTPException(status_code=409, detail={"code": "DUPLICATE_RESOURCE", "message": "Registration number already exists.", "details": {}})
    vtype = db.query(VehicleType).filter(VehicleType.id == data.vehicle_type_id).first()
    if vtype is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Vehicle type not found.", "details": {}})
    vehicle = Vehicle(
        registration_number=data.registration_no,
        vehicle_type_id=data.vehicle_type_id,
        current_soc_percent=100.0,
        status="idle",
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return _to_read(vehicle)


def get_vehicle(db: Session, vehicle_id: int) -> VehicleRead:
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if v is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Vehicle not found.", "details": {}})
    return _to_read(v)


def update_soc(db: Session, vehicle_id: int, data: SoCUpdate) -> VehicleRead:
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if v is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Vehicle not found.", "details": {}})
    v.current_soc_percent = data.soc_percent
    db.commit()
    db.refresh(v)
    return _to_read(v)


def get_fleet_batteries(db: Session, warehouse_id: int = None) -> list:
    """
    Returns EV battery overview for admin showing EV SoC, status, reservation/session,
    registration numbers, store names, and estimated time to full (target 90%).
    """
    from backend.app.models.charging import ChargingReservation, ChargingSession, ChargingConnector
    from backend.app.models.warehouse import Warehouse

    q = db.query(Vehicle).join(VehicleType).filter(VehicleType.is_ev == True)
    if warehouse_id:
        q = q.filter(Vehicle.warehouse_id == warehouse_id)

    evs = q.all()
    res = []

    for v in evs:
        store_name = v.warehouse.name if v.warehouse else "Unassigned"
        active_res = (
            db.query(ChargingReservation)
            .filter(ChargingReservation.vehicle_id == v.id, ChargingReservation.status.in_(["confirmed", "active"]))
            .order_by(ChargingReservation.start_time.asc())
            .first()
        )
        active_sess = (
            db.query(ChargingSession)
            .filter(ChargingSession.vehicle_id == v.id, ChargingSession.end_time.is_(None))
            .first()
        )

        est_time_to_full_mins = 0.0
        current_soc = float(v.current_soc_percent)
        target_soc = 90.0

        if current_soc < target_soc:
            bat_cap = float(v.vehicle_type.battery_capacity_kwh) if (v.vehicle_type and v.vehicle_type.battery_capacity_kwh) else 3.5
            needed_kwh = ((target_soc - current_soc) / 100.0) * bat_cap

            # Power limit: min(connector power if charging, else 50.0, vehicle max 1.5 kW)
            veh_max_charge_kw = 1.5
            conn_power = 50.0
            if active_sess and active_sess.connector:
                conn_power = float(active_sess.connector.max_power_kw)

            effective_kw = min(conn_power, veh_max_charge_kw)
            est_time_to_full_mins = round((needed_kwh / effective_kw) * 60.0, 1)

        res.append({
            "vehicle_id": v.id,
            "registration_number": v.registration_number,
            "warehouse_id": v.warehouse_id,
            "store_name": store_name,
            "connector_type": v.connector_type or "CCS2",
            "current_soc_percent": current_soc,
            "status": v.status,
            "battery_capacity_kwh": float(v.vehicle_type.battery_capacity_kwh) if v.vehicle_type else 3.5,
            "active_reservation_code": active_res.reservation_code if active_res else None,
            "charging_status": "charging" if active_sess else ("reserved" if active_res else "idle"),
            "estimated_time_to_full_mins": est_time_to_full_mins,
        })
    return res
