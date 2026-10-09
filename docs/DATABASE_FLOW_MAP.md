# Smart Logistics Platform — Database Flow Map

This document outlines the database tables, relationships, and state mutations managed by SQLAlchemy ORM models in `backend/app/models/`.

## 1. Domain Tables & Key Relationships

### Authentication & Users
- **`users`**: `id` (PK), `username`, `email`, `hashed_password`, `role_id` (FK -> `roles.id`), `is_active`.
- **`roles`**: `id` (PK), `name` (`admin`, `warehouse_operator`, `fleet_manager`, `driver`, `station_admin`, `customer`), `description`.

### Warehouse & Inventory
- **`warehouses`**: `id` (PK), `code`, `name`, `latitude`, `longitude`, `status`, `address`.
- **`warehouse_zones`**: `id` (PK), `warehouse_id` (FK -> `warehouses.id`), `zone_code`, `name`, `zone_type`.
- **`warehouse_nodes`**: `id` (PK), `warehouse_id` (FK -> `warehouses.id`), `zone_id` (FK), `node_code`, `x_coord`, `y_coord`, `z_coord`, `is_blocked`, `is_depot` (Boolean, default False).
- **`warehouse_edges`**: `id` (PK), `warehouse_id` (FK), `from_node_id` (FK -> `warehouse_nodes.id`), `to_node_id` (FK -> `warehouse_nodes.id`), `distance_meters`, `is_bidirectional`, `is_blocked`.
- **`storage_locations`**: `id` (PK), `node_id` (FK -> `warehouse_nodes.id`), `location_code`, `aisle`, `shelf`, `bin`, `max_weight_kg`.
- **`products`**: `id` (PK), `sku`, `name`, `category`, `unit_weight_kg`, `unit_volume_cbm`, `price`.
- **`inventory`**: `id` (PK), `warehouse_id` (FK), `product_id` (FK), `location_id` (FK), `quantity`, `reorder_threshold`.

### Orders & Batches
- **`orders`**: `id` (PK), `order_number`, `warehouse_id` (FK), `customer_id` (FK -> `users.id`), `customer_name`, `destination_address`, `destination_lat`, `destination_lon`, `priority`, `status` (`pending`, `batched`, `picked`, `delivered`, `cancelled`).
- **`order_items`**: `id` (PK), `order_id` (FK -> `orders.id`), `product_id` (FK -> `products.id`), `quantity`, `unit_price`.
- **`batches`**: `id` (PK), `batch_code`, `warehouse_id` (FK), `status`, `max_orders`, `total_weight_kg`.
- **`batch_orders`**: `id` (PK), `batch_id` (FK -> `batches.id`), `order_id` (FK -> `orders.id`).
- **`pick_routes`**: `id` (PK), `batch_id` (FK -> `batches.id`), `total_distance_meters`, `estimated_duration_minutes`, `algorithm_used`.
- **`pick_route_steps`**: `id` (PK), `pick_route_id` (FK), `step_number`, `location_id` (FK), `product_id` (FK), `quantity_to_pick`, `is_completed`.

---

## 2. User Action to Database State Mutation Mappings

### Action: Customer Checkout
```
Frontend: Customer submits cart items at location (lat, lon)
  └─► API: POST /api/v1/shop/checkout
        └─► Service: shop_service.checkout
              ├─► SELECT candidate warehouses within SERVICE_RADIUS_KM (10km) sorted by distance
              ├─► Compute available stock = SUM(Inventory.quantity) - SUM(pending/batched OrderItem.quantity)
              ├─► SELECT nearest warehouse fulfilling ALL items
              ├─► Lock inventory rows WITH FOR UPDATE
              ├─► INSERT INTO orders (order_number, warehouse_id, customer_id, customer_name, destination_lat, destination_lon, status='pending')
              └─► INSERT INTO order_items (order_id, product_id, quantity, unit_price)
```

### Action: Picker Completes Step & Deducts Inventory Stock
```
Picker / Operator: Completes picking step
  └─► API: POST /api/v1/pick-route-steps/{id}/complete
        └─► Service: picking_service.complete_pick_route_step
              ├─► IF step.is_completed == True RETURN (Idempotent double-complete protection)
              ├─► SELECT Inventory WITH FOR UPDATE WHERE location_id = ? AND product_id = ?
              ├─► IF Inventory.quantity < quantity_to_pick RETURN 409 Conflict
              ├─► UPDATE inventory SET quantity = quantity - quantity_to_pick WHERE location_id = ? AND product_id = ?
              ├─► UPDATE pick_route_steps SET is_completed = True WHERE id = ?
              └─► IF ALL steps in pick_route completed:
                    ├─► UPDATE batches SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?
                    └─► UPDATE orders SET status = 'picked' WHERE id IN (SELECT order_id FROM batch_orders WHERE batch_id = ?)
```

