# MASTER_IMPLEMENTATION_PLAN.md

**Project:** AI-Driven Smart Logistics Platform for Warehouse Optimization, Delivery Safety, and EV Charging Management  
**Target:** 80% Functional Prototype Completion  
**Version:** 1.0  
**Baseline Specs:** `docs/PROJECT_REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/UI_UX_SPECIFICATION.md`, `docs/AGENTS.md`, `AGENT_RULES.md`, `docs/22MIS0630_INHOUSE.pdf`

---

## 1. Executive Summary & Project Context

The **AI-Driven Smart Logistics Platform** integrates three core logistics domains into a unified operational platform:
1. **Warehouse Optimization:** Node/edge dark-store navigation graph, picking sequence optimization (A*/Dijkstra), constraint-based order batching (OR-Tools), demand forecasting (XGBoost/LightGBM), and inventory positioning recommendations.
2. **Delivery Safety:** Route planning, dynamic ETA calculation, telemetry processing (speeding, harsh braking/acceleration, route deviation), rider Safety Score calculation ($100 - \text{weighted penalties}$), and safety alerts.
3. **EV Charging Management:** Battery State-of-Charge (SoC) tracking, station and connector management, wait-time prediction, route-integrated multi-objective charging station recommendations, and atomic slot reservations.
4. **Shared Intelligence Layer:** Hybrid AI architecture with deterministic algorithms first, ML prediction models second, and LLM explanation/orchestration third (with complete mock/fallback capabilities).

---

## 2. Current Project State

- **Documentation & Specifications:** 100% Complete (`PROJECT_REQUIREMENTS.md`, `ARCHITECTURE.md`, `UI_UX_SPECIFICATION.md`, `AGENTS.md`, `AGENT_RULES.md`, `22MIS0630_INHOUSE.pdf`).
- **Codebase Infrastructure:** Root workspace structure exists with empty subdirectories (`backend/`, `frontend/`, `intelligence/`, `data/`, `docker/`, `scripts/`, `tests/`). `.env.example` is configured.
- **Application Code & Schemas:** 0% Implemented. No database models, backend API routes, optimization routines, ML models, AI agents, or frontend UI components exist yet.

---

## 3. Proposed Project Structure

```text
smart-logistics/
├── .env.example
├── AGENT_RULES.md
├── docs/
│   ├── 22MIS0630_INHOUSE.pdf
│   ├── AGENTS.md
│   ├── ARCHITECTURE.md
│   ├── MASTER_IMPLEMENTATION_PLAN.md
│   ├── PROJECT_REQUIREMENTS.md
│   └── UI_UX_SPECIFICATION.md
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   ├── v1/
│   │   │   │   ├── router.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── warehouse.py
│   │   │   │   ├── orders.py
│   │   │   │   ├── batches.py
│   │   │   │   ├── deliveries.py
│   │   │   │   ├── safety.py
│   │   │   │   ├── vehicles.py
│   │   │   │   ├── charging.py
│   │   │   │   ├── intelligence.py
│   │   │   │   └── dashboard.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   └── websockets.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── warehouse.py
│   │   │   ├── order.py
│   │   │   ├── delivery.py
│   │   │   ├── safety.py
│   │   │   ├── vehicle.py
│   │   │   ├── charging.py
│   │   │   └── audit.py
│   │   ├── schemas/
│   │   ├── repositories/
│   │   └── services/
│   ├── requirements.txt
│   └── main.py
├── intelligence/
│   ├── optimization/
│   │   ├── picking_graph.py
│   │   └── order_batcher.py
│   ├── forecasting/
│   │   └── demand_forecaster.py
│   ├── safety/
│   │   ├── telemetry_processor.py
│   │   └── safety_calculator.py
│   ├── eta/
│   │   └── dynamic_eta.py
│   ├── charging/
│   │   ├── station_ranker.py
│   │   └── slot_manager.py
│   ├── providers/
│   │   ├── llm_base.py
│   │   ├── llm_mock.py
│   │   └── llm_openai.py
│   └── agents/
│       ├── base_agent.py
│       ├── warehouse_agent.py
│       ├── delivery_agent.py
│       ├── ev_agent.py
│       └── orchestrator.py
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── map/
│   │   │   ├── warehouse/
│   │   │   ├── delivery/
│   │   │   └── charging/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── data/
│   ├── seed/
│   │   ├── warehouse_map.json
│   │   ├── products.json
│   │   ├── orders.json
│   │   ├── vehicles.json
│   │   └── charging_stations.json
│   └── raw/
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
├── scripts/
│   ├── seed_db.py
│   ├── simulate_telemetry.py
│   └── run_scenarios.py
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## 4. Implementation Phases (Independently Testable)

### Phase 0: Environment & Core Setup
- **Goal:** Initialize backend (FastAPI/Python), frontend (Vite/React/TS/Tailwind), and testing configuration.
- **Verification:** Backend FastAPI returns `200 OK` on `/health`; Frontend renders main layout shell; Pytest executes cleanly.

### Phase 1: Database Schema & Entity Models
- **Goal:** Define all SQLAlchemy models (Users, Warehouses, Nodes, Edges, Products, Inventory, Orders, Batches, Deliveries, Telemetry, SafetyEvents, SafetyScores, Vehicles, Stations, Connectors, Slots, Reservations, Forecasts, Recommendations, AuditLogs).
- **Verification:** Database tables create cleanly; database seeding script populates test datasets for all entities without FK errors.

### Phase 2: Core Platform API & RBAC Authentication
- **Goal:** Implement JWT auth (`/api/auth`), user management, and Role-Based Access Control (Admin, Warehouse Operator, Driver, Fleet Manager, Station Admin).
- **Verification:** Unauthenticated requests fail with `401 Unauthorized`; role-restricted endpoints return `403 Forbidden` for non-authorized roles.

### Phase 3: Deterministic Intelligence Algorithms
- **Goal:** Implement graph-based indoor picking (A*/Dijkstra via NetworkX), constraint order batching (OR-Tools/heuristics), Safety Score calculation, and multi-objective EV station ranking.
- **Verification:** Unit tests pass for picking distance reduction, batch size limit enforcement, Safety Score weight calculations, and station ranking logic.

### Phase 4: Domain REST APIs & Business Logic
- **Goal:** Expose REST APIs for Warehouse (`/api/warehouse`, `/api/orders`, `/api/batches`), Delivery (`/api/deliveries`, `/api/routes`, `/api/safety`), and EV Charging (`/api/vehicles`, `/api/charging`).
- **Verification:** API endpoints respond within NFR latency targets (p95 < 500ms); charging slot reservation prevents double-booking via database transactions.

### Phase 5: Machine Learning & Forecasting Models
- **Goal:** Implement demand forecasting (baseline/XGBoost model), dynamic ETA calculator (incorporating traffic & weather factors), and charging queue wait-time predictor.
- **Verification:** Forecast endpoint returns predictions with confidence intervals and error metrics (MAE/RMSE); ETA updates dynamically when traffic/weather factors change.

### Phase 6: AI Agent Layer & LLM Abstraction
- **Goal:** Build agent framework (`WarehouseAgent`, `DeliverySafetyAgent`, `EVChargingAgent`, `OrchestratorAgent`) using typed tools and `LLMProvider` abstraction (Mock/OpenAI).
- **Verification:** Agents call tools strictly via validated APIs; fallback to template-based explanations works when LLM provider is set to mock/disabled.

### Phase 7: Frontend Application Shell & Design Tokens
- **Goal:** Build React application shell with navigation, responsive layout, dark/light theme tokens, and Leaflet interactive map abstraction.
- **Verification:** Responsive navigation works across desktop and mobile breakpoints (<768px); map component renders warehouse layout and fleet markers.

### Phase 8: Domain Dashboards & Driver Mobile UI
- **Goal:** Build Warehouse Dashboard (map, pick paths, batching UI), Fleet Operations & Safety Dashboard, EV Charging Dashboard, Driver Mobile Screen, and AI Insights Page.
- **Verification:** All user personas can navigate to primary tasks in $\le 3$ clicks; mobile view renders cleanly at 360px width.

### Phase 9: Telemetry Simulation & Real-Time Events
- **Goal:** Create simulated telemetry engine (`simulate_telemetry.py`) emitting live GPS, speed, braking, and SoC events over WebSockets/SSE to frontend.
- **Verification:** Speeding and harsh braking events trigger real-time alerts on the dashboard; vehicle SoC updates live without full page reload.

### Phase 10: End-to-End Integration, Validation & Demo Scenarios
- **Goal:** Connect full workflow (Order Ingestion $\rightarrow$ Warehouse Batching $\rightarrow$ Pick Path $\rightarrow$ Delivery Creation $\rightarrow$ Live Telemetry & Safety Alerts $\rightarrow$ Low Battery Trigger $\rightarrow$ EV Station Recommendation $\rightarrow$ Slot Reservation).
- **Verification:** Successfully demonstrate all 4 required test scenarios (Scenario A: Warehouse Peak, Scenario B: Unsafe Delivery, Scenario C: Low-Battery EV, Scenario D: Combined End-to-End Flow).

---

## 5. Architectural Risks & Mitigation Strategies

| Risk Description | Severity | Mitigation Strategy |
|---|---|---|
| **Agent Overreach & Direct Database Writes** | High | Enforce strict rule: Agents only receive read-only data snapshots and invoke validated FastAPI domain tools. No direct SQL generation. |
| **Charging Slot Race Conditions / Double Booking** | High | Use database atomic transactions (`SELECT ... FOR UPDATE`) or unique constraint indexes on `(connector_id, start_time, end_time)`. |
| **External API Failure (Traffic/Weather/Maps/LLM)** | Medium | Abstract all external integrations behind interface providers with guaranteed deterministic local mock implementations. |
| **Optimization Latency (OR-Tools/NetworkX)** | Medium | Run heavy constraint solving asynchronously off the main API event loop using Python thread pools or background tasks. |
| **Telemetry Ingestion Bottleneck** | Medium | Process telemetry events in lightweight memory queues before batching DB writes to maintain low ingestion latency (<1s). |

---

## 6. Technical Dependencies & Consistency Verification

- **Language Stack:** Python 3.11+ (Backend & Intelligence) and TypeScript/React 18 (Frontend).
- **Backend Libraries:** `fastapi`, `pydantic`, `sqlalchemy`, `alembic`, `python-jose`, `passlib`, `uvicorn`.
- **Intelligence Libraries:** `networkx`, `ortools`, `scikit-learn`, `xgboost`, `pandas`, `numpy`.
- **Frontend Libraries:** `react`, `react-dom`, `react-router-dom`, `leaflet`, `react-leaflet`, `recharts`, `lucide-react`, `tailwindcss`.
- **Consistency Verification:** Complete alignment across frontend, backend, intelligence, and data persistence layers without technology stack divergence.

---

## 7. Key Assumptions

1. **Academic Scope:** Targeting ~80% functional prototype capability focusing on core operational logic and interactive workflows.
2. **Local & Simulation First:** Telemetry, traffic, weather, and LLM APIs use simulated/mock providers by default for reliable local demonstrations.
3. **Deterministic First:** All AI agent recommendations rely on underlying deterministic calculations and optimizers before generating explanations.

---

## 8. First Coding Task (Phase 0)

Create backend project structure (`backend/app`), `requirements.txt`, FastAPI main app entry point (`main.py`), frontend React + Vite + TypeScript boilerplate (`frontend/`), and basic docker configuration.