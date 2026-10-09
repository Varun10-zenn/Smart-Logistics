# ARCHITECTURE.md

**Project:** AI-Driven Smart Logistics Platform  
**Version:** 1.0  
**Target:** 80% academic prototype

---

# 1. Architectural Decision Summary

The recommended architecture is a **modular monolith with independently deployable AI/optimization services**, rather than starting with a large microservice system.

### Why

A completely distributed microservice architecture adds unnecessary complexity for an academic project. The system still needs clear module boundaries, APIs, and replaceable intelligence components.

Recommended structure:

```text
                 ┌──────────────────────────┐
                 │        Web / Mobile      │
                 │ React / Responsive UI    │
                 └────────────┬─────────────┘
                              │ REST/WebSocket
                 ┌────────────▼─────────────┐
                 │      API / Gateway       │
                 │ Auth + RBAC + Validation │
                 └────────────┬─────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐   ┌────────▼────────┐   ┌───────▼─────────┐
│ Warehouse      │   │ Delivery/Safety │   │ EV Charging     │
│ Module         │   │ Module          │   │ Module          │
└───────┬────────┘   └────────┬────────┘   └───────┬─────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │ Intelligence      │
                    │ Orchestrator      │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐   ┌────────▼────────┐   ┌───────▼─────────┐
│ Optimization   │   │ ML Prediction   │   │ LLM/Agent       │
│ OR-Tools/A*    │   │ Models          │   │ Reasoning       │
└────────────────┘   └─────────────────┘   └─────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │ PostgreSQL/MySQL  │
                    │ Redis (optional)  │
                    └───────────────────┘
```

---

# 2. Intelligence Architecture

Do NOT make one LLM responsible for every logistics decision.

Use a hybrid intelligence stack:

| Problem | Recommended intelligence |
|---|---|
| Warehouse shortest path | A*/Dijkstra |
| Picking sequence | OR-Tools / routing optimization |
| Order batching | Constraint optimization / clustering |
| Demand forecast | XGBoost/LightGBM baseline or time-series model |
| ETA | Regression/ML + route/traffic features |
| Safety Score | Deterministic scoring + anomaly detection |
| Route deviation | Geospatial calculation |
| EV station selection | Multi-objective optimization |
| Charging slot assignment | Constraint optimization |
| Queue prediction | Regression/time-series model |
| Natural-language explanation | LLM |
| Cross-module orchestration | AI agent layer |

The LLM should explain, coordinate, validate and summarize decisions rather than replace mathematical optimization.

---

# 3. Recommended Technology Stack

## Frontend

- React
- TypeScript
- Tailwind CSS
- Recharts
- Leaflet or another map abstraction
- WebSocket/SSE for simulated real-time updates

## Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL or MySQL
- Redis optional

## AI/Optimization

- scikit-learn
- XGBoost or LightGBM
- OR-Tools
- NetworkX
- NumPy/Pandas
- optional PyTorch for advanced models

## Agent layer

Use a small Python orchestration layer with typed tools.

An agent should call functions such as:

```text
get_orders()
optimize_batches()
optimize_pick_route()
get_vehicle_state()
calculate_safety_score()
get_charging_stations()
predict_wait_time()
reserve_charging_slot()
```

The agent must not directly write arbitrary SQL or bypass validation.

## LLM

Use an API-based or locally hosted instruction model behind an abstraction:

```text
LLMProvider
 ├── OpenAI-compatible provider
 ├── local model provider
 └── mock provider
```

This makes the project provider-independent.

---

# 4. Repository Architecture

```text
smart-logistics/
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── services/
│   │   ├── hooks/
│   │   └── types/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── modules/
│   │   │   ├── warehouse/
│   │   │   ├── delivery/
│   │   │   └── charging/
│   │   └── main.py
│
├── intelligence/
│   ├── agents/
│   ├── optimization/
│   ├── forecasting/
│   ├── safety/
│   ├── eta/
│   ├── charging/
│   └── providers/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── seed/
│
├── tests/
├── docs/
├── scripts/
├── docker/
├── .env.example
└── README.md
```

---

# 5. Domain Data Model

```text
Warehouse
 ├── WarehouseNode
 ├── WarehouseEdge
 ├── Product
 ├── Inventory
 └── Order
       └── OrderItem
             │
             ▼
           Batch
             │
             ▼
        PickTask
             │
             ▼
         Delivery
        /        \
     Rider       Vehicle
                    │
             TelemetryEvent
                    │
             SafetyEvent
                    │
                  Route
                    │
                    ▼
             ChargingNeed
                    │
                    ▼
          ChargingReservation
                    │
                    ▼
          ChargingStation
```

---

# 6. Database Schema

## users

```text
id PK
name
email UNIQUE
password_hash
role
is_active
created_at
```

## warehouses

```text
id PK
name
latitude
longitude
status
```

## warehouse_nodes

```text
id PK
warehouse_id FK
node_code
x
y
zone
```

## warehouse_edges

```text
id PK
warehouse_id FK
from_node_id FK
to_node_id FK
distance
blocked
```

## products

```text
id PK
sku UNIQUE
name
category
weight
volume
```

## inventory

```text
id PK
warehouse_id FK
product_id FK
node_id FK
quantity
reorder_level
```

## orders

```text
id PK
warehouse_id FK
customer_lat
customer_lon
created_at
promised_at
priority
status
```

## order_items

```text
id PK
order_id FK
product_id FK
quantity
```

## batches

```text
id PK
warehouse_id FK
capacity
deadline
status
created_at
```

## batch_items

```text
id PK
batch_id FK
order_id FK
```

## deliveries

```text
id PK
batch_id FK
rider_id FK
vehicle_id FK
route_id FK
eta
status
```

## telemetry_events

```text
id PK
vehicle_id FK
timestamp
latitude
longitude
speed
acceleration
braking
heading
```

## safety_events

```text
id PK
delivery_id FK
event_type
severity
timestamp
latitude
longitude
value
threshold
```

## safety_scores

```text
id PK
delivery_id FK
score
speed_score
braking_score
acceleration_score
route_score
calculated_at
```

## vehicles

```text
id PK
registration_no
vehicle_type
is_ev
battery_capacity_kwh
soc_percent
consumption_kwh_per_km
status
```

## charging_stations

```text
id PK
name
latitude
longitude
status
total_connectors
```

## charging_connectors

```text
id PK
station_id FK
connector_type
power_kw
status
```

## charging_reservations

```text
id PK
connector_id FK
vehicle_id FK
start_time
end_time
status
```

## forecasts

```text
id PK
forecast_type
entity_id
forecast_time
predicted_value
lower_bound
upper_bound
model_name
model_version
created_at
```

## recommendations

```text
id PK
agent_name
recommendation_type
input_snapshot
output
explanation
confidence
model_version
created_at
```

---

# 7. API Specification

## Warehouse

### GET /api/warehouses/{id}

Returns warehouse information and map.

### POST /api/orders

Create order.

### POST /api/warehouse/batches/optimize

Request:

```json
{
  "warehouse_id": 1,
  "order_ids": [101, 102, 103],
  "max_orders_per_batch": 5,
  "deadline_weight": 0.4,
  "distance_weight": 0.4,
  "capacity_weight": 0.2
}
```

### POST /api/warehouse/picking/optimize

Returns:

```json
{
  "batch_id": 22,
  "sequence": ["N01", "N04", "N08", "N03"],
  "distance": 124.5,
  "estimated_minutes": 8.4
}
```

---

# 8. Delivery API

### POST /api/deliveries

Create delivery from batch.

### POST /api/routes/optimize

Input:

```json
{
  "origin": [12.9, 80.2],
  "destination": [13.0, 80.25],
  "traffic_factor": 1.2,
  "weather_factor": 1.1
}
```

### POST /api/safety/events

Telemetry/safety event ingestion.

### GET /api/deliveries/{id}/safety-score

Returns:

```json
{
  "score": 82,
  "speed_compliance": 91,
  "braking": 78,
  "acceleration": 86,
  "route_adherence": 73
}
```

---

# 9. EV API

### GET /api/charging/stations

Returns stations, connectors and availability.

### POST /api/charging/recommend

Input:

```json
{
  "vehicle_id": 12,
  "current_soc": 24,
  "required_soc": 60,
  "destination": [13.02, 80.25],
  "current_location": [12.98, 80.22]
}
```

Recommendation score:

```text
score =
  w1 * normalized_distance
+ w2 * normalized_wait
+ w3 * normalized_price
+ w4 * route_detour
+ w5 * availability_risk
```

Lower score is better.

### POST /api/charging/reservations

Must execute an atomic availability check before insertion.

---

# 10. Shared Intelligence API

### POST /api/intelligence/recommend

```json
{
  "domain": "charging",
  "task": "recommend_station",
  "context": {}
}
```

Response:

```json
{
  "recommendation": {},
  "explanation": "...",
  "confidence": 0.88,
  "agent": "ev_charging_agent",
  "algorithm": "multi_objective_v1"
}
```

---

# 11. Event Flow

```text
Order Created
     │
     ▼
Warehouse Agent
     │
     ├── batch orders
     └── optimize pick sequence
             │
             ▼
        Delivery Created
             │
             ▼
       Delivery Agent
             │
       ┌─────┴─────┐
       ▼           ▼
   ETA Update   Safety Monitor
       │           │
       └─────┬─────┘
             ▼
        EV Decision
             │
             ▼
       Charging Agent
             │
       ┌─────┴─────┐
       ▼           ▼
 Recommend      Reserve
 station          slot
```

---

# 12. Cross-Module Intelligence

Shared context should include:

```json
{
  "order": {},
  "batch": {},
  "delivery": {},
  "vehicle": {},
  "route": {},
  "safety": {},
  "battery": {},
  "charging": {},
  "weather": {},
  "traffic": {}
}
```

The intelligence layer can use this context to make decisions without duplicating data.

---

# 13. Agent Decision Boundary

Agents can:

- inspect approved data;
- call registered tools;
- calculate recommendations;
- explain decisions;
- request actions.

Agents cannot:

- execute arbitrary code;
- directly alter database tables;
- bypass authorization;
- reserve a charger without validation;
- override safety rules;
- silently change scoring formulas.

High-impact actions should follow:

```text
Agent recommendation
       ↓
Validation
       ↓
Business rules
       ↓
Optional human approval
       ↓
Action
       ↓
Audit log
```

---

# 14. Real-Time Architecture

For prototype:

```text
Simulator
   ↓
Telemetry API
   ↓
Safety/ETA services
   ↓
WebSocket/SSE
   ↓
Dashboard
```

Use simulated telemetry to demonstrate real-time behavior without requiring actual vehicle hardware.

---

# 15. Cloud Recommendation

For the academic 80% version:

### Option A — simplest

One VM/container deployment:

```text
Frontend
Backend
Intelligence
Database
```

### Option B — better demonstration

Docker Compose:

```text
frontend
backend
intelligence
postgres
redis
```

### Future production architecture

Use managed database, object storage, container orchestration, monitoring, queue/event infrastructure and autoscaling.

Do not build the production cloud complexity before the core prototype works.

---

# 16. Observability

Every recommendation should log:

```text
request_id
agent
task
input_hash
algorithm/model
model_version
latency_ms
result
confidence
fallback_used
timestamp
```

Track:

- API latency
- model latency
- optimization duration
- failed recommendations
- fallback count
- safety alerts
- reservation conflicts

---

# 17. Security Architecture

```text
User
 ↓
Authentication
 ↓
JWT/session
 ↓
RBAC middleware
 ↓
API validation
 ↓
Domain service
 ↓
Database
```

Secrets:

```text
.env
```

Never:

```text
API_KEY = "..."
```

inside source code.

---

# 18. Implementation Milestones

### 0–20%

- repo
- DB
- auth
- seed data
- backend skeleton

### 20–40%

- warehouse
- orders
- batches
- picking optimization
- basic UI

### 40–55%

- delivery
- routing
- telemetry
- safety scoring

### 55–70%

- EV
- station management
- recommendation
- reservation

### 70–80%

- AI agents
- dynamic dashboard
- integration
- testing
- demo scenarios
- documentation

---

# 19. Architecture Acceptance Criteria

Architecture is ready when:

- modules have defined boundaries;
- APIs are documented;
- database relationships are implemented;
- every AI component has a deterministic fallback;
- cross-module flow works;
- model versions are traceable;
- security boundaries exist;
- the application can run locally using demo data.
