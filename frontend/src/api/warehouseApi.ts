import apiClient from '../lib/apiClient';
import type {
  Page,
  WarehouseRead,
  WarehouseCreate,
  WarehouseUpdate,
  WarehouseZoneRead,
  NodeRead,
  EdgeRead,
  StorageLocationRead,
  WarehouseGraphRead,
  WarehouseValidationRead,
  ProductRead,
  InventoryRead,
  OrderRead,
  WarehouseOptimizationResultDTO,
} from '../types/api';

export const warehouseApi = {
  // Warehouses
  list: (params?: { page?: number; page_size?: number; status?: string }) =>
    apiClient.get<Page<WarehouseRead>>('/api/v1/warehouses', { params }).then((r) => r.data),

  get: (id: number) =>
    apiClient.get<WarehouseRead>(`/api/v1/warehouses/${id}`).then((r) => r.data),

  create: (data: WarehouseCreate) =>
    apiClient.post<WarehouseRead>('/api/v1/warehouses', data).then((r) => r.data),

  update: (id: number, data: WarehouseUpdate) =>
    apiClient.patch<WarehouseRead>(`/api/v1/warehouses/${id}`, data).then((r) => r.data),

  delete: (id: number) =>
    apiClient.delete(`/api/v1/warehouses/${id}`).then((r) => r.data),

  validate: (id: number) =>
    apiClient.get<WarehouseValidationRead>(`/api/v1/warehouses/${id}/validate`).then((r) => r.data),

  getGraph: (id: number) =>
    apiClient.get<WarehouseGraphRead>(`/api/v1/warehouses/${id}/graph`).then((r) => r.data),

  optimize: (
    id: number,
    payload?: {
      constraints?: {
        max_orders_per_batch?: number;
        max_weight_kg?: number;
        max_volume_cbm?: number;
      };
      use_2opt_routing?: boolean;
    }
  ) =>
    apiClient.post<WarehouseOptimizationResultDTO>(`/api/v1/warehouses/${id}/optimize`, payload || {}).then((r) => r.data),

  // Zones
  listZones: (warehouseId: number) =>
    apiClient.get<WarehouseZoneRead[]>(`/api/v1/warehouses/${warehouseId}/zones`).then((r) => r.data),

  createZone: (warehouseId: number, data: { zone_code: string; name: string; zone_type?: string }) =>
    apiClient.post<WarehouseZoneRead>(`/api/v1/warehouses/${warehouseId}/zones`, data).then((r) => r.data),

  updateZone: (warehouseId: number, zoneId: number, data: { zone_code?: string; name?: string; zone_type?: string }) =>
    apiClient.patch<WarehouseZoneRead>(`/api/v1/warehouses/${warehouseId}/zones/${zoneId}`, data).then((r) => r.data),

  deleteZone: (warehouseId: number, zoneId: number) =>
    apiClient.delete(`/api/v1/warehouses/${warehouseId}/zones/${zoneId}`).then((r) => r.data),

  // Nodes
  listNodes: (warehouseId: number) =>
    apiClient.get<NodeRead[]>(`/api/v1/warehouses/${warehouseId}/nodes`).then((r) => r.data),

  createNode: (warehouseId: number, data: { node_code: string; x_coord: number; y_coord: number; z_coord?: number; zone_id?: number | null; is_blocked?: boolean; is_depot?: boolean }) =>
    apiClient.post<NodeRead>(`/api/v1/warehouses/${warehouseId}/nodes`, data).then((r) => r.data),

  updateNode: (warehouseId: number, nodeId: number, data: { node_code?: string; x_coord?: number; y_coord?: number; z_coord?: number; zone_id?: number | null; is_blocked?: boolean; is_depot?: boolean }) =>
    apiClient.patch<NodeRead>(`/api/v1/warehouses/${warehouseId}/nodes/${nodeId}`, data).then((r) => r.data),

  deleteNode: (warehouseId: number, nodeId: number) =>
    apiClient.delete(`/api/v1/warehouses/${warehouseId}/nodes/${nodeId}`).then((r) => r.data),

  // Edges
  listEdges: (warehouseId: number) =>
    apiClient.get<EdgeRead[]>(`/api/v1/warehouses/${warehouseId}/edges`).then((r) => r.data),

  createEdge: (warehouseId: number, data: { from_node_id: number; to_node_id: number; distance_meters?: number; is_bidirectional?: boolean; is_blocked?: boolean }) =>
    apiClient.post<EdgeRead>(`/api/v1/warehouses/${warehouseId}/edges`, data).then((r) => r.data),

  updateEdge: (warehouseId: number, edgeId: number, data: { distance_meters?: number; is_bidirectional?: boolean; is_blocked?: boolean }) =>
    apiClient.patch<EdgeRead>(`/api/v1/warehouses/${warehouseId}/edges/${edgeId}`, data).then((r) => r.data),

  deleteEdge: (warehouseId: number, edgeId: number) =>
    apiClient.delete(`/api/v1/warehouses/${warehouseId}/edges/${edgeId}`).then((r) => r.data),

  // Storage Locations
  listLocations: (warehouseId: number) =>
    apiClient.get<StorageLocationRead[]>(`/api/v1/warehouses/${warehouseId}/locations`).then((r) => r.data),

  createLocation: (warehouseId: number, data: { node_id: number; location_code: string; aisle: string; shelf: string; bin: string; max_weight_kg?: number }) =>
    apiClient.post<StorageLocationRead>(`/api/v1/warehouses/${warehouseId}/locations`, data).then((r) => r.data),

  updateLocation: (warehouseId: number, locationId: number, data: { location_code?: string; aisle?: string; shelf?: string; bin?: string; max_weight_kg?: number }) =>
    apiClient.patch<StorageLocationRead>(`/api/v1/warehouses/${warehouseId}/locations/${locationId}`, data).then((r) => r.data),

  deleteLocation: (warehouseId: number, locationId: number) =>
    apiClient.delete(`/api/v1/warehouses/${warehouseId}/locations/${locationId}`).then((r) => r.data),

  // Products (Global)
  listProducts: (params?: { page?: number; page_size?: number; category?: string; sku?: string }) =>
    apiClient.get<Page<ProductRead>>('/api/v1/products', { params }).then((r) => r.data),

  createProduct: (data: { sku: string; name: string; category: string; unit_weight_kg: number; unit_volume_cbm: number; price: number }) =>
    apiClient.post<ProductRead>('/api/v1/products', data).then((r) => r.data),

  updateProduct: (id: number, data: { name?: string; category?: string; unit_weight_kg?: number; unit_volume_cbm?: number; price?: number }) =>
    apiClient.patch<ProductRead>(`/api/v1/products/${id}`, data).then((r) => r.data),

  deleteProduct: (id: number) =>
    apiClient.delete(`/api/v1/products/${id}`).then((r) => r.data),

  // Inventory
  listInventory: (params?: { page?: number; page_size?: number; warehouse_id?: number; product_id?: number }) =>
    apiClient.get<Page<InventoryRead>>('/api/v1/inventory', { params }).then((r) => r.data),

  upsertInventory: (data: { warehouse_id: number; location_id: number; product_id: number; quantity: number; reorder_threshold?: number }) =>
    apiClient.post<InventoryRead>('/api/v1/inventory', data).then((r) => r.data),

  updateInventory: (id: number, data: { quantity?: number; reorder_threshold?: number }) =>
    apiClient.patch<InventoryRead>(`/api/v1/inventory/${id}`, data).then((r) => r.data),

  deleteInventory: (id: number) =>
    apiClient.delete(`/api/v1/inventory/${id}`).then((r) => r.data),

  // Orders
  listOrders: (params?: { page?: number; page_size?: number; warehouse_id?: number; status?: string; priority?: string }) =>
    apiClient.get<Page<OrderRead>>('/api/v1/orders', { params }).then((r) => r.data),

  createOrder: (data: {
    order_number?: string;
    warehouse_id: number;
    customer_name?: string;
    destination_address?: string;
    customer_lat: number;
    customer_lon: number;
    promised_at: string;
    priority?: 'low' | 'normal' | 'high' | 'urgent';
    items: { product_id: number; quantity: number }[];
  }) => apiClient.post<OrderRead>('/api/v1/orders', data).then((r) => r.data),

  updateOrderStatus: (id: number, status: string) =>
    apiClient.patch<OrderRead>(`/api/v1/orders/${id}/status`, { status }).then((r) => r.data),

  deleteOrder: (id: number) =>
    apiClient.delete(`/api/v1/orders/${id}`).then((r) => r.data),
};
