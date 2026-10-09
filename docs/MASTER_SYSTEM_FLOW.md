# Smart Logistics Platform — Master System Flow Map

This document details the single master flow of data through the platform from user login to dashboard update.

```
USER
 │
 ▼
[1. LOGIN] ──────────────────► POST /api/v1/auth/login ──► JWT Bearer Token stored in localStorage
 │
 ▼
[2. DASHBOARD] ──────────────► GET /api/v1/dashboard/stats ──► Renders Fleet, Order & Safety KPIs
 │
 ▼
[3. WAREHOUSE SELECTION] ────► GET /api/v1/warehouses/{id}/graph ──► Loads Nodes, Edges & Locations
 │
 ▼
[4. ORDER INGESTION] ────────► GET /api/v1/orders?status=pending ──► Lists Pending Pick Orders
 │
 ▼
[5. BATCH OPTIMIZATION] ─────► POST /api/v1/batches/optimize ──► Groups orders by capacity/priority
 │                                                               └──► Inserts into `batches` & `batch_orders`
 ▼
[6. PICK ROUTE OPTIMIZATION] ─► OrderBatcher + PickRoutingEngine ──► Dijkstra Shortest Path + 2-opt TSP
 │                                                               └──► Inserts into `pick_routes` & `pick_route_steps`
 ▼
[7. DELIVERY DISPATCH] ──────► POST /api/v1/deliveries ──► Assigns Driver + Vehicle
 │                                                          └──► Inserts into `deliveries`
 ▼
[8. ROUTE & ETA GENERATION] ──► POST /api/v1/deliveries/{id}/route ──► OSRM / Haversine + Traffic & Weather
 │                                                                     └──► Updates `deliveries` (route, ETA)
 ▼
[9. TELEMETRY INGESTION] ────► POST /api/v1/telemetry ──► Ingests Speed, Acceleration, GPS, Timestamp
 │                                                        └──► Inserts into `telemetry_events`
 ▼
[10. SAFETY ANALYSIS] ───────► SafetyService.analyze_telemetry ──► Evaluates Speed, Braking & Accel rules
 │                                                                  └──► Inserts `safety_events`
 ▼
[11. SAFETY SCORE & ALERTS] ──► Deducts penalty points ──► Updates `safety_scores`
 │                                                      └──► Creates `safety_alerts` if score < 70
 ▼
[12. EV SOC MONITORING] ─────► GET /api/v1/vehicles?type=EV ──► Reads current battery SoC %
 │
 ▼
[13. EV RECOMMENDATION] ─────► POST /api/v1/charging/recommend ──► Ranks compatible charging stations
 │
 ▼
[14. SLOT RESERVATION] ──────► POST /api/v1/charging/reservations ──► SELECT FOR UPDATE + Overlap Check
 │                                                                    └──► Inserts into `charging_reservations`
 ▼
[15. CHARGING SESSION] ──────► Updates SoC from Initial to Target ──► Inserts into `charging_sessions`
 │
 ▼
[16. DASHBOARD UPDATE] ──────► TanStack Query Refetch ──► Real-time UI synchronization across components
```

---

## Stage-by-Stage Mapping

| Stage | Frontend File | API Endpoint | Backend Service | Database Tables | Primary Output |
| ----- | ------------- | ------------ | --------------- | --------------- | -------------- |
| **Login** | `LoginPage.tsx` | `POST /api/v1/auth/login` | `auth_service.py` | `users`, `roles` | JWT Access Token |
| **Dashboard** | `DashboardPage.tsx` | `GET /api/v1/dashboard/stats` | `dashboard_service.py` | Read-only metrics across all tables | Metric Counters & Alerts |
| **Warehouse Graph** | `WarehousePage.tsx` | `GET /api/v1/warehouses/{id}/graph` | `warehouse_service.py` | `warehouses`, `warehouse_nodes`, `warehouse_edges` | Canvas Node/Edge Data |
| **Batching** | `WarehousePage.tsx` | `POST /api/v1/batches/optimize` | `warehouse_optimization_service.py` | `orders`, `batches`, `batch_orders` | Optimized Batches |
| **Pick Routing** | `WarehousePage.tsx` | Included in batch optimization | `pick_routing_engine.py` | `pick_routes`, `pick_route_steps` | Sequential Pick Path |
| **Create Delivery**| `DeliveriesPage.tsx` | `POST /api/v1/deliveries` | `delivery_service.py` | `deliveries` | Delivery Record |
| **Dispatch / Route**| `DeliveryDetailPage.tsx`| `POST /api/v1/deliveries/{id}/route`| `routing_service.py` | `deliveries` | Polyline & Calculated ETA |
| **Telemetry** | External API / Form | `POST /api/v1/telemetry` | `telemetry_service.py` | `telemetry_events` | Ingested Point Record |
| **Safety Analysis** | Automatic trigger | Internal function call | `safety_service.py` | `safety_events`, `safety_scores`, `safety_alerts` | Score update & Alert |
| **EV Recommend** | `ChargingOptimizePage.tsx`| `POST /api/v1/charging/recommend`| `ev_charging_optimization_service.py`| Read-only stations/slots | Ranked Recommendations |
| **Slot Reservation**| `ChargingPage.tsx` | `POST /api/v1/charging/reservations`| `charging_service.py` | `charging_reservations`, `charging_slots` | Confirmed Reservation |
