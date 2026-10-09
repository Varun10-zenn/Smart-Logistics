# Smart Logistics Platform — Input / Output Examples

This document provides concrete JSON payload examples and step-by-step processing execution traces for key module actions.

---

## 1. Warehouse: Batch Optimization

### HTTP Request
`POST /api/v1/batches/optimize`

**Request Payload:**
```json
{
  "warehouse_id": 1,
  "max_orders_per_batch": 5,
  "max_weight_kg": 150.0,
  "max_volume_cbm": 2.5,
  "use_2opt_routing": true
}
```

### Processing Flow
1. FastAPI router `batches.py` delegates to `WarehouseOptimizationService.optimize_warehouse`.
2. DB query fetches pending orders for `warehouse_id = 1` and stock availability map.
3. `OrderBatchingEngine` evaluates orders based on weight, volume, and priority constraints.
4. `PickRouteOptimizationEngine` constructs Dijkstra shortest path matrix and runs 2-opt TSP route smoothing across picking locations.
5. Atomic DB transaction creates `batches`, `batch_orders`, `pick_routes`, and `pick_route_steps`.

### API Response Payload
```json
{
  "success": true,
  "warehouse_id": 1,
  "total_pending_orders": 3,
  "eligible_orders_count": 3,
  "generated_batches_count": 1,
  "batches": [
    {
      "batch_id": 12,
      "batch_code": "BATCH-8F9E2A10",
      "order_ids": [101, 102, 103],
      "total_weight_kg": 42.5,
      "total_volume_cbm": 0.85,
      "pick_route_id": 7,
      "total_distance_meters": 148.5,
      "estimated_duration_minutes": 12.4,
      "algorithm_used": "dijkstra_2opt",
      "steps_count": 5
    }
  ],
  "unassigned_order_ids": [],
  "unassigned_reasons": {},
  "overall_distance_reduction_pct": 18.4,
  "execution_time_ms": 42.1,
  "recommendation_id": 45
}
```

---

## 2. Safety: Telemetry Ingestion & Score Processing

### HTTP Request
`POST /api/v1/telemetry`

**Request Payload:**
```json
{
  "delivery_id": 5,
  "timestamp": "2026-10-02T10:15:30Z",
  "latitude": 12.9716,
  "longitude": 77.5946,
  "speed_kmh": 92.5,
  "acceleration_mpss": -4.8
}
```

### Processing Flow
1. `telemetry_service.py` inserts raw event into `telemetry_events`.
2. Triggers `safety_service.analyze_telemetry(db, event)`:
   - `speed_kmh = 92.5` > threshold `80.0` $\rightarrow$ Creates speeding `SafetyEvent` (penalty 2.0 pts).
   - `acceleration_mpss = -4.8` < threshold `-4.0` $\rightarrow$ Creates harsh braking `SafetyEvent` (penalty 3.0 pts).
3. Deducts points from `SafetyScore` for Delivery 5:
   - Speed score: $100.0 - 2.0 = 98.0$
   - Braking score: $100.0 - 3.0 = 97.0$
   - Final score = $(98.0 + 97.0 + 100.0 + 100.0) / 4 = 98.75$
4. Commits score update.

### API Response Payload
```json
{
  "id": 801,
  "delivery_id": 5,
  "timestamp": "2026-10-02T10:15:30Z",
  "latitude": 12.9716,
  "longitude": 77.5946,
  "speed_kmh": 92.5,
  "acceleration_mpss": -4.8
}
```

---

## 3. EV Charging: Slot Reservation

### HTTP Request
`POST /api/v1/charging/reservations`

**Request Payload:**
```json
{
  "slot_id": 24,
  "vehicle_id": 3,
  "driver_id": 2,
  "delivery_id": 5
}
```

### Processing Flow
1. `charging_service.create_reservation` locks connector row via `SELECT FOR UPDATE`.
2. Verifies `ChargingSlot(id=24).is_booked == False`.
3. Runs `has_charging_reservation_overlap` query to guarantee no overlapping active booking exists on the same connector.
4. Marks `is_booked = True` and inserts new `ChargingReservation`.

### API Response Payload
```json
{
  "id": 14,
  "reservation_code": "RES-4A82B91C0E",
  "slot_id": 24,
  "vehicle_id": 3,
  "driver_id": 2,
  "delivery_id": 5,
  "start_time": "2026-10-02T14:00:00Z",
  "end_time": "2026-10-02T14:45:00Z",
  "status": "confirmed",
  "created_at": "2026-10-02T12:05:10Z"
}
```
