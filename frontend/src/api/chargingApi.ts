import apiClient from '../lib/apiClient';
import type {
  Page,
  ChargingStationRead,
  ChargingConnectorRead,
  ChargingSlotRead,
  ChargingReservationRead,
  ChargingSessionRead,
  ChargingRecommendRequest,
  ChargingRecommendResponse,
} from '../types/api';

export const chargingApi = {
  listStations: (params?: { page?: number; page_size?: number; status?: string }) =>
    apiClient.get<Page<ChargingStationRead>>('/api/v1/charging/stations', { params }).then((r) => r.data),

  getStation: (id: number) =>
    apiClient.get<ChargingStationRead>(`/api/v1/charging/stations/${id}`).then((r) => r.data),

  createStation: (data: { station_code: string; name: string; latitude: number; longitude: number; total_connectors: number }) =>
    apiClient.post<ChargingStationRead>('/api/v1/charging/stations', data).then((r) => r.data),

  deleteStation: (id: number) =>
    apiClient.delete(`/api/v1/charging/stations/${id}`),

  listConnectors: (params?: { page?: number; page_size?: number; station_id?: number; status?: string }) =>
    apiClient.get<Page<ChargingConnectorRead>>('/api/v1/charging/connectors', { params }).then((r) => r.data),

  createConnector: (stationId: number, data: { connector_type: string; max_power_kw: number }) =>
    apiClient.post<ChargingConnectorRead>(`/api/v1/charging/stations/${stationId}/connectors`, data).then((r) => r.data),

  listSlots: (params?: { page?: number; page_size?: number; connector_id?: number; available_only?: boolean }) =>
    apiClient.get<Page<ChargingSlotRead>>('/api/v1/charging/slots', { params }).then((r) => r.data),

  generateSlots: (connectorId: number, data?: { slot_minutes?: number; hours_ahead?: number }) =>
    apiClient.post<ChargingSlotRead[]>(`/api/v1/charging/connectors/${connectorId}/slots/generate`, data || {}).then((r) => r.data),

  createReservation: (data: { slot_id: number; vehicle_id: number; driver_id: number; delivery_id?: number }) =>
    apiClient.post<ChargingReservationRead>('/api/v1/charging/reservations', data).then((r) => r.data),

  listReservations: (params?: { page?: number; page_size?: number; status?: string }) =>
    apiClient.get<Page<ChargingReservationRead>>('/api/v1/charging/reservations', { params }).then((r) => r.data),

  cancelReservation: (id: number) =>
    apiClient.delete(`/api/v1/charging/reservations/${id}`),

  startSession: (reservationId: number) =>
    apiClient.post<ChargingSessionRead>(`/api/v1/charging/reservations/${reservationId}/start`).then((r) => r.data),

  completeSession: (reservationId: number, targetSoc: number = 90) =>
    apiClient.post<ChargingSessionRead>(`/api/v1/charging/reservations/${reservationId}/complete?target_soc=${targetSoc}`).then((r) => r.data),

  listSessions: (params?: { page?: number; page_size?: number; vehicle_id?: number; connector_id?: number }) =>
    apiClient.get<Page<ChargingSessionRead>>('/api/v1/charging/sessions', { params }).then((r) => r.data),

  recommend: (req: ChargingRecommendRequest) =>
    apiClient.post<ChargingRecommendResponse>('/api/v1/charging/recommend', req).then((r) => r.data),
};
