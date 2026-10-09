# Smart Logistics Platform — Discovered Issues & Discrepancies

This document logs architectural edge cases, missing UI entry points, and source code vs documentation discrepancies identified during code inspection.

---

## 1. Safety Telemetry UI Entry Expose Missing
- **Issue**: The Safety frontend page (`src/pages/SafetyPage.tsx`) displays safety scores, events, and alerts, but does **NOT** provide a manual input form or simulation UI to submit live telemetry (`speed`, `latitude`, `longitude`, `acceleration`).
- **File**: `frontend/src/pages/SafetyPage.tsx`
- **Cause**: Telemetry ingestion was implemented primarily as an API-first endpoint (`POST /api/v1/telemetry`) without a corresponding interactive React component.
- **Impact**: Testing safety event generation and score deduction requires using external HTTP clients (e.g. Postman, cURL, or FastAPI `/docs` Swagger UI) rather than direct UI clicks.
- **Recommended Fix**: Add a "Simulate Driver Telemetry" modal component in `SafetyPage.tsx` that calls `telemetryApi.ingestTelemetry()`.

---

## 2. LLM Client Injection vs Rule-Based Fallback
- **Issue**: Documentation (`AGENTS.md`) presents `WarehouseOptimizationAgent` and `DeliverySafetyAgent` as autonomous LLM-driven agents. However, inspectable source code (`backend/app/services/warehouse_agent.py`) defaults `llm_client = None`.
- **File**: `backend/app/services/warehouse_agent.py`
- **Cause**: No external LLM API key (e.g. OpenAI / Gemini API key) is configured in default environment files `.env`.
- **Impact**: The intelligence layer functions **100% deterministically** using string template fallbacks (`_generate_deterministic_explanation`). All optimization values, batch groupings, and shortest paths are computed by pure algorithmic code (`OrderBatcher` and `PickRoutingEngine`), not LLM reasoning.
- **Recommended Fix**: Clarify in project documentation that optimization logic is pure Python algorithms, while LLMs are strictly optional for natural language explanation generation.

---

## 3. SQLite In-Memory Concurrency Limitation
- **Issue**: In local development fallback mode using SQLite (`test.db` / `smart_logistics_fallback.db`), concurrent calls to `create_reservation` (`SELECT FOR UPDATE`) do not enforce row-level locks because SQLite uses database-level locking.
- **File**: `backend/app/services/charging_service.py`
- **Cause**: `SELECT FOR UPDATE` syntax is parsed by SQLite but ignored during transaction lock escalation.
- **Impact**: Full atomic concurrency prevention against double-booking requires a running MySQL InnoDB instance (`docker-compose up -d mysql`).
- **Recommended Fix**: Ensure production and evaluation testing run against the provided MySQL Docker container.
