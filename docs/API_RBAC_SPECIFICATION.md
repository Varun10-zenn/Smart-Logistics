# API_RBAC_SPECIFICATION.md

**Project:** AI-Driven Smart Logistics Platform for Warehouse Optimization, Delivery Safety, and EV Charging Management  
**Phase:** 2 — Core Platform APIs & RBAC Authentication  
**Version:** 1.0  
**Baseline Specs:** `PROJECT_REQUIREMENTS.md`, `ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `AGENTS.md`, `AGENT_RULES.md`

---

## 1. Scope and Objectives

This document specifies the complete REST API contract and authorization layer for Phase 2 of the Smart Logistics Platform. It defines:

1. Versioned API structure under `/api/v1/`
2. JWT authentication flow and token lifecycle
3. Role-Based Access Control (RBAC) matrix mapping roles to endpoints
4. Pydantic request/response schemas for every router
5. Standard pagination, filtering, and error conventions
6. Agent and service access boundaries (what the AI layer may call)

**Primary consumers:**
- React/TypeScript frontend (user-facing)
- Internal domain services (future warehouse, delivery, EV modules)
- AI agent orchestration layer (routed through approved service APIs only)

---

## 2. API Versioning

All endpoints are prefixed:

```
/api/v1/<router>/<resource>
```

The `v1` prefix ensures backward compatibility. Breaking changes require a new version prefix (`v2`).

The `v1` main router file aggregates all sub-routers at:

```
backend/app/api/v1/__init__.py
```

---

## 3. Authentication Architecture

### 3.1 Mechanism

- JWT (JSON Web Token) bearer authentication
- **No social logins, no OAuth, no direct database credentials for API consumers**
- Password stored as bcrypt hash (minimum cost factor 12)
- Tokens are stateless; revocation uses a short-lived access token + denylist on logout

### 3.2 Token Types

| Token | Lifetime | Purpose |
|---|---|---|
| Access Token | 60 minutes | API request authentication (Bearer header) |
| Refresh Token | 7 days | Re-issue access tokens without re-login |

### 3.3 JWT Payload Structure

```json
{
  "sub": "42",
  "email": "operator@warehouse.local",
  "role": "warehouse_operator",
  "iat": 1700000000,
  "exp": 1700003600,
  "jti": "unique-token-id"
}
```

Fields:
- `sub` — User `id` (string, integer serialized as string per JWT spec)
- `email` — User email (informational, no DB query needed for role check)
- `role` — Role code (one of the five defined roles)
- `iat` — Issued-at timestamp (UTC epoch)
- `exp` — Expiry timestamp (UTC epoch)
- `jti` — JWT ID (unique per token, used for revocation denylist)

### 3.4 Authentication Flow

```text
POST /api/v1/auth/login
        │
        ├─ Validate email + password
        ├─ Verify bcrypt hash
        ├─ Issue access_token (JWT, 60 min)
        ├─ Issue refresh_token (JWT, 7 days)
        └─ Return {access_token, refresh_token, token_type, expires_in}

POST /api/v1/auth/refresh
        │
        ├─ Validate refresh_token signature + expiry
        ├─ Issue new access_token
        └─ Return {access_token, token_type, expires_in}

POST /api/v1/auth/logout
        │
        ├─ Extract jti from access_token
        ├─ Add jti to in-memory or Redis denylist (TTL = remaining token lifetime)
        └─ 204 No Content

GET /api/v1/auth/me
        │
        ├─ Validate access_token (Bearer header)
        └─ Return current user profile
```

### 3.5 FastAPI Security Dependency

```python
# backend/app/core/security.py
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    """Decode JWT, validate signature, check denylist, return User ORM object."""
    ...

async def require_role(*roles: str):
    """Returns a dependency that enforces one of the given role codes."""
    ...
```

---

## 4. Roles

The five platform roles are fixed for Phase 2:

| Role Code | Description | Primary Domain |
|---|---|---|
| `admin` | Full platform access; user management; audit log access | Cross-platform |
| `warehouse_operator` | Warehouse operations; order management; batch and picking management | Warehouse |
| `driver` | Own delivery visibility; safety score; charging reservation | Delivery / EV |
| `fleet_manager` | Fleet and vehicle management; all deliveries; all safety data | Delivery / Fleet |
| `station_admin` | Charging station and slot management; reservations | EV Charging |

> **Roles are seeded into the `roles` table by the Phase 1 seed script and must not be altered by API endpoints.**

---

## 5. RBAC Matrix

Legend:
- ✅ Allowed
- ❌ Denied
- 🔒 Own record only (e.g., driver sees only their own deliveries)
- 🔑 Admin only

| Endpoint Group | admin | warehouse_operator | driver | fleet_manager | station_admin |
|---|:---:|:---:|:---:|:---:|:---:|
| **Auth** | | | | | |
| POST /auth/login | ✅ | ✅ | ✅ | ✅ | ✅ |
| POST /auth/refresh | ✅ | ✅ | ✅ | ✅ | ✅ |
| POST /auth/logout | ✅ | ✅ | ✅ | ✅ | ✅ |
| GET /auth/me | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Users** | | | | | |
| GET /users | 🔑 | ❌ | ❌ | ❌ | ❌ |
| POST /users | 🔑 | ❌ | ❌ | ❌ | ❌ |
| GET /users/{id} | 🔑 | ❌ | 🔒 | ❌ | ❌ |
| PATCH /users/{id} | 🔑 | ❌ | 🔒 | ❌ | ❌ |
| DELETE /users/{id} | 🔑 | ❌ | ❌ | ❌ | ❌ |
| **Warehouses** | | | | | |
| GET /warehouses | ✅ | ✅ | ❌ | ✅ | ❌ |
| POST /warehouses | 🔑 | ❌ | ❌ | ❌ | ❌ |
| GET /warehouses/{id} | ✅ | ✅ | ❌ | ✅ | ❌ |
| GET /warehouses/{id}/graph | ✅ | ✅ | ❌ | ✅ | ❌ |
| PATCH /warehouses/{id} | 🔑 | ❌ | ❌ | ❌ | ❌ |
| **Products** | | | | | |
| GET /products | ✅ | ✅ | ❌ | ✅ | ❌ |
| POST /products | 🔑 | ✅ | ❌ | ❌ | ❌ |
| GET /products/{id} | ✅ | ✅ | ❌ | ✅ | ❌ |
| PATCH /products/{id} | 🔑 | ✅ | ❌ | ❌ | ❌ |
| **Inventory** | | | | | |
| GET /inventory | ✅ | ✅ | ❌ | ✅ | ❌ |
| PATCH /inventory/{id} | 🔑 | ✅ | ❌ | ❌ | ❌ |
| **Orders** | | | | | |
| GET /orders | ✅ | ✅ | ❌ | ✅ | ❌ |
| POST /orders | ✅ | ✅ | ❌ | ❌ | ❌ |
| GET /orders/{id} | ✅ | ✅ | ❌ | ✅ | ❌ |
| PATCH /orders/{id}/status | 🔑 | ✅ | ❌ | ❌ | ❌ |
| **Batches** | | | | | |
| GET /batches | ✅ | ✅ | ❌ | ✅ | ❌ |
| POST /batches/optimize | ✅ | ✅ | ❌ | ❌ | ❌ |
| GET /batches/{id} | ✅ | ✅ | ❌ | ✅ | ❌ |
| PATCH /batches/{id}/status | 🔑 | ✅ | ❌ | ❌ | ❌ |
| **Picking** | | | | | |
| POST /picking/optimize | ✅ | ✅ | ❌ | ❌ | ❌ |
| GET /picking/routes/{id} | ✅ | ✅ | ❌ | ✅ | ❌ |
| **Deliveries** | | | | | |
| GET /deliveries | ✅ | ❌ | 🔒 | ✅ | ❌ |
| POST /deliveries | ✅ | ✅ | ❌ | ✅ | ❌ |
| GET /deliveries/{id} | ✅ | ✅ | 🔒 | ✅ | ❌ |
| PATCH /deliveries/{id}/status | 🔑 | ❌ | 🔒 | ✅ | ❌ |
| **Drivers** | | | | | |
| GET /drivers | ✅ | ❌ | 🔒 | ✅ | ❌ |
| POST /drivers | 🔑 | ❌ | ❌ | ✅ | ❌ |
| GET /drivers/{id} | ✅ | ❌ | 🔒 | ✅ | ❌ |
| PATCH /drivers/{id} | 🔑 | ❌ | 🔒 | ✅ | ❌ |
| **Vehicles** | | | | | |
| GET /vehicles | ✅ | ❌ | ❌ | ✅ | ✅ |
| POST /vehicles | 🔑 | ❌ | ❌ | ✅ | ❌ |
| GET /vehicles/{id} | ✅ | ❌ | 🔒 | ✅ | ✅ |
| PATCH /vehicles/{id}/soc | 🔑 | ❌ | 🔒 | ✅ | ❌ |
| **Telemetry** | | | | | |
| POST /telemetry/events | ✅ | ❌ | ✅ | ✅ | ❌ |
| GET /telemetry/events | ✅ | ❌ | 🔒 | ✅ | ❌ |
| **Safety** | | | | | |
| GET /safety/scores | ✅ | ❌ | 🔒 | ✅ | ❌ |
| GET /safety/scores/{delivery_id} | ✅ | ❌ | 🔒 | ✅ | ❌ |
| GET /safety/events | ✅ | ❌ | 🔒 | ✅ | ❌ |
| GET /safety/alerts | ✅ | ❌ | 🔒 | ✅ | ❌ |
| PATCH /safety/alerts/{id}/acknowledge | 🔑 | ❌ | 🔒 | ✅ | ❌ |
| **Charging** | | | | | |
| GET /charging/stations | ✅ | ❌ | ✅ | ✅ | ✅ |
| POST /charging/stations | 🔑 | ❌ | ❌ | ❌ | ✅ |
| GET /charging/stations/{id} | ✅ | ❌ | ✅ | ✅ | ✅ |
| PATCH /charging/stations/{id} | 🔑 | ❌ | ❌ | ❌ | ✅ |
| GET /charging/connectors | ✅ | ❌ | ✅ | ✅ | ✅ |
| GET /charging/slots | ✅ | ❌ | ✅ | ✅ | ✅ |
| POST /charging/recommend | ✅ | ❌ | ✅ | ✅ | ❌ |
| POST /charging/reservations | ✅ | ❌ | ✅ | ✅ | ✅ |
| GET /charging/reservations | ✅ | ❌ | 🔒 | ✅ | ✅ |
| DELETE /charging/reservations/{id} | 🔑 | ❌ | 🔒 | ✅ | ✅ |
| GET /charging/sessions | ✅ | ❌ | 🔒 | ✅ | ✅ |
| **Intelligence** | | | | | |
| POST /intelligence/run | ✅ | ✅ | ✅ | ✅ | ✅ |
| GET /intelligence/recommendations | ✅ | ✅ | 🔒 | ✅ | ✅ |
| GET /intelligence/forecasts | ✅ | ✅ | ❌ | ✅ | ✅ |
| **Audit** | | | | | |
| GET /audit/logs | 🔑 | ❌ | ❌ | ❌ | ❌ |
| **Dashboard** | | | | | |
| GET /dashboard/warehouse | ✅ | ✅ | ❌ | ✅ | ❌ |
| GET /dashboard/delivery | ✅ | ❌ | ✅ | ✅ | ❌ |
| GET /dashboard/charging | ✅ | ❌ | ✅ | ✅ | ✅ |
| GET /dashboard/overview | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 6. Pagination and Filtering Convention

All list endpoints (`GET /resource`) support cursor-based or offset-based pagination through a consistent query interface.

### 6.1 Query Parameters (all list endpoints)

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number (1-indexed) |
| `page_size` | int | 20 | Items per page (max 100) |
| `sort_by` | string | `created_at` | Sort field |
| `sort_dir` | `asc` / `desc` | `desc` | Sort direction |

Specific list endpoints may add domain-specific filters (e.g., `warehouse_id`, `status`, `from_date`, `to_date`).

### 6.2 Paginated Response Envelope

```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 342,
    "total_pages": 18,
    "has_next": true,
    "has_prev": false
  }
}
```

### 6.3 Pydantic Generic Page Schema

```python
# backend/app/schemas/common.py
from typing import TypeVar, Generic, List
from pydantic import BaseModel

T = TypeVar("T")

class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool

class Page(BaseModel, Generic[T]):
    items: List[T]
    pagination: PaginationMeta
```

---

## 7. Standard Error Response Format

All error responses use the same envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": [
      {"field": "email", "issue": "Invalid email format"}
    ],
    "request_id": "req_a3b2c1d0e9f8"
  }
}
```

### 7.1 HTTP Status Code Mapping

| Scenario | HTTP Code | Error Code |
|---|---|---|
| Missing/invalid JWT | 401 | `UNAUTHORIZED` |
| Insufficient role | 403 | `FORBIDDEN` |
| Resource not found | 404 | `NOT_FOUND` |
| Request validation failure | 422 | `VALIDATION_ERROR` |
| Business rule violation | 409 | `CONFLICT` |
| Duplicate resource | 409 | `DUPLICATE_RESOURCE` |
| Internal service error | 500 | `INTERNAL_ERROR` |
| AI/optimization service unavailable | 503 | `SERVICE_UNAVAILABLE` |

### 7.2 Request ID

Every request must propagate a `request_id` header (generated if not supplied by caller). All logs and error responses include this ID for traceability.

---

## 8. Router Definitions

### 8.1 Auth Router — `/api/v1/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | None | Authenticate and receive tokens |
| POST | `/auth/refresh` | Refresh token | Re-issue access token |
| POST | `/auth/logout` | Access token | Invalidate current access token |
| GET | `/auth/me` | Any role | Return current user profile |

#### Request: POST /auth/login
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

#### Response: POST /auth/login (200)
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### 8.2 Users Router — `/api/v1/users`

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/users` | admin | List all users (paginated) |
| POST | `/users` | admin | Create a new user |
| GET | `/users/{id}` | admin / own | Get user by ID |
| PATCH | `/users/{id}` | admin / own | Update user fields |
| DELETE | `/users/{id}` | admin | Soft-delete user (`is_active = false`) |

#### Pydantic Schemas

```python
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=128)
    phone: Optional[str] = None
    password: str = Field(..., min_length=8)
    role_code: Literal["admin", "warehouse_operator", "driver", "fleet_manager", "station_admin"]

class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    phone: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
```

---

### 8.3 Warehouses Router — `/api/v1/warehouses`

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/warehouses` | admin, warehouse_operator, fleet_manager | List warehouses |
| POST | `/warehouses` | admin | Create warehouse |
| GET | `/warehouses/{id}` | admin, warehouse_operator, fleet_manager | Warehouse detail |
| GET | `/warehouses/{id}/graph` | admin, warehouse_operator, fleet_manager | Node + edge graph for visualization |
| PATCH | `/warehouses/{id}` | admin | Update warehouse metadata |

#### Pydantic Schemas

```python
class WarehouseCreate(BaseModel):
    code: str = Field(..., max_length=32)
    name: str = Field(..., max_length=128)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = None

class WarehouseRead(BaseModel):
    id: int
    code: str
    name: str
    latitude: float
    longitude: float
    address: Optional[str]
    status: str
    created_at: datetime

class WarehouseGraphRead(BaseModel):
    warehouse_id: int
    nodes: List[NodeRead]
    edges: List[EdgeRead]

class NodeRead(BaseModel):
    id: int
    node_code: str
    x_coord: float
    y_coord: float
    z_coord: float
    is_blocked: bool
    zone_id: Optional[int]

class EdgeRead(BaseModel):
    id: int
    from_node_id: int
    to_node_id: int
    distance_meters: float
    is_bidirectional: bool
    is_blocked: bool
```

---

### 8.4 Products Router — `/api/v1/products`

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/products` | admin, warehouse_operator, fleet_manager | List products (filterable by category, SKU) |
| POST | `/products` | admin, warehouse_operator | Create product |
| GET | `/products/{id}` | admin, warehouse_operator, fleet_manager | Product detail |
| PATCH | `/products/{id}` | admin, warehouse_operator | Update product |

#### Pydantic Schemas

```python
class ProductCreate(BaseModel):
    sku: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    category: str = Field(..., max_length=64)
    unit_weight_kg: float = Field(..., gt=0)
    unit_volume_cbm: float = Field(..., gt=0)
    price: float = Field(..., ge=0)

class ProductRead(BaseModel):
    id: int
    sku: str
    name: str
    category: str
    unit_weight_kg: float
    unit_volume_cbm: float
    price: float
    created_at: datetime
```

---

### 8.5 Inventory Router — `/api/v1/inventory`

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/inventory` | admin, warehouse_operator, fleet_manager | List inventory (filter by warehouse_id, product_id) |
| GET | `/inventory/{id}` | admin, warehouse_operator | Inventory record detail |
| PATCH | `/inventory/{id}` | admin, warehouse_operator | Adjust quantity or reorder threshold |

```python
class InventoryRead(BaseModel):
    id: int
    warehouse_id: int
    product_id: int
    location_id: int
    quantity: int
    reorder_threshold: int
    updated_at: datetime

class InventoryUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=0)
    reorder_threshold: Optional[int] = Field(None, ge=0)
```

---

### 8.6 Orders Router — `/api/v1/orders`

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/orders` | admin, warehouse_operator, fleet_manager | List orders (filter by warehouse_id, status, priority) |
| POST | `/orders` | admin, warehouse_operator | Create order with items |
| GET | `/orders/{id}` | admin, warehouse_operator, fleet_manager | Order detail with items |
| PATCH | `/orders/{id}/status` | admin, warehouse_operator | Update order status |

#### Pydantic Schemas

```python
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)

class OrderCreate(BaseModel):
    warehouse_id: int
    customer_lat: float = Field(..., ge=-90, le=90)
    customer_lon: float = Field(..., ge=-180, le=180)
    promised_at: datetime
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    items: List[OrderItemCreate] = Field(..., min_length=1)

class OrderItemRead(BaseModel):
    id: int
    product_id: int
    quantity: int

class OrderRead(BaseModel):
    id: int
    warehouse_id: int
    customer_lat: float
    customer_lon: float
    created_at: datetime
    promised_at: datetime
    priority: str
    status: str
    items: List[OrderItemRead]

class OrderStatusUpdate(BaseModel):
    status: Literal["pending", "batched", "picking", "picked", "dispatched", "delivered", "cancelled"]
```

---

### 8.7 Batches Router — `/api/v1/batches`

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/batches` | admin, warehouse_operator, fleet_manager | List batches |
| POST | `/batches/optimize` | admin, warehouse_operator | Request batch optimization |
| GET | `/batches/{id}` | admin, warehouse_operator, fleet_manager | Batch detail with linked orders |
| PATCH | `/batches/{id}/status` | admin, warehouse_operator | Update batch status |

#### Pydantic Schemas

```python
class BatchOptimizeRequest(BaseModel):
    warehouse_id: int
    order_ids: List[int] = Field(..., min_length=1)
    max_orders_per_batch: int = Field(5, ge=1, le=20)
    deadline_weight: float = Field(0.4, ge=0.0, le=1.0)
    distance_weight: float = Field(0.4, ge=0.0, le=1.0)
    capacity_weight: float = Field(0.2, ge=0.0, le=1.0)

class BatchPlan(BaseModel):
    batch_id: Optional[int]   # null if not yet persisted
    order_ids: List[int]
    estimated_distance: float
    estimated_time_minutes: float

class BatchOptimizeResponse(BaseModel):
    task_id: str
    warehouse_id: int
    batches: List[BatchPlan]
    explanation: str
    algorithm: str
    fallback_used: bool

class BatchRead(BaseModel):
    id: int
    warehouse_id: int
    status: str
    deadline: Optional[datetime]
    created_at: datetime
    order_ids: List[int]
```

---

### 8.8 Picking Router — `/api/v1/picking`

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/picking/optimize` | admin, warehouse_operator | Generate optimized pick route for a batch |
| GET | `/picking/routes/{id}` | admin, warehouse_operator, fleet_manager | Retrieve pick route with steps |

```python
class PickOptimizeRequest(BaseModel):
    batch_id: int

class PickRouteStepRead(BaseModel):
    step_number: int
    location_code: str
    node_id: int
    product_sku: str
    quantity: int
    x_coord: float
    y_coord: float

class PickRouteRead(BaseModel):
    id: int
    batch_id: int
    total_distance_meters: float
    estimated_minutes: float
    algorithm: str
    created_at: datetime
    steps: List[PickRouteStepRead]
```

---

### 8.9 Deliveries Router — `/api/v1/deliveries`

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/deliveries` | admin, fleet_manager, driver (own) | List deliveries |
| POST | `/deliveries` | admin, warehouse_operator, fleet_manager | Create delivery from batch |
| GET | `/deliveries/{id}` | admin, warehouse_operator, fleet_manager, driver (own) | Delivery detail |
| PATCH | `/deliveries/{id}/status` | admin, fleet_manager, driver (own) | Update delivery status |
| GET | `/deliveries/{id}/eta` | admin, fleet_manager, driver (own) | Get current ETA |

```python
class DeliveryCreate(BaseModel):
    batch_id: int
    driver_id: int
    vehicle_id: int

class DeliveryStatusUpdate(BaseModel):
    status: Literal["assigned", "in_transit", "completed", "cancelled", "failed"]
    traffic_factor: Optional[float] = Field(None, ge=1.0, le=5.0)
    weather_factor: Optional[float] = Field(None, ge=1.0, le=3.0)

class ETAResponse(BaseModel):
    delivery_id: int
    eta: datetime
    base_route_minutes: float
    traffic_factor: float
    weather_factor: float
    algorithm: str
    confidence: Optional[float]

class DeliveryRead(BaseModel):
    id: int
    batch_id: int
    driver_id: int
    vehicle_id: int
    status: str
    eta: Optional[datetime]
    created_at: datetime
```

---

### 8.10 Drivers Router — `/api/v1/drivers`

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/drivers` | admin, fleet_manager | List drivers |
| POST | `/drivers` | admin, fleet_manager | Register driver profile |
| GET | `/drivers/{id}` | admin, fleet_manager, driver (own) | Driver detail |
| PATCH | `/drivers/{id}` | admin, fleet_manager, driver (own) | Update driver data |

```python
class DriverCreate(BaseModel):
    user_id: int
    license_number: str = Field(..., max_length=32)
    license_expiry: datetime
    vehicle_type_id: Optional[int] = None

class DriverRead(BaseModel):
    id: int
    user_id: int
    full_name: str
    license_number: str
    license_expiry: datetime
    status: str
```

---

### 8.11 Vehicles Router — `/api/v1/vehicles`

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/vehicles` | admin, fleet_manager, station_admin | List vehicles (filter by is_ev) |
| POST | `/vehicles` | admin, fleet_manager | Register vehicle |
| GET | `/vehicles/{id}` | admin, fleet_manager, station_admin, driver (own) | Vehicle detail |
| PATCH | `/vehicles/{id}/soc` | admin, fleet_manager, driver (own) | Update State of Charge |

```python
class VehicleCreate(BaseModel):
    registration_no: str = Field(..., max_length=32)
    vehicle_type_id: int
    is_ev: bool = False
    battery_capacity_kwh: Optional[float] = Field(None, gt=0)
    consumption_kwh_per_km: Optional[float] = Field(None, gt=0)

class VehicleRead(BaseModel):
    id: int
    registration_no: str
    is_ev: bool
    battery_capacity_kwh: Optional[float]
    soc_percent: Optional[float]
    consumption_kwh_per_km: Optional[float]
    status: str

class SoCUpdate(BaseModel):
    soc_percent: float = Field(..., ge=0.0, le=100.0)
```

---

### 8.12 Telemetry Router — `/api/v1/telemetry`

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/telemetry/events` | admin, fleet_manager, driver | Ingest telemetry event (single or batch) |
| GET | `/telemetry/events` | admin, fleet_manager | Query telemetry events (filter by vehicle_id, delivery_id, time range) |

```python
class TelemetryEventCreate(BaseModel):
    vehicle_id: int
    delivery_id: Optional[int] = None
    timestamp: datetime
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    speed_kmh: float = Field(..., ge=0)
    acceleration_ms2: Optional[float] = None
    braking_ms2: Optional[float] = None
    heading_degrees: Optional[float] = Field(None, ge=0, le=360)
    soc_percent: Optional[float] = Field(None, ge=0, le=100)

class TelemetryBatchCreate(BaseModel):
    events: List[TelemetryEventCreate] = Field(..., max_length=500)

class TelemetryEventRead(BaseModel):
    id: int
    vehicle_id: int
    delivery_id: Optional[int]
    timestamp: datetime
    latitude: float
    longitude: float
    speed_kmh: float
    soc_percent: Optional[float]
```

---

### 8.13 Safety Router — `/api/v1/safety`

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/safety/scores` | admin, fleet_manager | List safety scores (filter by delivery_id, driver_id) |
| GET | `/safety/scores/{delivery_id}` | admin, fleet_manager, driver (own) | Safety score for one delivery |
| GET | `/safety/events` | admin, fleet_manager | List safety events |
| GET | `/safety/alerts` | admin, fleet_manager, driver (own) | List active safety alerts |
| PATCH | `/safety/alerts/{id}/acknowledge` | admin, fleet_manager, driver (own) | Mark alert acknowledged |

```python
class SafetyScoreRead(BaseModel):
    id: int
    delivery_id: int
    score: float
    speed_score: float
    braking_score: float
    acceleration_score: float
    route_score: float
    calculated_at: datetime

class SafetyEventRead(BaseModel):
    id: int
    delivery_id: int
    event_type: str
    severity: str
    timestamp: datetime
    latitude: float
    longitude: float
    value: float
    threshold: float

class SafetyAlertRead(BaseModel):
    id: int
    delivery_id: int
    alert_type: str
    severity: str
    message: str
    acknowledged: bool
    created_at: datetime
```

---

### 8.14 Charging Router — `/api/v1/charging`

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/charging/stations` | admin, fleet_manager, driver, station_admin | List stations (filter by status, bbox) |
| POST | `/charging/stations` | admin, station_admin | Register station |
| GET | `/charging/stations/{id}` | admin, fleet_manager, driver, station_admin | Station detail with connectors |
| PATCH | `/charging/stations/{id}` | admin, station_admin | Update station metadata/status |
| GET | `/charging/connectors` | admin, fleet_manager, driver, station_admin | List connectors (filter by station_id, status) |
| GET | `/charging/slots` | admin, fleet_manager, driver, station_admin | List available slots (filter by connector_id, time range) |
| POST | `/charging/recommend` | admin, fleet_manager, driver | Request charging station recommendation |
| POST | `/charging/reservations` | admin, fleet_manager, driver, station_admin | Reserve a slot (atomic transaction) |
| GET | `/charging/reservations` | admin, fleet_manager, station_admin, driver (own) | List reservations |
| DELETE | `/charging/reservations/{id}` | admin, fleet_manager, station_admin, driver (own) | Cancel reservation |
| GET | `/charging/sessions` | admin, fleet_manager, station_admin, driver (own) | List charging sessions |

#### Reservation (critical path — atomic check required)

```python
class ChargingRecommendRequest(BaseModel):
    vehicle_id: int
    current_soc_percent: float = Field(..., ge=0, le=100)
    destination_lat: float = Field(..., ge=-90, le=90)
    destination_lon: float = Field(..., ge=-180, le=180)
    current_lat: float = Field(..., ge=-90, le=90)
    current_lon: float = Field(..., ge=-180, le=180)
    minimum_soc_after_charge: float = Field(80.0, ge=0, le=100)
    preferred_start: Optional[datetime] = None

class ChargingRecommendResponse(BaseModel):
    recommended_station_id: int
    recommended_connector_id: int
    recommended_slot_id: int
    estimated_wait_minutes: float
    estimated_charge_minutes: float
    route_detour_km: float
    station_score: float
    explanation: str
    algorithm: str
    fallback_used: bool

class ReservationCreate(BaseModel):
    slot_id: int
    vehicle_id: int
    driver_id: int
    delivery_id: Optional[int] = None

class ReservationRead(BaseModel):
    id: int
    reservation_code: str
    slot_id: int
    vehicle_id: int
    driver_id: int
    delivery_id: Optional[int]
    start_time: datetime
    end_time: datetime
    status: str
    created_at: datetime
```

**Reservation transaction sequence** (enforced in service layer, not router):

```text
1. Begin DB transaction
2. SELECT connector slot WHERE id = slot_id FOR UPDATE
3. Call has_charging_reservation_overlap(connector_id, start, end)
4. If overlap → raise 409 CONFLICT
5. Create ChargingReservation + mark ChargingSlot.is_booked = True
6. Commit
7. Return reservation
```

---

### 8.15 Intelligence Router — `/api/v1/intelligence`

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/intelligence/run` | Any authenticated | Submit agent task |
| GET | `/intelligence/recommendations` | Any authenticated | List AI recommendation history |
| GET | `/intelligence/forecasts` | admin, warehouse_operator, fleet_manager, station_admin | List demand/queue forecasts |

```python
class AgentRunRequest(BaseModel):
    agent: Literal["warehouse", "delivery_safety", "ev_charging"]
    task: str
    context: Dict[str, Any]

class AgentRunResponse(BaseModel):
    task_id: str
    agent: str
    status: Literal["completed", "failed", "fallback"]
    result: Dict[str, Any]
    explanation: str
    confidence: Optional[float]
    fallback_used: bool
    model_version: str
    latency_ms: int

class RecommendationRead(BaseModel):
    id: int
    agent_name: str
    recommendation_type: str
    input_snapshot: Dict
    output: Dict
    explanation: str
    confidence: Optional[float]
    model_version: str
    created_at: datetime

class ForecastRead(BaseModel):
    id: int
    forecast_type: str
    entity_id: int
    forecast_time: datetime
    predicted_value: float
    lower_bound: Optional[float]
    upper_bound: Optional[float]
    model_name: str
    model_version: str
    created_at: datetime
```

---

### 8.16 Audit Router — `/api/v1/audit`

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/audit/logs` | admin | List audit log entries (paginated, filter by action, resource_type, user_id, date range) |

```python
class AuditLogRead(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[Dict]
    ip_address: Optional[str]
    created_at: datetime
```

---

### 8.17 Dashboard Router — `/api/v1/dashboard`

Aggregates KPI data for each module dashboard. These endpoints return pre-computed summaries, not raw ORM entities. Complex calculations happen in dedicated service functions.

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/dashboard/overview` | Any authenticated | Cross-module summary KPIs |
| GET | `/dashboard/warehouse` | admin, warehouse_operator, fleet_manager | Warehouse operations KPIs |
| GET | `/dashboard/delivery` | admin, fleet_manager, driver (own) | Delivery and safety KPIs |
| GET | `/dashboard/charging` | admin, fleet_manager, driver, station_admin | EV charging KPIs |

```python
class WarehouseDashboard(BaseModel):
    active_warehouses: int
    pending_orders: int
    active_batches: int
    orders_completed_today: int
    avg_picking_distance_m: float
    batch_utilization_pct: float
    low_stock_alerts: int

class DeliveryDashboard(BaseModel):
    active_deliveries: int
    deliveries_completed_today: int
    avg_safety_score: float
    active_alerts: int
    avg_eta_error_minutes: float
    speeding_events_today: int
    harsh_braking_events_today: int

class ChargingDashboard(BaseModel):
    operational_stations: int
    total_connectors: int
    available_connectors: int
    active_sessions: int
    reservations_today: int
    avg_wait_minutes: float
    utilization_pct: float

class OverviewDashboard(BaseModel):
    warehouse: WarehouseDashboard
    delivery: DeliveryDashboard
    charging: ChargingDashboard
    generated_at: datetime
```

---

## 9. Agent and Service Access Boundaries

### 9.1 Principle

The AI agent layer **must not**:
- Hold or open its own SQLAlchemy sessions
- Directly read from or write to ORM models
- Bypass the service/repository layer
- Execute raw SQL statements
- Call admin-only endpoints without authorized credentials

### 9.2 Approved Agent-to-API Interface

AI agents interact with the platform exclusively through the `POST /api/v1/intelligence/run` endpoint. Internally the `IntelligenceRouter` dispatches to the appropriate domain agent which then calls **approved domain service functions** — never raw queries.

```text
Agent Run Request
        │
        ▼
AgentRegistry.dispatch(agent="warehouse", task="optimize_batch", context={})
        │
        ▼
WarehouseAgent.run(task, context)
        │
        ├── WarehouseService.get_pending_orders(warehouse_id)
        ├── WarehouseService.get_warehouse_graph(warehouse_id)
        ├── BatchingService.optimize_batches(orders, config)
        └── PickingService.optimize_pick_route(batch)
```

### 9.3 Service Layer Functions Exposed to Agents

#### Warehouse Domain
```text
WarehouseService.get_warehouse(id)
WarehouseService.get_warehouse_graph(id)
WarehouseService.get_pending_orders(warehouse_id)
WarehouseService.get_inventory(warehouse_id, product_id)
BatchingService.optimize_batches(order_ids, config)
PickingService.optimize_pick_route(batch_id)
```

#### Delivery/Safety Domain
```text
DeliveryService.get_delivery(id)
DeliveryService.get_route(delivery_id)
TelemetryService.get_recent_telemetry(vehicle_id, limit)
SafetyService.calculate_safety_score(delivery_id)
SafetyService.create_safety_event(event_data)
ETAService.calculate_eta(delivery_id, traffic_factor, weather_factor)
```

#### EV Charging Domain
```text
VehicleService.get_vehicle_state(vehicle_id)
ChargingService.get_stations(bbox, status)
ChargingService.get_available_slots(connector_id, time_range)
ChargingService.rank_charging_options(vehicle_state, destination)
ChargingService.reserve_slot(slot_id, vehicle_id, driver_id)
ChargingService.release_reservation(reservation_id)
```

### 9.4 Audit on Consequential Actions

Any agent action that creates, modifies, or cancels a database record must be passed through the service layer which appends an `AuditLog` entry with:

```python
AuditLog(
    user_id=None,              # null for autonomous agent actions
    action="AGENT_RESERVE_SLOT",
    resource_type="charging_reservations",
    resource_id=str(reservation_id),
    details={"agent": "ev_charging", "task_id": "A-123", "vehicle_id": 42},
    ip_address=None,
)
```

---

## 10. API Layer Architecture Constraints

Per ARCHITECTURE.md and AGENT_RULES.md:

1. **No business algorithms in routers.** Routers validate input, call a service function, and return the result. All optimization, scoring, and recommendation logic lives in `backend/app/services/` or `intelligence/`.

2. **Schema separation.** `backend/app/schemas/` contains only Pydantic I/O models. SQLAlchemy ORM models live in `backend/app/models/`. These must not be mixed.

3. **No direct ORM imports in routers.** Routers import service functions. Services import repositories. Repositories import ORM models.

4. **Dependency injection for database sessions.** All routers receive `AsyncSession` via `Depends(get_db)`.

5. **Versioned prefix locked.** The `/api/v1/` prefix is enforced in the main `FastAPI` app router include. Future breaking changes must use `/api/v2/`.

---

## 11. File Structure for Phase 2

```text
backend/
└── app/
    ├── api/
    │   └── v1/
    │       ├── __init__.py          ← aggregates all sub-routers
    │       ├── auth.py
    │       ├── users.py
    │       ├── warehouses.py
    │       ├── products.py
    │       ├── inventory.py
    │       ├── orders.py
    │       ├── batches.py
    │       ├── picking.py
    │       ├── deliveries.py
    │       ├── drivers.py
    │       ├── vehicles.py
    │       ├── telemetry.py
    │       ├── safety.py
    │       ├── charging.py
    │       ├── intelligence.py
    │       ├── audit.py
    │       └── dashboard.py
    ├── core/
    │   ├── database.py              ← existing
    │   ├── config.py                ← existing
    │   └── security.py              ← [NEW] JWT encode/decode, bcrypt, dependencies
    ├── schemas/
    │   ├── common.py                ← [NEW] Page[T], PaginationMeta, ErrorResponse
    │   ├── auth.py                  ← [NEW]
    │   ├── user.py                  ← [NEW]
    │   ├── warehouse.py             ← [NEW]
    │   ├── product.py               ← [NEW]
    │   ├── inventory.py             ← [NEW]
    │   ├── order.py                 ← [NEW]
    │   ├── batch.py                 ← [NEW]
    │   ├── picking.py               ← [NEW]
    │   ├── delivery.py              ← [NEW]
    │   ├── driver.py                ← [NEW]
    │   ├── vehicle.py               ← [NEW]
    │   ├── telemetry.py             ← [NEW]
    │   ├── safety.py                ← [NEW]
    │   ├── charging.py              ← [NEW]
    │   ├── intelligence.py          ← [NEW]
    │   ├── audit.py                 ← [NEW]
    │   └── dashboard.py             ← [NEW]
    └── services/
        ├── auth_service.py          ← [NEW]
        ├── user_service.py          ← [NEW]
        ├── warehouse_service.py     ← [NEW] (stub)
        ├── order_service.py         ← [NEW] (stub)
        ├── batch_service.py         ← [NEW] (stub)
        ├── delivery_service.py      ← [NEW] (stub)
        ├── charging_service.py      ← [NEW] (stub)
        └── dashboard_service.py     ← [NEW] (stub)
```

> Service stubs are initialized with correct signatures and docstrings but delegate complex algorithm implementations to later phases (warehouse optimization, intelligence, etc.).

---

## 12. Dependencies to Add (Phase 2)

```text
python-jose[cryptography]   ← JWT encode/decode
passlib[bcrypt]             ← password hashing
python-multipart            ← form data support (login form)
```

These must be added to `backend/requirements.txt`.

---

## 13. Verification Plan

### Automated Tests

```bash
# Run all existing Phase 1 tests to confirm they still pass
pytest tests/test_database.py -v

# New Phase 2 test suite
pytest tests/test_auth.py -v           # login, refresh, logout, JWT validation
pytest tests/test_rbac.py -v           # role enforcement for all protected routes
pytest tests/test_api_warehouses.py -v
pytest tests/test_api_orders.py -v
pytest tests/test_api_charging.py -v   # includes reservation conflict test
pytest tests/test_api_intelligence.py -v
```

### Manual Verification Checklist

- [ ] `POST /auth/login` returns access + refresh tokens
- [ ] `GET /auth/me` returns correct user with role
- [ ] `GET /warehouses` returns 200 for warehouse_operator, 403 for driver
- [ ] `POST /charging/reservations` blocks double-booking (409 on conflict)
- [ ] `POST /intelligence/run` returns a structured response (fallback or real)
- [ ] `GET /audit/logs` returns 403 for non-admin roles
- [ ] Pagination envelope appears on all list endpoints
- [ ] Error envelope format is consistent across all failure cases

---

*This document is the authoritative specification for Phase 2 implementation. No changes to the Phase 1 database schema are required by this API design. Implementation begins upon user approval.*
