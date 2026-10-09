import pytest
from datetime import datetime, timezone, timedelta
from backend.app.schemas.charging import ChargingRecommendRequest
from backend.app.services.ev_charging_optimization_service import optimize_charging
from backend.app.models.charging import ChargingStation, ChargingConnector, ChargingSlot, ChargingReservation
from backend.app.models.vehicle import Vehicle, VehicleType

def setup_test_data(db):
    # Ensure vehicle exists
    v = db.query(Vehicle).first()
    v.vehicle_type.battery_capacity_kwh = 60.0
    db.commit()
    
    # Check if station already exists
    s1 = db.query(ChargingStation).filter(ChargingStation.station_code == "ST-OPT-1").first()
    if s1:
        s2 = db.query(ChargingStation).filter(ChargingStation.station_code == "ST-OPT-2").first()
        c1 = db.query(ChargingConnector).filter(ChargingConnector.station_id == s1.id, ChargingConnector.connector_number == 1).first()
        c2 = db.query(ChargingConnector).filter(ChargingConnector.station_id == s1.id, ChargingConnector.connector_number == 2).first()
        c3 = db.query(ChargingConnector).filter(ChargingConnector.station_id == s2.id, ChargingConnector.connector_number == 1).first()
        return v, s1, s2, c1, c2, c3

    # Create stations
    s1 = ChargingStation(station_code="ST-OPT-1", name="Station 1", latitude=13.0, longitude=80.0, total_connectors=2)
    s2 = ChargingStation(station_code="ST-OPT-2", name="Station 2", latitude=13.1, longitude=80.1, total_connectors=1)
    db.add(s1)
    db.add(s2)
    db.commit()
    
    c1 = ChargingConnector(station_id=s1.id, connector_number=1, connector_type="CCS2", max_power_kw=50.0)
    c2 = ChargingConnector(station_id=s1.id, connector_number=2, connector_type="CCS2", max_power_kw=50.0)
    c3 = ChargingConnector(station_id=s2.id, connector_number=1, connector_type="CCS2", max_power_kw=150.0) # Fast charger
    db.add_all([c1, c2, c3])
    db.commit()
    
    # Add slots
    now = datetime.now(timezone.utc)
    slots = []
    # c1 has a slot now
    slots.append(ChargingSlot(connector_id=c1.id, start_time=now, end_time=now + timedelta(hours=2), is_booked=False))
    # c2 is booked for next 1 hour, free after that
    slots.append(ChargingSlot(connector_id=c2.id, start_time=now, end_time=now + timedelta(hours=1), is_booked=True))
    slots.append(ChargingSlot(connector_id=c2.id, start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=3), is_booked=False))
    # c3 is available now
    slots.append(ChargingSlot(connector_id=c3.id, start_time=now, end_time=now + timedelta(hours=2), is_booked=False))
    
    db.add_all(slots)
    db.commit()
    
    return v, s1, s2, c1, c2, c3

class TestEVOptimization:
    def test_optimization_success(self, db_session):
        v, s1, s2, c1, c2, c3 = setup_test_data(db_session)
        
        req = ChargingRecommendRequest(
            vehicle_id=v.id,
            current_soc_percent=20.0,
            minimum_soc_after_charge=80.0,
            current_lat=13.0,
            current_lon=80.0,
            destination_lat=13.2,
            destination_lon=80.2
        )
        
        res = optimize_charging(db_session, req)
        assert res is not None
        assert res.recommended_station_id is not None
        assert res.recommended_connector_id is not None
        assert res.optimization_metadata["energy_required_kwh"] == 36.0 # 60 * (80-20)/100
        assert len(res.candidate_stations) > 0

    def test_optimization_invalid_soc(self, db_session):
        v = db_session.query(Vehicle).first()
        req = ChargingRecommendRequest(
            vehicle_id=v.id,
            current_soc_percent=90.0,
            minimum_soc_after_charge=80.0,
            current_lat=13.0,
            current_lon=80.0,
            destination_lat=13.2,
            destination_lon=80.2
        )
        from fastapi import HTTPException
        try:
            optimize_charging(db_session, req)
            assert False, "Should raise Exception"
        except HTTPException as e:
            assert e.status_code == 422
            
    def test_optimization_api(self, client, admin_headers, db_session):
        v, _, _, _, _, _ = setup_test_data(db_session)
        
        resp = client.post("/api/v1/charging/recommend", headers=admin_headers, json={
            "vehicle_id": v.id,
            "current_soc_percent": 30.0,
            "minimum_soc_after_charge": 80.0,
            "current_lat": 13.0,
            "current_lon": 80.0,
            "destination_lat": 13.2,
            "destination_lon": 80.2
        })
        
        assert resp.status_code == 200
        data = resp.json()
        assert "recommended_station_id" in data
        assert "candidate_stations" in data
        assert data["optimization_metadata"]["energy_required_kwh"] == 30.0
