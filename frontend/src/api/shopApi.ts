import apiClient from '../lib/apiClient';

export interface ShopProductItem {
  id: number;
  sku: string;
  name: string;
  category?: string | null;
  unit_weight_kg: number;
  unit_volume_cbm: number;
  price: number;
  available_quantity: number;
}

export interface ShopProductsResponse {
  warehouse_id: number;
  warehouse_name: string;
  distance_km: number;
  products: ShopProductItem[];
}

export interface CheckoutItem {
  product_id: number;
  quantity: number;
}

export interface CheckoutRequest {
  items: CheckoutItem[];
  lat: number;
  lon: number;
  address: string;
}

export interface TimelineStep {
  step: string;
  completed: boolean;
  timestamp?: string | null;
}

export interface CustomerOrderRead {
  id: number;
  order_number: string;
  warehouse_id: number;
  warehouse_name?: string | null;
  customer_name?: string | null;
  destination_address: string;
  customer_lat: number;
  customer_lon: number;
  status: string;
  priority: string;
  created_at: string;
  promised_at: string;
  timeline: TimelineStep[];
  items: Array<{
    id?: number;
    product_id: number;
    product_name?: string;
    product_sku?: string;
    quantity: number;
    unit_price?: number;
  }>;
  delivery_status?: string | null;
  rider_first_name?: string | null;
  vehicle_type?: string | null;
  stop_eta?: string | null;
  stops_before?: number | null;
  route_geometry?: string | null;
  rider_last_lat?: number | null;
  rider_last_lon?: number | null;
}

export const shopApi = {
  getProducts: (lat: number, lon: number) =>
    apiClient
      .get<ShopProductsResponse>('/api/v1/shop/products', { params: { lat, lon } })
      .then((r) => r.data),

  checkout: (data: CheckoutRequest) =>
    apiClient.post<CustomerOrderRead>('/api/v1/shop/checkout', data).then((r) => r.data),

  listOrders: () =>
    apiClient.get<CustomerOrderRead[]>('/api/v1/shop/orders').then((r) => r.data),

  getOrder: (id: number) =>
    apiClient.get<CustomerOrderRead>(`/api/v1/shop/orders/${id}`).then((r) => r.data),
};
