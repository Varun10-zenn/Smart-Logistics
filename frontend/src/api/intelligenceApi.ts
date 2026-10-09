import apiClient from '../lib/apiClient';
import type { IntelligenceRequest, IntelligenceResponse, DashboardData, Page, AuditLogRead } from '../types/api';

export const intelligenceApi = {
  query: (req: IntelligenceRequest) =>
    apiClient.post<IntelligenceResponse>('/api/v1/intelligence', req).then((r) => r.data),

  dashboard: () =>
    apiClient.get<DashboardData>('/api/v1/dashboard').then((r) => r.data),

  auditLogs: (params?: { page?: number; page_size?: number }) =>
    apiClient.get<Page<AuditLogRead>>('/api/v1/audit-logs', { params }).then((r) => r.data),
};
