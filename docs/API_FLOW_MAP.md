# Smart Logistics Platform — API Flow Map

This document lists actual FastAPI endpoints implemented under `backend/app/api/v1/`.

| Feature | HTTP Method | Endpoint | Input Schema | Auth Required | Allowed Roles | Service / Handler | Output Schema |
| ------- | ----------- | -------- | ------------ | ------------- | ------------- | ----------------- | ------------- |
| **User Login** | `POST` | `/api/v1/auth/login` | `Body(username, password)` | No | Public | `auth_service.login_user` | `Token` |
| **Current User** | `GET` | `/api/v1/auth/me` | None | Yes | All roles | `get_current_user` | `UserRead` |
| **List Warehouses** | `GET` | `/api/v1/warehouses` | Query params (page, limit) | Yes | All roles | `warehouse_service.list_warehouses` | `Page[WarehouseRead]` |
| **Create Warehouse** | `POST` | `/api/v1/warehouses` | `WarehouseCreate` | Yes | `admin` | `warehouse_service.create_warehouse` | `WarehouseRead` |
| **Get Warehouse** | `GET` | `/api/v1/warehouses/{id}` | Path param (`id`) | Yes | All roles | `warehouse_service.get_warehouse` | `WarehouseRead` |
| **Update Warehouse** | `PATCH` | `/api/v1/warehouses/{id}` | `WarehouseUpdate` | Yes | `admin` | `warehouse_service.update_warehouse` | `WarehouseRead` |
| **Delete Warehouse** | `DELETE` | `/api/v1/warehouses/{id}` | Path param (`id`) | Yes | `admin` | `warehouse_service.delete_warehouse` | 204 No Content |
| **Validate Layout** | `GET` | `/api/v1/warehouses/{id}/validate` | Path param (`id`) | Yes | All roles | `warehouse_service.validate_warehouse_layout` | `WarehouseValidationRead` |
| **Get Graph** | `GET` | `/api/v1/warehouses/{id}/graph` | Path param (`id`) | Yes | All roles | `warehouse_service.get_warehouse_graph` | `WarehouseGraphRead` |
| **List Zones** | `GET` | `/api/v1/warehouses/{id}/zones` | Path param (`id`) | Yes | All roles | `warehouse_service.list_zones` | `List[WarehouseZoneRead]` |
| **Create Zone** | `POST` | `/api/v1/warehouses/{id}/zones` | `WarehouseZoneCreate` | Yes | `admin` | `warehouse_service.create_zone` | `WarehouseZoneRead` |
| **Delete Zone** | `DELETE` | `/api/v1/warehouses/{id}/zones/{zone_id}` | Path params | Yes | `admin` | `warehouse_service.delete_zone` | 204 No Content |
| **List Nodes** | `GET` | `/api/v1/warehouses/{id}/nodes` | Path param (`id`) | Yes | All roles | `warehouse_service.list_nodes` | `List[NodeRead]` |
| **Create Node** | `POST` | `/api/v1/warehouses/{id}/nodes` | `WarehouseNodeCreate` | Yes | `admin` | `warehouse_service.create_node` | `NodeRead` |
| **Update Node** | `PATCH` | `/api/v1/warehouses/{id}/nodes/{node_id}` | `WarehouseNodeUpdate` | Yes | `admin` | `warehouse_service.update_node` | `NodeRead` |
| **Delete Node** | `DELETE` | `/api/v1/warehouses/{id}/nodes/{node_id}` | Path params | Yes | `admin` | `warehouse_service.delete_node` | 204 No Content |
| **List Edges** | `GET` | `/api/v1/warehouses/{id}/edges` | Path param (`id`) | Yes | All roles | `warehouse_service.list_edges` | `List[EdgeRead]` |
| **Create Edge** | `POST` | `/api/v1/warehouses/{id}/edges` | `WarehouseEdgeCreate` | Yes | `admin` | `warehouse_service.create_edge` | `EdgeRead` |
| **Delete Edge** | `DELETE` | `/api/v1/warehouses/{id}/edges/{edge_id}` | Path params | Yes | `admin` | `warehouse_service.delete_edge` | 204 No Content |
| **List Locations** | `GET` | `/api/v1/warehouses/{id}/locations` | Path param (`id`) | Yes | All roles | `warehouse_service.list_locations` | `List[StorageLocationRead]` |
| **Create Location** | `POST` | `/api/v1/warehouses/{id}/locations` | `StorageLocationCreate` | Yes | `admin` | `warehouse_service.create_location` | `StorageLocationRead` |
| **Delete Location** | `DELETE` | `/api/v1/warehouses/{id}/locations/{location_id}` | Path params | Yes | `admin` | `warehouse_service.delete_location` | 204 No Content |
| **Optimize Warehouse** | `POST` | `/api/v1/warehouses/{id}/optimize` | `{constraints, use_2opt_routing}` | Yes | `admin`, `warehouse_operator` | `WarehouseOptimizationService.optimize_warehouse` | `WarehouseOptimizationResultDTO` |
| **List Products** | `GET` | `/api/v1/products` | Query params | Yes | All roles | `product_service.list_products` | `Page[ProductRead]` |
| **Create Product** | `POST` | `/api/v1/products` | `ProductCreate` | Yes | `admin` | `product_service.create_product` | `ProductRead` |
| **Delete Product** | `DELETE` | `/api/v1/products/{id}` | Path param (`id`) | Yes | `admin` | `product_service.delete_product` | 204 No Content |
| **List Inventory** | `GET` | `/api/v1/inventory` | Query params | Yes | All roles | `inventory_service.list_inventory` | `Page[InventoryRead]` |
| **Upsert Inventory** | `POST` | `/api/v1/inventory` | `InventoryCreate` | Yes | `admin`, `warehouse_operator` | `inventory_service.upsert_inventory` | `InventoryRead` |
| **Delete Inventory** | `DELETE` | `/api/v1/inventory/{id}` | Path param (`id`) | Yes | `admin`, `warehouse_operator` | `inventory_service.delete_inventory` | 204 No Content |
| **List Orders** | `GET` | `/api/v1/orders` | Query params | Yes | All roles | `order_service.list_orders` | `Page[OrderRead]` |
| **Create Order** | `POST` | `/api/v1/orders` | `OrderCreate` | Yes | `admin`, `warehouse_operator` | `order_service.create_order` | `OrderRead` |
| **Customer Register** | `POST` | `/api/v1/auth/register` | `RegisterRequest` | No | Public | `auth_service.register_customer` | `UserRead` |
| **Browse Shop Products** | `GET` | `/api/v1/shop/products` | Query (`lat`, `lon`) | Yes | `customer`, `admin` | `shop_service.get_shop_products` | `ShopProductsResponse` |
| **Customer Checkout** | `POST` | `/api/v1/shop/checkout` | `CheckoutRequest` | Yes | `customer` | `shop_service.checkout` | `CustomerOrderRead` |
| **List Customer Orders** | `GET` | `/api/v1/shop/orders` | None | Yes | `customer` | `shop_service.list_customer_orders` | `List[CustomerOrderRead]` |
| **Get Customer Order** | `GET` | `/api/v1/shop/orders/{id}` | Path param (`id`) | Yes | `customer` | `shop_service.get_customer_order` | `CustomerOrderRead` |
| **Get Batch Pick Route** | `GET` | `/api/v1/batches/{id}/pick-route` | Path param (`id`) | Yes | `admin`, `warehouse_operator` | `picking_service.get_batch_pick_route` | `PickRouteRead` |
| **Complete Pick Step** | `POST` | `/api/v1/pick-route-steps/{id}/complete` | Path param (`id`) | Yes | `admin`, `warehouse_operator` | `picking_service.complete_pick_route_step` | `PickRouteStepRead` |
| **Generate Layout** | `POST` | `/api/v1/warehouses/{id}/layout/generate` | `LayoutGenerateRequest` | Yes | `admin` | `warehouse_service.generate_warehouse_layout` | `WarehouseValidationRead` |
| **Import Products (CSV)** | `POST` | `/api/v1/products/import` | File (CSV) | Yes | `admin` | `product_service.import_products` | `ImportResult` |
| **Product Import Template** | `GET` | `/api/v1/products/import/template` | None | Yes | `admin` | `products.get_product_import_template` | `text/csv` |
| **Import Inventory (CSV)** | `POST` | `/api/v1/inventory/import` | File (CSV) | Yes | `admin`, `warehouse_operator` | `inventory_service.import_inventory` | `ImportResult` |
| **Inventory Import Template** | `GET` | `/api/v1/inventory/import/template` | None | Yes | `admin`, `warehouse_operator` | `inventory.get_inventory_import_template` | `text/csv` |

