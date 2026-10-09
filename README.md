# AI-Driven Smart Logistics Platform

An AI-Driven Smart Logistics Platform for **Warehouse Optimization**, **Delivery Safety**, and **EV Charging Management**. Target completion: ~80% academic prototype.

---

## 1. Prerequisites

- **Python:** 3.11 or higher
- **Node.js:** v18.0 or higher (v24 supported)
- **Database:** MySQL 8.0+ (SQLite is used only by isolated offline unit tests)
- **Docker & Docker Compose:** (Optional, for containerized execution)

---

## 2. Environment Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Configure environment variables in `.env` if needed:
   ```env
   APP_ENV=development
   DATABASE_URL=mysql+pymysql://smart_logistics:password@localhost:3306/smart_logistics
   JWT_SECRET=supersecret_jwt_key_change_in_production_32bytes
   ```

---

## 3. Installation

### Backend Setup
```bash
# Create virtual environment (optional)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
python -m pip install -r backend/requirements.txt
```

### Frontend Setup
```bash
cd frontend
npm install
cd ..
```

---

## 4. Database Setup (MySQL 8.0)

### Option A: Local MySQL
Ensure a MySQL 8.0 server is running on `localhost:3306` with database `smart_logistics` and user `smart_logistics:password`.

### Option B: Docker Compose MySQL
```bash
docker-compose up -d mysql
```

### Option C: Isolated Unit Test Database
A small set of offline unit tests create their own in-memory SQLite database and never touch the configured `DATABASE_URL`.

---

## 5. Database Migrations (Alembic)

Alembic infrastructure manages schema revisions for MySQL:

```bash
# Generate a new migration revision (when models change)
alembic revision --autogenerate -m "migration description"

# Apply all pending migrations to MySQL database
alembic upgrade head

# Rollback the last migration
alembic downgrade -1

# Show current migration revision
alembic current
```

---

## 6. Running the Backend

Start FastAPI development server:
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Root API Info:** `http://localhost:8000/`
- **Swagger Docs:** `http://localhost:8000/docs`
- **Health Endpoint:** `http://localhost:8000/health`
- **Database Connectivity:** `http://localhost:8000/health/db`

---

## 7. Running the Frontend

Start Vite React development server:
```bash
cd frontend
npm run dev
```

- **Frontend Dashboard:** `http://localhost:5173/`

---

## 8. Running Docker Containers

To run the entire platform (MySQL + Backend + Frontend) using Docker Compose:
```bash
docker-compose up --build
```

---

## 9. Running Tests

Run backend automated pytest suite:
```bash
python -m pytest tests/
```

---

---

## 11. Phase 2 Architecture & REST APIs

Phase 2 introduces **70 REST API Endpoints across 17 Routers** under `/api/v1/`, backed by standard **JWT Authentication (bcrypt + HS256)** and a **5-Role RBAC Matrix**:

- **Roles:** `admin`, `warehouse_operator`, `driver`, `fleet_manager`, `station_admin`
- **Error Envelope:** All error responses follow standard schema `{"error": {"code", "message", "details", "request_id"}}`
- **Pagination:** List endpoints use standardized `Page[T]` envelope containing `items`, `total`, `page`, `size`, `pages`
- **Atomic EV Reservation:** `POST /api/v1/charging/reservations` uses `SELECT ... FOR UPDATE` row locks to prevent double-booking
- **Intelligence Bridge:** `POST /api/v1/intelligence/run` is strictly allowlisted to 3 operations (`warehouse_batch_recommendation`, `delivery_safety_analysis`, `ev_charging_recommendation`)

### API Routers Summary

| Router Tag | Base Path | Endpoints | Key Operations |
|---|---|---|---|
| **Auth** | `/api/v1/auth` | `/login`, `/refresh`, `/logout`, `/me` | JWT login, session refresh, token revocation, profile lookup |
| **Users** | `/api/v1/users` | `GET/POST /`, `GET/PUT /:id` | User account management with role assignment (Admin only) |
| **Warehouses** | `/api/v1/warehouses` | `GET/POST /`, `GET/PUT /:id`, `/:id/graph` | Warehouse facilities & layout graph (nodes, edges) |
| **Products** | `/api/v1/products` | `GET/POST /`, `GET/PUT /:id` | Product catalog with SKU, weight, volume, hazmat flag |
| **Inventory** | `/api/v1/inventory` | `GET/POST /`, `GET/PUT /:id`, `/low-stock` | Stock level tracking, replenishment triggers |
| **Orders** | `/api/v1/orders` | `GET/POST /`, `GET/PUT /:id`, `/:id/status` | Order creation, priority conversion, status progression |
| **Batches** | `/api/v1/batches` | `GET/POST /`, `GET /:id`, `/optimize` | Picking batch creation & FIFO batching algorithm stub |
| **Picking** | `/api/v1/picking` | `GET /tasks`, `/tasks/:id/status`, `/routes/:batch_id` | Picking tasks and sequential route generation |
| **Deliveries** | `/api/v1/deliveries` | `GET/POST /`, `GET /:id`, `/:id/status`, `/:id/eta` | Delivery dispatch, driver status updates, ETA estimation |
| **Drivers** | `/api/v1/drivers` | `GET/POST /`, `GET/PUT /:id`, `/:id/availability` | Driver profiles, status tracking, schedule assignment |
| **Vehicles** | `/api/v1/vehicles` | `GET/POST /`, `GET/PUT /:id`, `/:id/soc` | Fleet vehicle profiles, telemetry SoC updates |
| **Telemetry** | `/api/v1/telemetry` | `POST /`, `GET /vehicle/:id`, `GET /alerts` | Speed, battery, location telemetry ingest & alert filters |
| **Safety** | `/api/v1/safety` | `GET /events`, `GET /driver-scores`, `/driver-scores/:id` | Speeding/harsh braking events and driver safety scoring |
| **Charging** | `/api/v1/charging` | `/stations`, `/connectors`, `/reservations`, `/recommend` | Charging infrastructure & atomic reservation slot locking |
| **Intelligence** | `/api/v1/intelligence` | `POST /run`, `GET /history` | Whitelisted AI bridge for batching, safety, and charging |
| **Audit** | `/api/v1/audit` | `GET /logs` | System audit trail with automatic request-id and redacting |
| **Dashboard** | `/api/v1/dashboard` | `/overview`, `/warehouse`, `/delivery`, `/charging` | Consolidated operational metrics & aggregations |

### Authentication & Testing Commands

To authenticate against the API:
```bash
# 1. Login to retrieve access token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@smartlogistics.local", "password": "AdminPass123!"}'

# 2. Access protected endpoint with Bearer token
curl -X GET http://localhost:8000/api/v1/warehouses \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Run test suite:
```bash
python -m pytest tests/test_auth.py tests/test_rbac.py tests/test_api_warehouses.py tests/test_api_orders.py tests/test_api_charging.py tests/test_api_intelligence.py -v
```

