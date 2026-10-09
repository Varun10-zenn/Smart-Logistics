# Smart Logistics Platform — Architecture & Operational Workflow Document

---

## 1. Why Data Was Not Displaying & How It Was Resolved

### Initial Cause
1. **Empty Local Database**: The SQLite fallback database (`smart_logistics_fallback.db`) did not have seeded records populated.
2. **Strict RBAC Enforcement**: Role-Based Access Control (RBAC) restricts endpoints like `/api/v1/deliveries` to authorized roles (`admin`, `fleet_manager`, `driver`). When non-delivery roles loaded dashboard widgets, requests without permission returned `403 Forbidden` errors.

### Resolution Applied
1. **Database Seeding**: Executed database initialization script (`scripts/reinit_db.py`) to generate records for all domain entities across all 5 user roles.
2. **Frontend Optimization**: Added explicit role-permission checks on the frontend (`DashboardPage.tsx`) so widgets gracefully display relevant cards or access restriction notices.

---

## 2. Platform Architecture Overview

The **AI-Driven Smart Logistics Platform** is built with a modular, 3-tier architecture:

```
                  ┌─────────────────────────────────────┐
                  │   React / TypeScript UI (Vite)     │
                  │   Dashboard & Module Management     │
                  └──────────────────┬──────────────────┘
                                     │ REST API / JWT
                                     ▼
                  ┌─────────────────────────────────────┐
                  │    FastAPI Application (Python)     │
                  │    RBAC Middleware / Services       │
                  └──────────────────┬──────────────────┘
                                     │ ORM (SQLAlchemy)
                                     ▼
                  ┌─────────────────────────────────────┐
                  │   Database Layer (SQLite / MySQL)   │
                  │   Structured Domain Schema          │
                  └─────────────────────────────────────┘
```

---

## 3. Module Mechanics & Functions

### 🔑 1. Identity & RBAC Module
- **Purpose**: Authenticates users using JWT Bearer tokens and enforces role-based authorization rules across API endpoints.
- **Roles**:
  - `admin`: Full platform administration and access to audit logs.
  - `warehouse_operator`: Manages products, inventory, orders, batching, and picking.
  - `fleet_manager`: Monitors vehicles, drivers, active deliveries, and safety alerts.
  - `driver`: Views personal delivery assignments, safety scores, and route details.
  - `station_admin`: Oversees EV charging stations, connectors, slots, and reservations.

---

### 🏭 2. Warehouse Optimization Module
- **Purpose**: Manages multi-warehouse node/edge graphs, product catalog, inventory levels, order creation, order batching, and optimal pick-route generation.
- **Workflow**:
  - **Orders**: Customer orders with priority levels (`urgent`, `high`, `normal`, `low`) and promised SLA deadlines.
  - **Batching Engine**: Groups pending orders into optimal batches based on capacity, SLA deadlines, and location.
  - **Pick Routing Engine**: Uses graph traversal algorithms (A* / TSP solver) to produce optimal picking routes for warehouse pickers.

---

### 🚚 3. Delivery & Routing Module
- **Purpose**: Handles dispatching, real-time ETA calculation, and status progression of deliveries.
- **Workflow**:
  - Batches are assigned to available **Drivers** and **Vehicles**.
  - Dispatch triggers dynamic route generation with real-time ETA factor adjustments (traffic and weather multipliers).
  - Status transitions: `assigned` ➔ `dispatched` ➔ `in_transit` ➔ `completed`.

---

### ⚡ 4. EV Charging Management Module
- **Purpose**: Manages EV vehicle State of Charge (SoC), charging station connectors, slot schedules, and intelligent charging reservation recommendations.
- **Workflow**:
  - Tracks vehicle SoC levels (`current_soc_percent`).
  - Recommends optimal charging slots for EV delivery vehicles during or between trips.
  - Transactional overlap protection prevents double-booking of charging connectors.

---

### 🛡️ 5. Safety & Telemetry Module
- **Purpose**: Ingests vehicle telemetry events (speed, location, acceleration, braking) and evaluates driver safety metrics.
- **Workflow**:
  - Evaluates telemetry data against safety thresholds.
  - Generates safety scores (0–100 scale) per delivery.
  - Triggers real-time **Safety Alerts** for severe events (e.g., sudden braking, overspeeding).

---

### 🧠 6. Intelligence & AI Orchestration Module
- **Purpose**: Provides automated recommendations and demand/delivery forecasting across all operational modules.
- **Operations**:
  - `warehouse_batch_recommendation`: AI-suggested batch assignments.
  - `ev_charging_recommendation`: Optimal charging slot allocation.
  - Fallback mechanisms ensure continuous service even if AI service backends are offline.

---

## 4. End-to-End Operational Workflow

```
 1. Order Creation     ➔   2. Batching        ➔   3. Pick Optimization
    (Customer Order)         (Group Orders)         (Generate Pick Route)
           │                       │                         │
           ▼                       ▼                         ▼
 6. Delivery Completed ◄─ 5. Transit & Safety ◄─  4. Dispatch & Route
    (Status Updated)        (Telemetry & Alerts)    (Driver & EV Assigned)
                                   │
                                   ▼
                         7. EV Charging Slot
                            (Reservation & Charge)
```

1. **Order Reception**: Orders enter the system assigned to a specific warehouse hub.
2. **Order Batching**: Warehouse operators run batch optimization to cluster orders.
3. **Picking Execution**: Pick routes are calculated for warehouse operators to gather goods.
4. **Dispatch**: Delivery created from batch, assigned to driver & EV vehicle.
5. **In-Transit Telemetry**: Real-time telemetry is streamed, calculating ETAs and safety scores.
6. **Charging Management**: If battery drops below threshold, charging slots are reserved and utilized.
7. **Delivery Fulfillment**: Delivery completes and driver status resets to available.

---

## 5. Seed Test Credentials

You can log into the web application using any of the following pre-configured credentials:

| Role | Email Address | Password | Permissions Summary |
|---|---|---|---|
| **Admin** | `admin@smartlogistics.com` | `test1234` | Full access across all modules |
| **Warehouse Operator** | `warehouse@smartlogistics.com` | `test1234` | Warehouses, Inventory, Orders, Batches |
| **Fleet Manager** | `fleet@smartlogistics.com` | `test1234` | Vehicles, Drivers, Deliveries, Safety |
| **Driver** | `driver@smartlogistics.com` | `test1234` | Personal Delivery & Safety Details |
| **Station Admin** | `station@smartlogistics.com` | `test1234` | EV Charging Stations & Slots |
