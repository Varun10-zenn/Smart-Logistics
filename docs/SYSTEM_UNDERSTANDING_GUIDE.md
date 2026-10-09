# Smart Logistics Platform — System Understanding Guide

## 1. High-Level Platform Overview
The Smart Logistics Platform is an enterprise-grade logistics and dark-store management system designed to handle end-to-end supply chain execution. It covers four primary domain modules:
1. **Warehouse Module**: Dark-store topological graph modeling, stock checking, order batching optimization (Next-Fit / Capacity & Volume constrained), and pick route optimization (Dijkstra shortest paths + 2-opt TSP route smoothing).
2. **Deliveries Module**: Fleet dispatch, driver and vehicle assignment, route generation (OSRM integration with haversine fallback), and traffic/weather multi-factor ETA calculation.
3. **Safety Module**: Real-time driver telemetry ingestion, event threshold detection (speeding, harsh braking, harsh acceleration, route deviation), dynamic 0-100 penalty safety scoring, and real-time safety alert generation.
4. **EV Charging Module**: EV fleet energy management, SoC monitoring, multi-attribute charging recommendation ranking, and atomic slot reservation (`SELECT FOR UPDATE` + overlap checking) to prevent double-booking.

---

## 2. End-to-End Data Flow (User → React → FastAPI → Service → MySQL → User)

```
[ USER ACTION ]
      │
      ▼
[ REACT FRONTEND ] ──── (State, Components, TanStack Query)
      │
      ▼
[ AXIOS HTTP CLIENT ] ── (JWT Bearer Token in Authorization Header)
      │
      ▼
[ FASTAPI ROUTER ] ──── (Prefix: /api/v1/..., Route Handlers)
      │
      ▼
[ AUTH & RBAC DEPENDENCY ] ── (require_role("admin", ...), decode_token)
      │
      ▼
[ PYDANTIC SCHEMA ] ─── (Payload validation & type coercion)
      │
      ▼
[ SERVICE / ENGINE ] ── (Domain logic: OrderBatcher, PickRoutingEngine, SafetyService)
      │
      ▼
[ SQLALCHEMY ORM ] ─── (Db session, queries, transactional commit/rollback)
      │
      ▼
[ DATABASE (MySQL/SQLite) ] ─ (Atomically persists/reads relational tables)
      │
      ▼
[ API RESPONSE SCHEMAS ] ─── (Standardized JSON payload returned to React)
      │
      ▼
[ REACT FRONTEND UI ] ────── (State update & dynamic visual render)
```

### Flow Breakdown per Component:
1. **User Action**: User clicks a button in React (e.g., "Run Batch Optimization").
2. **React Frontend (`src/pages/WarehousePage.tsx`)**: Calls query mutation via API service (`src/api/warehouseApi.ts`).
3. **Axios Client (`src/lib/axios.ts`)**: Attaches `Authorization: Bearer <jwt_token>` from `localStorage` (`token` key).
4. **FastAPI Router (`backend/app/api/v1/batches.py`)**: Intercepts HTTP `POST /api/v1/batches/optimize`.
5. **Auth/RBAC (`backend/app/core/security.py`)**: `require_role("admin", "warehouse_operator")` decodes token, validates JTI against `denylist`, and verifies user role.
6. **Pydantic Validation (`backend/app/schemas/batch.py`)**: Validates input body against `BatchOptimizeRequest`.
7. **Service Layer (`backend/app/services/warehouse_optimization_service.py`)**: Orchestrates stock map queries, `OrderBatchingEngine`, `PickRouteOptimizationEngine`, and `GraphEngine`.
8. **SQLAlchemy ORM (`backend/app/models/batch.py`)**: Inserts `batches`, `batch_orders`, `pick_routes`, `pick_route_steps`, and updates `orders.status = 'batched'`.
9. **MySQL Database**: Executes atomic transaction (`db.commit()`).
10. **Response**: FastAPI serializes `WarehouseOptimizationResultDTO` into JSON response.
11. **Frontend Update**: TanStack Query invalidates order/batch queries; React re-renders dark-store canvas and batch summary lists.

---

## 3. Module Deep-Dives

### A. Warehouse Module (`/warehouse`)
- **React Components**: `WarehousePage.tsx`, `WarehouseGraphCanvas.tsx`, `OrderBatchList.tsx`, `PickRouteDetails.tsx`.
- **Graph Algorithm**: Dark-store topology built using NetworkX (`GraphEngine.load_warehouse_graph`). Computes pairwise distances between all picking locations using **Dijkstra's Algorithm**. Route ordering for picked items is solved using **2-opt Traveling Salesperson Problem (TSP) heuristic** to minimize picker walking distance.
- **Batching Algorithm**: `OrderBatcher.batch_priority_heuristic` groups pending orders by priority and SLA deadline while enforcing weight capacity (`max_weight_kg`), volume constraints (`max_volume_cbm`), and max item count per batch.

### B. Delivery Module (`/deliveries`)
- **React Components**: `DeliveriesPage.tsx`, `DeliveryDetailPage.tsx`, `DeliveryFormModal.tsx`, `DriverAssignModal.tsx`.
- **Routing Engine**: `routing_service.py` calls OSRM public API or falls back to Haversine distance calculations.
- **ETA Formula**: 
  $$\text{ETA} = \text{base\_travel\_time} \times \text{traffic\_factor} \times \text{weather\_factor}$$
  Where traffic factors range from `1.0` (smooth) to `1.5` (heavy), and weather factors range from `1.0` (clear) to `1.3` (stormy).

### C. Safety Module (`/safety`)
- **React Components**: `SafetyPage.tsx`, `SafetyScoreCard.tsx`, `SafetyAlertList.tsx`, `TelemetryLogTable.tsx`.
- **Telemetry Processing**: Ingested via `POST /api/v1/telemetry`.
- **Threshold Rules**:
  - Speeding: Speed > 80.0 km/h (Penalty: 2.0 pts)
  - Harsh Braking: Acceleration < -4.0 $m/s^2$ (Penalty: 3.0 pts)
  - Harsh Acceleration: Acceleration > 4.0 $m/s^2$ (Penalty: 1.5 pts)
  - Route Deviation: Distance from planned path > 1.0 km (Penalty: 2.0 pts)
- **Score Formula**: Starts at 100.0. Penalties subtract points per event type. Final score is the arithmetic mean of 4 component scores (Speed, Braking, Acceleration, Route Adherence). Alert created if score < 70.0.

### D. EV Charging Module (`/charging`)
- **React Components**: `ChargingPage.tsx`, `ChargingOptimizePage.tsx`, `StationMap.tsx`, `ReservationModal.tsx`.
- **Recommendation Scoring**: `ev_charging_optimization_service.py` filters candidates by distance and connector compatibility, then ranks them using a weighted multi-attribute formula considering distance, power output, wait time, and cost.
- **Atomic Reservation**: `create_reservation` in `charging_service.py` locks the connector row using `SELECT FOR UPDATE` to serialize bookings and checks for time overlaps (`has_charging_reservation_overlap`), preventing double-booking.

---

## 4. AI & Intelligence Layer (`AGENTS.md` vs Source Code)
- **Architecture**: `WarehouseOptimizationAgent` and `DeliverySafetyAgent` act as orchestrators and explanation generators.
- **Source Truth**: Operations (batching, routing, safety scoring, EV recommendation) are **100% deterministic algorithms**. If an LLM client is configured, it is called solely to generate natural language explanations from deterministic output. If no LLM is present, the agents fall back to rule-based template explanations.
