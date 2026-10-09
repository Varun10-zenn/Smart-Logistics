# AGENTS.md

**Project:** AI-Driven Smart Logistics Platform  
**Version:** 1.0  
**Target:** 80% functional prototype

---

# 1. Core Design Principle

The system should use **specialized intelligence**, not one general-purpose autonomous agent.

Recommended structure:

```text
                    Intelligence Orchestrator
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
       ▼                    ▼                    ▼
Warehouse Agent      Delivery Safety Agent   EV Charging Agent
       │                    │                    │
       ▼                    ▼                    ▼
Optimization Tools    Safety/ETA Tools       Charging Tools
       │                    │                    │
       └────────────────────┼────────────────────┘
                            ▼
                     Shared Context
                            │
                            ▼
                         Database
```

---

# 2. Agent Responsibilities

## 2.1 Warehouse Optimization Agent

### Mission

Improve warehouse order fulfillment through:

- batching;
- picking sequence optimization;
- picker assignment;
- demand insight;
- inventory-positioning recommendations.

### Inputs

- orders;
- order items;
- SKU locations;
- warehouse graph;
- picker availability;
- batch capacity;
- deadlines;
- inventory;
- historical demand;
- weather/events where available.

### Tools

```text
get_pending_orders()
get_inventory()
get_warehouse_graph()
optimize_batches()
optimize_pick_route()
get_picker_status()
forecast_demand()
recommend_inventory_position()
```

### Outputs

```json
{
  "batch_plan": [],
  "pick_sequence": [],
  "estimated_distance": 0,
  "estimated_time": 0,
  "recommendations": [],
  "explanation": ""
}
```

---

# 3. Delivery Safety Agent

### Mission

Improve delivery reliability and responsible driving by monitoring:

- route;
- ETA;
- speed;
- braking;
- acceleration;
- route adherence;
- weather/traffic effects.

### Inputs

- delivery;
- route;
- telemetry;
- speed limit;
- traffic factor;
- weather factor;
- destination;
- vehicle state.

### Tools

```text
get_delivery()
get_route()
get_telemetry()
calculate_eta()
detect_speeding()
detect_harsh_braking()
detect_route_deviation()
calculate_safety_score()
create_alert()
```

### Outputs

```json
{
  "eta": "...",
  "safety_score": 86,
  "events": [],
  "alerts": [],
  "explanation": ""
}
```

---

# 4. EV Charging Management Agent

### Mission

Reduce charging-related delivery disruption.

### Inputs

- current location;
- destination;
- battery SoC;
- battery capacity;
- energy consumption;
- stations;
- connector availability;
- queue;
- expected charging duration;
- route.

### Tools

```text
get_vehicle_state()
get_charging_stations()
calculate_energy_need()
estimate_wait_time()
rank_charging_options()
reserve_slot()
release_slot()
```

### Outputs

```json
{
  "recommended_station_id": "S04",
  "recommended_slot_id": "S04-C2-1845",
  "estimated_wait_minutes": 7,
  "estimated_charge_minutes": 32,
  "route_detour_km": 0.8,
  "explanation": ""
}
```

---

# 5. Orchestrator Agent

The orchestrator decides which specialist should handle a request.

Examples:

```text
"Why is this delivery delayed?"
        ↓
Delivery Safety Agent

"Which orders should be batched?"
        ↓
Warehouse Agent

"Where should this EV charge?"
        ↓
EV Charging Agent
```

For cross-module questions:

```text
"Can this EV complete the assigned delivery?"
        ↓
Delivery Agent
        ↓
EV Agent
        ↓
Shared result
```

The orchestrator should not solve domain problems itself.

---

# 6. Tool Contract

Every tool must have:

- typed input;
- typed output;
- validation;
- authorization;
- timeout;
- error response;
- audit logging.

Example:

```python
class ChargingRecommendationRequest(BaseModel):
    vehicle_id: int
    destination_lat: float
    destination_lon: float
    minimum_soc: float
```

Tool output:

```python
class ChargingRecommendation(BaseModel):
    station_id: int
    wait_minutes: float
    detour_km: float
    score: float
    explanation: str
```

---

# 7. Decision Framework

Every agent follows:

```text
1. Understand request
2. Collect required state
3. Validate data
4. Select tool/model
5. Execute deterministic calculation/model
6. Validate result
7. Generate explanation
8. Return recommendation
9. Request approval if action is consequential
10. Log decision
```

---

# 8. Deterministic First Principle

The agent should NOT invent calculations.

For example, Safety Score must come from a deterministic function:

```text
Safety Score =
100
- speeding penalty
- braking penalty
- acceleration penalty
- route deviation penalty
```

The LLM may explain the score but must not silently change the formula.

Similarly:

- routing uses routing algorithms;
- batching uses optimization;
- charging uses explicit scoring/constraints;
- forecasts use a registered model.

---

# 9. Warehouse Intelligence

## Batching algorithm

Initial approach:

1. filter valid orders;
2. group by warehouse;
3. calculate geographic similarity;
4. consider promised time;
5. enforce batch capacity;
6. optimize objective;
7. validate deadline constraints.

Prototype objective:

```text
minimize(
    distance_cost
  + deadline_penalty
  + capacity_penalty
)
```

## Picking optimization

Represent warehouse as graph:

```text
Node = aisle/shelf/decision point
Edge = walkable connection
Weight = distance/time
```

Use shortest-path algorithms for local paths and a routing optimizer for multiple pick locations.

---

# 10. Demand Forecasting

Recommended initial model:

- baseline: moving average / seasonal baseline;
- ML: XGBoost/LightGBM regression;
- optional advanced model later.

Features may include:

- hour;
- day of week;
- month;
- holiday;
- weekend;
- historical demand;
- weather;
- local event indicator.

Do not claim the model is accurate until evaluated on held-out data.

Metrics:

- MAE
- RMSE
- MAPE where appropriate

---

# 11. Delivery Safety Intelligence

## Speed detection

```text
if observed_speed > speed_limit + tolerance:
    create_speed_event()
```

Use a configurable tolerance to reduce noisy alerts.

## Harsh braking

Use configurable deceleration threshold.

## Route deviation

Calculate distance from current GPS point to planned route.

If distance exceeds threshold for sufficient duration:

```text
route_deviation_event
```

## Safety Score

Initial configurable weights:

```text
speed compliance      30%
braking               25%
acceleration          15%
route adherence       30%
```

Store raw component scores as well as final score.

---

# 12. ETA Intelligence

Initial ETA:

```text
ETA = base_route_time
    × traffic_factor
    × weather_factor
```

Later replace with an ML model.

Features:

- distance;
- historical travel time;
- time of day;
- traffic;
- weather;
- road type;
- current speed.

Evaluate with MAE in minutes.

---

# 13. EV Charging Intelligence

## Feasibility

First determine:

```text
required_energy =
distance_to_destination
× consumption_kwh_per_km
```

If:

```text
available_energy < required_energy + safety_reserve
```

charging becomes mandatory.

## Station ranking

Example:

```text
station_score =
0.35 * normalized_detour
+ 0.30 * normalized_wait
+ 0.20 * availability_risk
+ 0.15 * charging_duration
```

Weights must be configurable.

Lower score = better candidate.

## Reservation

Reservation sequence:

```text
Check availability
       ↓
Lock/transaction
       ↓
Re-check availability
       ↓
Create reservation
       ↓
Commit
```

Never allow the agent to bypass this transaction.

---

# 14. Multi-Agent Collaboration

Agents communicate using structured context, not free-form conversation.

Example:

```json
{
  "task_id": "T-1004",
  "requesting_agent": "delivery_agent",
  "target_agent": "ev_agent",
  "context": {
    "vehicle_id": 42,
    "soc": 21,
    "destination": {},
    "eta": "18:45"
  }
}
```

Response:

```json
{
  "task_id": "T-1004",
  "status": "success",
  "result": {
    "charging_required": true,
    "station_id": 4
  }
}
```

---

# 15. Confidence and Uncertainty

Confidence should be derived from the underlying model/algorithm where possible.

Do not fabricate confidence.

Examples:

- optimization feasibility: high/low;
- ML forecast confidence interval;
- route availability certainty;
- charging availability freshness.

If the system lacks enough information:

```text
confidence = null
status = "insufficient_data"
```

---

# 16. Fallback Strategy

Every intelligence component needs fallback.

## LLM unavailable

Use template-based explanations.

## Forecast model unavailable

Use historical baseline.

## Traffic unavailable

Use historical/default traffic factor.

## Weather unavailable

Use neutral weather factor.

## Routing provider unavailable

Use local graph/routing algorithm where possible.

## Charging prediction unavailable

Use current queue / deterministic estimate.

The application should remain operational in degraded mode.

---

# 17. Agent Memory

Do not create unrestricted long-term agent memory.

Use three controlled types:

### Working context

Current request only.

### Operational state

Database state.

### Historical analytics

Forecasts, safety history, reservations and recommendation history.

No hidden memory should be required for correctness.

---

# 18. Guardrails

Agents must:

- validate inputs;
- respect role permissions;
- use registered tools;
- obey domain constraints;
- log actions;
- expose uncertainty;
- fail safely.

Agents must not:

- fabricate telemetry;
- fabricate station availability;
- invent routes;
- modify safety formulas;
- directly manipulate database records;
- execute arbitrary shell commands;
- reveal secrets;
- approve their own high-impact actions without configured authorization.

---

# 19. Human-in-the-Loop

Use approval for:

- charging reservation;
- cancelling reservations;
- changing operational constraints;
- changing safety thresholds;
- bulk inventory changes;
- system configuration.

Low-risk recommendations may be auto-generated.

---

# 20. Agent API

### POST /api/agents/run

```json
{
  "agent": "warehouse",
  "task": "optimize_batch",
  "context": {
    "warehouse_id": 1,
    "order_ids": [101,102,103]
  }
}
```

Response:

```json
{
  "task_id": "A-123",
  "agent": "warehouse",
  "status": "completed",
  "result": {},
  "explanation": "...",
  "confidence": null,
  "fallback_used": false,
  "model_version": "warehouse-v1"
}
```

---

# 21. Agent Registry

```python
AGENTS = {
    "warehouse": WarehouseAgent,
    "delivery_safety": DeliverySafetyAgent,
    "ev_charging": EVChargingAgent
}
```

Each agent declares:

```text
name
version
supported_tasks
tools
input_schema
output_schema
fallback
```

---

# 22. Testing Strategy

## Unit tests

- scoring;
- routing;
- batching;
- SoC calculations;
- station ranking;
- reservation validation.

## Integration tests

- order → batch;
- batch → delivery;
- delivery → safety;
- vehicle → charging;
- charging → reservation.

## Agent tests

Test:

- correct tool selection;
- invalid input;
- missing data;
- provider failure;
- fallback;
- unauthorized action.

---

# 23. Evaluation Dataset

Create fixed scenarios:

### Scenario A — warehouse peak

High order volume + limited picker capacity.

Expected:

- sensible batching;
- optimized pick route;
- peak warning.

### Scenario B — unsafe delivery

Inject speeding + harsh braking + route deviation.

Expected:

- events;
- lower Safety Score;
- alerts.

### Scenario C — low-battery EV

Low SoC + multiple stations.

Expected:

- feasible stations only;
- recommendation;
- route-aware ranking;
- reservation.

### Scenario D — combined

Warehouse batch → delivery → low battery → charging recommendation.

This is the most important end-to-end demonstration.

---

# 24. Versioning

Use semantic versions:

```text
warehouse-agent 1.0.0
safety-agent 1.0.0
ev-agent 1.0.0
forecast-model 1.0.0
```

Record:

- code version;
- model version;
- dataset version;
- configuration version.

---

# 25. 80% Implementation Roadmap

## Phase 1 — Intelligence foundations

- define schemas;
- implement tool interfaces;
- implement deterministic algorithms;
- create mock LLM provider.

## Phase 2 — Warehouse Agent

- batch optimizer;
- pick optimizer;
- forecast baseline;
- recommendation API.

## Phase 3 — Delivery Agent

- telemetry;
- event detection;
- Safety Score;
- ETA.

## Phase 4 — EV Agent

- SoC;
- station ranking;
- wait estimate;
- reservation.

## Phase 5 — Orchestrator

- route requests;
- structured agent-to-agent context;
- fallbacks;
- audit logs.

## Phase 6 — UI

- AI insights;
- alerts;
- module dashboards;
- driver mobile UI.

## Phase 7 — Validation

- fixed datasets;
- benchmark algorithms;
- integration tests;
- failure tests;
- end-to-end demo.

---

# 26. Definition of Agent Completion

An agent is considered complete when:

- it has defined responsibilities;
- tools are registered;
- inputs/outputs are typed;
- core logic works;
- fallback exists;
- tests exist;
- decisions are logged;
- explanations are available;
- it can participate in at least one end-to-end workflow.

---

# 27. Recommended First Implementation

Do not start by training a custom AI model.

Start with:

```text
FastAPI
+
PostgreSQL/MySQL
+
OR-Tools
+
NetworkX
+
scikit-learn/XGBoost
+
React
+
Specialized Python agents
+
LLM provider abstraction
```

Then progressively replace baseline algorithms with better models only when measurable improvement is demonstrated.

---

# 28. 80% End-to-End Target

The final demonstration should be:

```text
Customer Orders
      ↓
Warehouse Agent
      ↓
Optimized Batch
      ↓
Optimized Pick Route
      ↓
Delivery Created
      ↓
Delivery Safety Agent
      ↓
Route + ETA + Safety Score
      ↓
EV detects low SoC
      ↓
EV Charging Agent
      ↓
Station Recommendation
      ↓
Slot Reservation
      ↓
Fleet Dashboard
      ↓
AI Explanation + KPIs
```

This integrated flow should be treated as the primary project milestone.
