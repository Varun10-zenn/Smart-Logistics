# Smart Logistics Platform — Architecture Diagram & System Topology

This document provides visual ASCII topology diagrams and architectural mappings for the Smart Logistics Platform repository.

```
 +-----------------------------------------------------------------------------------+
 |                                   REACT UI LAYER                                  |
 |  [LoginPage]  [DashboardPage]  [WarehousePage]  [DeliveriesPage]  [SafetyPage] ...|
 +-----------------------------------------+-----------------------------------------+
                                           |
                                           | HTTP / REST (Axios + TanStack Query)
                                           v
 +-----------------------------------------------------------------------------------+
 |                              FASTAPI BACKEND ROUTER                               |
 |   /api/v1/auth    /api/v1/warehouses    /api/v1/batches    /api/v1/deliveries   |
 +-----------------------------------------+-----------------------------------------+
                                           |
                                           | Authentication & RBAC Middleware
                                           v
 +-----------------------------------------------------------------------------------+
 |                             SECURITY & VALIDATION LAYER                           |
 |   - PyJWT (Token decode & JTI denylist check)                                     |
 |   - require_role("admin", "warehouse_operator", "fleet_manager", "driver", ...)   |
 |   - Pydantic Schema Validation (Type Coercion & Payload Checks)                   |
 +-----------------------------------------+-----------------------------------------+
                                           |
                                           v
 +-----------------------------------------------------------------------------------+
 |                              DOMAIN SERVICE LAYER                                 |
 | +-----------------------+ +------------------------+ +--------------------------+ |
 | |  Warehouse Optimization| | Delivery Routing Engine| | Safety & Telemetry Service| |
 | |  - Graph Engine       | | - OSRM Router API      | | - Rule Threshold Evaluator| |
 | |  - OrderBatcher       | | - Haversine Fallback | | - 0-100 Score Deductor   | |
 | |  - PickRouting Engine | | - ETA Factor Calculation| - Alert Dispatcher      | |
 | +-----------------------+ +------------------------+ +--------------------------+ |
 +-----------------------------------------+-----------------------------------------+
                                           |
                                           v
 +-----------------------------------------------------------------------------------+
 |                               SQLALCHEMY ORM LAYER                                |
 |   Models: User, Warehouse, WarehouseNode, Order, Batch, Delivery, SafetyScore, ... |
 +-----------------------------------------+-----------------------------------------+
                                           |
                                           v
 +-----------------------------------------------------------------------------------+
 |                                PERSISTENCE LAYER                                  |
 |   MySQL Database (InnoDB Engine) / SQLite Fallback Mode                           |
 +-----------------------------------------------------------------------------------+
```
