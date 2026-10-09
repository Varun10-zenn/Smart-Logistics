import apiClient from '../lib/apiClient';
import type {
  Page,
  DeliveryRead,
  DeliveryRouteRead,
  ETAResponse,
} from '../types/api';

export const deliveryApi = {
  list: (params?: { page?: number; page_size?: number; status?: string }) =>
    apiClient.get<Page<DeliveryRead>>('/api/v1/deliveries', { params }).then((r) => r.data),

  get: (id: number) =>
    apiClient.get<DeliveryRead>(`/api/v1/deliveries/${id}`).then((r) => r.data),

  getRoute: (id: number) =>
    apiClient.get<DeliveryRouteRead>(`/api/v1/deliveries/${id}/route`).then((r) => r.data),

  getEta: (id: number) =>
    apiClient.get<ETAResponse>(`/api/v1/deliveries/${id}/eta`).then((r) => r.data),

  updateStatus: (id: number, status: string) =>
    apiClient.patch<DeliveryRead>(`/api/v1/deliveries/${id}/status`, { status }).then((r) => r.data),

  // Rider API
  getRiderActive: () =>
    apiClient.get<any[]>('/api/v1/deliveries/rider/active').then((r) => r.data),

  startDelivery: (id: number) =>
    apiClient.post(`/api/v1/deliveries/${id}/start`).then((r) => r.data),

  deliverStop: (deliveryId: number, stopId: number) =>
    apiClient.post(`/api/v1/deliveries/${deliveryId}/stops/${stopId}/deliver`).then((r) => r.data),

  generateFleet: (warehouseId: number, data: { riders: number; ev_count: number }) =>
    apiClient.post(`/api/v1/warehouses/${warehouseId}/fleet/generate`, data).then((r) => r.data),

  // Simulation API
  startSimulation: (id: number, profile: string = 'normal') =>
    apiClient.post(`/api/v1/deliveries/${id}/simulation/start`, { profile }).then((r) => r.data),

  stopSimulation: (id: number) =>
    apiClient.post(`/api/v1/deliveries/${id}/simulation/stop`).then((r) => r.data),

  getSimulationStatus: (id: number) =>
    apiClient.get(`/api/v1/deliveries/${id}/simulation`).then((r) => r.data),

  getChargingRecommendation: (id: number) =>
    apiClient.get(`/api/v1/deliveries/${id}/charging-recommendation`).then((r) => r.data),
};
