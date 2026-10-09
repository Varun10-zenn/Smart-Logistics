# PROJECT_REQUIREMENTS.md

**Project:** AI-Driven Smart Logistics Platform for Warehouse Optimization, Delivery Safety, and EV Charging Management  
**Domain:** AI-Powered Smart Logistics and Sustainable Transportation  
**Target completion:** 80% functional prototype  
**Document version:** 1.0  
**Baseline source:** SWE3004 Review-0 project document, Fall Semester 2026–27

---

## 1. Purpose

This document converts the Review-0 concept into implementation-ready requirements for an 80%-complete academic prototype.

The Review-0 concept combines three areas:

1. Warehouse Optimization
2. Delivery Safety
3. EV Charging Management

The platform is intended to share a common operational data model so that warehouse decisions, delivery decisions, vehicle state, safety information, routes, and charging decisions can influence one another.

The Review-0 document specifically describes indoor picking optimization, intelligent order batching, demand forecasting, dynamic ETA, rider Safety Score, real-time EV charging availability, charging-slot reservation, waiting-time prediction, and route-integrated charging recommendations.

---

## 2. Product Vision

Build one web-based logistics control platform with:

- a common operational database,
- optimization services,
- ML prediction services,
- a lightweight AI-agent orchestration layer,
- real-time dashboards,
- explainable recommendations,
- simulation/demo data for scenarios where live integrations are unavailable.

### 80% completion definition

The prototype is considered 80% complete when a user can:

- create/import warehouse orders;
- visualize a warehouse map;
- generate optimized picking sequences;
- batch orders using operational constraints;
- estimate demand for upcoming periods;
- create deliveries from selected batches;
- calculate routes and dynamic ETA;
- calculate and monitor a delivery Safety Score;
- register vehicles and their battery state;
- view EV charging stations and availability;
- recommend charging stations/slots;
- reserve a charging slot in the prototype;
- view cross-module dashboards;
- see AI/optimization recommendations with explanations;
- inspect historical metrics;
- demonstrate at least 3 end-to-end scenarios.

---

# 3. Scope

## 3.1 In scope

### Warehouse Optimization
- Warehouse/dark-store map
- Product/SKU locations
- Order ingestion
- Picking route optimization
- Order batching
- Picker assignment
- Pick-list generation
- Batch status tracking
- Basic demand forecasting
- Inventory positioning recommendation
- Warehouse KPI dashboard

### Delivery Safety
- Delivery creation
- Rider/driver and vehicle records
- Route planning
- Traffic/weather input abstraction
- ETA calculation
- Dynamic ETA updates
- Speed-compliance monitoring
- Harsh-braking/acceleration events
- Route-deviation detection
- Safety Score
- Safety alerts
- Delivery KPI dashboard

### EV Charging Management
- EV registration
- State-of-charge tracking
- Charging-station registry
- Connector/slot availability
- Queue/wait-time estimate
- Charging recommendation
- Charging-slot reservation
- Route-aware charging decision
- Charging KPI dashboard

### Shared platform
- Authentication and role-based access
- Common order/vehicle/route data model
- Notifications
- Audit logs
- AI recommendation history
- REST APIs
- Dashboard
- Scenario simulation

## 3.2 Out of scope for the 80% prototype

These may be future extensions:

- production-grade autonomous driving;
- direct vehicle ECU control;
- guaranteed real-time third-party traffic feeds;
- physical charging-station control;
- nationwide logistics deployment;
- fully autonomous agent actions without approval;
- custom foundation-model training;
- production-grade fleet-scale optimization;
- legally certified safety scoring.

---

# 4. Stakeholders and Personas

| Stakeholder | Main needs | Main interface |
|---|---|---|
| Warehouse operator | Pick lists, optimized paths, batch status | Warehouse dashboard/tablet |
| Delivery driver/rider | Route, ETA, safety alerts, charging guidance | Mobile UI |
| Fleet manager | Fleet state, safety, ETA, exceptions | Operations dashboard |
| EV station administrator | Station/slot/queue state | Charging dashboard |
| Project administrator | Configuration, users, datasets, audit | Admin console |
| Guide/evaluator | Demonstrable metrics and workflows | Demo dashboard/reports |

---

# 5. Functional Requirements

Priority:
- **P0:** mandatory for 80%
- **P1:** important enhancement
- **P2:** future/nice-to-have

## 5.1 Authentication and RBAC

| ID | Requirement | Priority |
|---|---|---|
| AUTH-01 | User login/logout | P0 |
| AUTH-02 | Roles: admin, warehouse_operator, driver, fleet_manager, station_admin | P0 |
| AUTH-03 | Restrict dashboard/API access by role | P0 |
| AUTH-04 | Store audit events for important actions | P1 |

## 5.2 Warehouse

| ID | Requirement | Priority |
|---|---|---|
| WH-01 | Create/import products and SKU locations | P0 |
| WH-02 | Create/import customer orders | P0 |
| WH-03 | Represent warehouse as nodes/edges | P0 |
| WH-04 | Generate optimized picking sequence | P0 |
| WH-05 | Generate batch groups from orders | P0 |
| WH-06 | Consider capacity/deadline/proximity in batching | P0 |
| WH-07 | Assign batches to available pickers | P1 |
| WH-08 | Forecast demand by time period | P0 |
| WH-09 | Recommend inventory positioning | P1 |
| WH-10 | Track batch/pick completion | P0 |
| WH-11 | Show warehouse KPIs | P0 |

## 5.3 Delivery Safety

| ID | Requirement | Priority |
|---|---|---|
| DEL-01 | Create delivery from warehouse batch | P0 |
| DEL-02 | Store origin/destination and route | P0 |
| DEL-03 | Calculate route distance/time | P0 |
| DEL-04 | Update ETA using traffic/weather inputs | P0 |
| DEL-05 | Receive/store telemetry events | P0 |
| DEL-06 | Detect speeding | P0 |
| DEL-07 | Detect harsh braking/acceleration | P0 |
| DEL-08 | Detect route deviation | P0 |
| DEL-09 | Calculate Safety Score | P0 |
| DEL-10 | Generate safety alerts | P0 |
| DEL-11 | Show route and delivery status | P0 |
| DEL-12 | Store safety history | P0 |

## 5.4 EV Charging

| ID | Requirement | Priority |
|---|---|---|
| EV-01 | Register EVs and battery specifications | P0 |
| EV-02 | Track current State of Charge | P0 |
| EV-03 | Register stations/connectors/slots | P0 |
| EV-04 | Track availability | P0 |
| EV-05 | Estimate queue/wait time | P0 |
| EV-06 | Recommend charging station | P0 |
| EV-07 | Recommend charging slot | P0 |
| EV-08 | Reserve slot | P0 |
| EV-09 | Include route impact in recommendation | P0 |
| EV-10 | Show charging dashboard | P0 |
| EV-11 | Predict future demand/queue | P1 |

## 5.5 AI/Recommendation layer

| ID | Requirement | Priority |
|---|---|---|
| AI-01 | Expose common recommendation API | P0 |
| AI-02 | Use specialized models/optimizers per problem | P0 |
| AI-03 | Store recommendation input/output | P0 |
| AI-04 | Explain major recommendation factors | P0 |
| AI-05 | Apply validation/business rules before action | P0 |
| AI-06 | Support fallback to deterministic algorithms | P0 |
| AI-07 | Track model/version used | P1 |

---

# 6. Non-Functional Requirements

## Performance targets

These are prototype engineering targets, not claims about the final production system.

| Area | Target |
|---|---|
| Normal REST API response | p95 < 500 ms |
| Simple optimization request | < 3 s |
| Batch optimization | < 10 s for demo dataset |
| Forecast generation | < 5 s |
| Dashboard initial load | < 3 s on local/demo deployment |
| Safety event processing | < 1 s/event target |
| Charging recommendation | < 2 s |
| Reservation transaction | < 1 s excluding network latency |
| UI update interval | 2–5 s for simulated real-time state |

## Reliability

- Validate all incoming data.
- Never allow invalid SoC values outside 0–100%.
- Prevent double-booking of charging slots.
- Keep audit records for reservations and critical recommendations.
- Provide fallback behavior when ML/LLM services fail.

## Security

- JWT/session-based authentication.
- Password hashing.
- RBAC.
- Server-side input validation.
- API rate limiting where appropriate.
- Secrets in environment variables.
- No API keys committed to Git.
- Parameterized SQL/ORM queries.
- Audit logs for privileged actions.

## Maintainability

- Modular services.
- Versioned APIs.
- Configuration through environment variables.
- Unit tests for core algorithms.
- Separate domain logic from UI.
- Model versions recorded with predictions.

---

# 7. Data Requirements

## 7.1 Core entities

- users
- warehouses
- warehouse_nodes
- warehouse_edges
- products
- inventory
- orders
- order_items
- batches
- batch_items
- pick_tasks
- pickers
- deliveries
- riders
- vehicles
- telemetry_events
- safety_events
- routes
- weather_observations
- traffic_observations
- charging_stations
- charging_connectors
- charging_slots
- charging_reservations
- forecasts
- recommendations
- alerts
- audit_logs

## 7.2 Minimum fields

### Order

`id, customer_id, warehouse_id, created_at, promised_at, priority, status, latitude, longitude`

### Order item

`id, order_id, product_id, quantity`

### Product

`id, sku, name, category, weight, volume`

### Inventory

`id, warehouse_id, product_id, quantity, reorder_level, node_id`

### Batch

`id, warehouse_id, status, capacity, deadline, created_at`

### Delivery

`id, batch_id, rider_id, vehicle_id, origin, destination, route_id, eta, status`

### Telemetry

`id, vehicle_id, timestamp, latitude, longitude, speed, acceleration, braking, heading`

### EV

`id, vehicle_id, battery_capacity_kwh, soc_percent, consumption_kwh_per_km`

### Charging station

`id, name, latitude, longitude, total_connectors, available_connectors, status`

### Reservation

`id, station_id, connector_id, vehicle_id, start_time, end_time, status`

---

# 8. Data Quality Rules

- timestamps must use one canonical timezone internally;
- latitude/longitude must be validated;
- duplicate telemetry events should be detected;
- missing telemetry must not automatically become a safety violation;
- missing traffic/weather values should trigger fallback behavior;
- order quantities must be positive;
- battery SoC must remain within 0–100%;
- charging reservation intervals must not overlap for one connector;
- model predictions must retain model/version metadata.

---

# 9. Integration Points

## Internal APIs

- `/api/auth`
- `/api/warehouse`
- `/api/orders`
- `/api/batches`
- `/api/picking`
- `/api/demand`
- `/api/routes`
- `/api/deliveries`
- `/api/safety`
- `/api/vehicles`
- `/api/charging`
- `/api/recommendations`
- `/api/alerts`
- `/api/dashboard`

## External integration abstraction

The architecture should isolate providers behind adapters:

- Maps/routing provider
- Weather provider
- Traffic provider
- Charging-station provider
- ML model provider
- LLM provider

For the academic prototype, every external dependency must have a simulated/local fallback.

---

# 10. Success Criteria

## Warehouse

- Optimized route is generated for a test order set.
- System displays pick sequence visually.
- Batching produces valid groups under configured constraints.
- Forecast endpoint returns a forecast and confidence/error metric.
- Dashboard reports picking/batching KPIs.

## Delivery

- Delivery route is generated.
- ETA changes when traffic/weather scenario changes.
- Speeding, harsh braking and route deviation are detected.
- Safety Score changes according to documented rules.
- Dashboard displays active alerts.

## EV

- EV SoC is tracked.
- Stations and availability are displayed.
- Queue/wait time is calculated or simulated.
- System recommends a station using distance, availability, wait and SoC.
- Slot reservation prevents conflicting reservations.

## Platform

- One order can progress from warehouse → batch → delivery → vehicle → charging.
- AI/optimization services can be called through documented APIs.
- Recommendation explanations are visible.
- System remains usable if an AI/LLM provider is unavailable.

---

# 11. KPI Definitions

### Warehouse

`Picking Efficiency = Orders Completed / Picker Hour`

`Average Picking Distance = Total Picking Distance / Completed Batches`

`Batch Utilization = Assigned Items / Batch Capacity`

### Delivery

`ETA Error = |Predicted ETA - Actual ETA|`

`Safety Score = 100 - weighted safety penalties`

Suggested initial penalty weights:

- speeding: 30%
- harsh braking: 25%
- harsh acceleration: 15%
- route deviation: 30%

These weights are prototype configuration values and must be configurable.

### EV

`Charging Wait Time = Actual/Predicted Start - Arrival Time`

`Charging Utilization = Occupied Connector Time / Available Connector Time`

`Energy Efficiency = Delivered Energy / Charging Duration`

---

# 12. Scalability Targets

The 80% prototype should support at least:

- 5 warehouses
- 10,000 products
- 50,000 orders in a test dataset
- 500 concurrent delivery vehicles in simulation
- 100 charging stations
- 1,000 charging connectors
- 100 telemetry events/sec in load simulation

These are engineering test targets, not requirements for a production deployment.

---

# 13. MVP vs 80% Scope

### MVP

- Auth
- Warehouse map
- Orders
- Batching
- Picking optimization
- Delivery route
- Safety Score
- EV stations
- Charging recommendation
- Dashboards

### 80%

Add:

- demand forecasting
- simulated real-time telemetry
- dynamic ETA
- queue prediction
- slot reservation
- recommendation explanations
- alert engine
- cross-module workflow
- audit/model versioning
- testing and documentation

---

# 14. Constraints

The Review-0 source establishes the project concept but does not specify final datasets, cloud provider, hardware, exact APIs, or model choices. Therefore those items must be treated as implementation decisions rather than source requirements.

Recommended constraint strategy:

- prioritize local/demo operation;
- avoid dependency on expensive APIs;
- use open-source optimization libraries;
- use pretrained models where useful;
- do not train a foundation model;
- keep every AI component replaceable.

---

# 15. Definition of Done

A feature is complete only when:

1. API exists.
2. Database model exists.
3. UI exists where applicable.
4. Happy path works.
5. At least one failure path works.
6. Unit/integration test exists for important logic.
7. Logs/errors are visible.
8. Demo data exists.
9. Documentation is updated.
10. Feature is demonstrated end-to-end.

---

# 16. Recommended Implementation Order

1. Repository + database + authentication
2. Common data model
3. Warehouse module
4. Delivery module
5. EV module
6. Shared event/recommendation layer
7. AI/optimization services
8. Dashboard
9. Simulation
10. Testing
11. Deployment
12. Demo scenarios

---

# 17. Version Control

Recommended branches:

- `main` — stable demo
- `develop` — integration
- `feature/warehouse`
- `feature/delivery-safety`
- `feature/ev-charging`
- `feature/ai-agents`
- `feature/ui`

Every model or algorithm change should record:

`component, algorithm/model, version, dataset version, timestamp, metrics`

---

# 18. Immediate Next Steps

### Phase 1
Create repository and folders.

### Phase 2
Create PostgreSQL/MySQL schema and seed data.

### Phase 3
Implement deterministic algorithms before AI agents.

### Phase 4
Wrap algorithms/models with service APIs.

### Phase 5
Add agent orchestration.

### Phase 6
Build dashboard and mobile-responsive screens.

### Phase 7
Connect the three workflows.

### Phase 8
Test using fixed scenarios.

### Phase 9
Deploy and prepare evaluation demo.

