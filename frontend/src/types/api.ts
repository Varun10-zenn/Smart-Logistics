// ─── Pagination ────────────────────────────────────────────────────────────
export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface Page<T> {
  items: T[];
  pagination: PaginationMeta;
}

// ─── Auth ───────────────────────────────────────────────────────────────────
export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserRead {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  role: string | { id?: number; code?: string; description?: string };
  warehouse_id?: number | null;
}

export function getRoleCode(role: UserRead['role'] | null | undefined): string {
  if (!role) return '';
  if (typeof role === 'string') return role;
  if (typeof role === 'object' && role.code) return role.code;
  return '';
}

// ─── Warehouses ─────────────────────────────────────────────────────────────
export interface WarehouseCreate {
  code: string;
  name: string;
  latitude: number;
  longitude: number;
  address?: string;
}

export interface WarehouseUpdate {
  name?: string;
  address?: string;
  status?: string;
}

export interface WarehouseRead {
  id: number;
  code: string;
  name: string;
  latitude: number;
  longitude: number;
  address?: string;
  status: string;
  created_at?: string;
}

export interface WarehouseZoneRead {
  id: number;
  warehouse_id: number;
  zone_code: string;
  name: string;
  zone_type: string;
}

export interface NodeRead {
  id: number;
  warehouse_id: number;
  node_code: string;
  x_coord: number;
  y_coord: number;
  z_coord: number;
  is_blocked: boolean;
  is_depot: boolean;
  zone_id?: number | null;
}

export interface EdgeRead {
  id: number;
  warehouse_id: number;
  from_node_id: number;
  to_node_id: number;
  distance_meters: number;
  is_bidirectional: boolean;
  is_blocked: boolean;
}

export interface StorageLocationRead {
  id: number;
  node_id: number;
  location_code: string;
  aisle: string;
  shelf: string;
  bin: string;
  max_weight_kg: number;
}

export interface WarehouseGraphRead {
  warehouse_id: number;
  nodes: NodeRead[];
  edges: EdgeRead[];
  locations: StorageLocationRead[];
}

export interface WarehouseValidationRead {
  valid: boolean;
  errors: string[];
}

export interface ProductRead {
  id: number;
  sku: string;
  name: string;
  category: string;
  unit_weight_kg: number;
  unit_volume_cbm: number;
  price: number;
  created_at?: string;
}

export interface InventoryRead {
  id: number;
  warehouse_id: number;
  location_id: number;
  product_id: number;
  quantity: number;
  reorder_threshold: number;
  updated_at?: string;
}

export interface OrderItemRead {
  id: number;
  product_id: number;
  quantity: number;
}

export interface OrderRead {
  id: number;
  order_number: string;
  warehouse_id: number;
  customer_name?: string;
  customer_lat: number;
  customer_lon: number;
  created_at: string;
  promised_at: string;
  priority: string;
  status: string;
  items: OrderItemRead[];
}

export interface BatchSummaryDTO {
  batch_id: number;
  batch_code: string;
  order_ids: number[];
  total_weight_kg: number;
  total_volume_cbm: number;
  pick_route_id: number;
  total_distance_meters: number;
  estimated_duration_minutes: number;
  algorithm_used: string;
  steps_count: number;
}

export interface BatchRead {
  id: number;
  batch_code: string;
  warehouse_id: number;
  status: string;
  total_weight_kg: number;
  total_volume_cbm: number;
  created_at: string;
  order_ids?: number[];
  steps_count?: number;
}

export interface WarehouseOptimizationResultDTO {
  success: boolean;
  warehouse_id: number;
  total_pending_orders: number;
  eligible_orders_count: number;
  generated_batches_count: number;
  batches: BatchSummaryDTO[];
  unassigned_order_ids: number[];
  unassigned_reasons: Record<number, string>;
  overall_distance_reduction_pct: number | null;
  execution_time_ms: number;
  recommendation_id?: number | null;
  failure_reason?: string | null;
}


// ─── Deliveries ─────────────────────────────────────────────────────────────
export interface DeliveryRead {
  id: number;
  delivery_code: string;
  batch_id: number;
  driver_id: number;
  vehicle_id: number;
  status: string;
  scheduled_dispatch_time: string;
  estimated_eta: string | null;
  created_at: string;
}

export interface ETAResponse {
  delivery_id: number;
  eta: string;
  base_route_minutes: number;
  traffic_factor: number;
  weather_factor: number;
  algorithm: string;
  confidence: number | null;
}

export interface DeliveryRouteRead {
  id: number;
  delivery_id: number;
  total_distance_km: number;
  estimated_travel_minutes: number;
  traffic_factor: number;
  weather_factor: number;
  route_geometry?: string | null;
}

export interface DeliveryStopRead {
  id: number;
  delivery_id: number;
  order_id: number;
  stop_sequence: number;
  status: string;
  estimated_arrival: string;
  actual_arrival: string | null;
}

// ─── Drivers & Vehicles ─────────────────────────────────────────────────────
export interface DriverRead {
  id: number;
  user_id: number;
  license_number: string;
  rating: number;
  status: string;
}

export interface VehicleRead {
  id: number;
  registration_number: string;
  vehicle_type_id: number;
  current_soc_percent: number;
  status: string;
  last_telemetry_at: string | null;
}

// ─── Telemetry ───────────────────────────────────────────────────────────────
export interface TelemetryEventRead {
  id: number;
  vehicle_id: number;
  delivery_id: number | null;
  timestamp: string;
  latitude: number;
  longitude: number;
  speed_kmh: number;
  acceleration_ms2: number;
  heading_deg: number | null;
  soc_percent: number | null;
}

// ─── Safety ──────────────────────────────────────────────────────────────────
export interface SafetyScoreRead {
  id: number;
  delivery_id: number;
  score: number;
  speed_score: number;
  braking_score: number;
  acceleration_score: number;
  route_score: number;
  calculated_at: string;
}

export interface SafetyEventRead {
  id: number;
  delivery_id: number;
  event_type: string;
  severity: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  value: number;
  threshold: number;
}

export interface SafetyAlertRead {
  id: number;
  delivery_id: number;
  alert_type: string;
  severity: string;
  message: string;
  acknowledged: boolean;
  created_at: string;
}

// ─── Charging ────────────────────────────────────────────────────────────────
export interface ChargingStationRead {
  id: number;
  station_code: string;
  name: string;
  latitude: number;
  longitude: number;
  total_connectors: number;
  status: string;
}

export interface ChargingConnectorRead {
  id: number;
  station_id: number;
  connector_number: number;
  connector_type: string;
  max_power_kw: number;
  status: string;
}

export interface ChargingSlotRead {
  id: number;
  connector_id: number;
  start_time: string;
  end_time: string;
  is_booked: boolean;
}

export interface ChargingReservationRead {
  id: number;
  reservation_code: string;
  slot_id: number;
  vehicle_id: number;
  driver_id: number;
  delivery_id: number | null;
  start_time: string;
  end_time: string;
  status: string;
  created_at: string;
  driver_name?: string | null;
  vehicle_code?: string | null;
  station_name?: string | null;
  connector_code?: string | null;
  slot_time_range?: string | null;
}

export interface ChargingSessionRead {
  id: number;
  reservation_id: number | null;
  connector_id: number;
  vehicle_id: number;
  start_time: string;
  end_time: string | null;
  initial_soc_percent: number;
  final_soc_percent: number | null;
  energy_kwh_delivered: number;
  driver_name?: string | null;
  vehicle_code?: string | null;
  station_name?: string | null;
  connector_code?: string | null;
}

export interface ChargingCandidate {
  station_id: number;
  connector_id: number;
  slot_id: number | null;
  estimated_wait_minutes: number;
  estimated_charge_minutes: number;
  route_detour_km: number;
  station_score: number;
}

export interface ChargingRecommendRequest {
  vehicle_id: number;
  current_soc_percent: number;
  destination_lat: number;
  destination_lon: number;
  current_lat: number;
  current_lon: number;
  minimum_soc_after_charge: number;
}

export interface ChargingRecommendResponse {
  recommended_station_id: number;
  recommended_connector_id: number;
  recommended_slot_id: number | null;
  estimated_wait_minutes: number;
  estimated_charge_minutes: number;
  route_detour_km: number;
  station_score: number;
  explanation: string;
  algorithm: string;
  fallback_used: boolean;
  candidate_stations: ChargingCandidate[];
  optimization_metadata: Record<string, unknown>;
}

// ─── Intelligence ────────────────────────────────────────────────────────────
export interface IntelligenceRequest {
  query: string;
  context?: Record<string, unknown>;
}

export interface IntelligenceResponse {
  recommendation: string;
  reasoning: string;
  confidence: number;
  fallback: boolean;
  metadata: Record<string, unknown>;
}

// ─── Dashboard ───────────────────────────────────────────────────────────────
export interface DashboardData {
  active_deliveries: number;
  total_warehouses: number;
  safety_alerts_open: number;
  charging_stations_operational: number;
  recent_events: SafetyAlertRead[];
}

// ─── Audit ───────────────────────────────────────────────────────────────────
export interface AuditLogRead {
  id: number;
  user_id: number;
  action: string;
  resource_type: string;
  resource_id: string;
  ip_address: string | null;
  created_at: string;
}
