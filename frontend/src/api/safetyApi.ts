import apiClient from '../lib/apiClient';
import type {
  Page,
  SafetyScoreRead,
  SafetyEventRead,
  SafetyAlertRead,
} from '../types/api';

export const safetyApi = {
  listScores: (params?: { page?: number; page_size?: number; delivery_id?: number }) =>
    apiClient.get<Page<SafetyScoreRead>>('/api/v1/safety/scores', { params }).then((r) => r.data),

  getScore: (deliveryId: number) =>
    apiClient.get<SafetyScoreRead>(`/api/v1/safety/scores/${deliveryId}`).then((r) => r.data),

  listEvents: (params?: { page?: number; page_size?: number; delivery_id?: number }) =>
    apiClient.get<Page<SafetyEventRead>>('/api/v1/safety/events', { params }).then((r) => r.data),

  listAlerts: (params?: { page?: number; page_size?: number; delivery_id?: number; acknowledged?: boolean }) =>
    apiClient.get<Page<SafetyAlertRead>>('/api/v1/safety/alerts', { params }).then((r) => r.data),

  acknowledgeAlert: (alertId: number) =>
    apiClient.patch<SafetyAlertRead>(`/api/v1/safety/alerts/${alertId}/acknowledge`).then((r) => r.data),
};
