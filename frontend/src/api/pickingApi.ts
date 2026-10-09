import apiClient from '../lib/apiClient';
import type { Page, BatchRead } from '../types/api';

export interface PickRouteStepRead {
  id: number;
  step_number: number;
  location_id: number;
  location_code: string;
  node_id: number;
  product_id: number;
  product_sku: string;
  product_name: string;
  quantity_to_pick: number;
  is_completed: boolean;
  x_coord: number;
  y_coord: number;
}

export interface PickRouteRead {
  id: number;
  batch_id: number;
  total_distance_meters: number;
  estimated_minutes: number;
  algorithm: string;
  created_at: string;
  steps: PickRouteStepRead[];
}

export const pickingApi = {
  listBatches: (params?: { page?: number; page_size?: number; warehouse_id?: number; status?: string }) =>
    apiClient.get<Page<BatchRead>>('/api/v1/batches', { params }).then((r) => r.data),

  getBatchPickRoute: (batchId: number) =>
    apiClient.get<PickRouteRead>(`/api/v1/batches/${batchId}/pick-route`).then((r) => r.data),

  completeStep: (stepId: number) =>
    apiClient.post<PickRouteStepRead>(`/api/v1/pick-route-steps/${stepId}/complete`).then((r) => r.data),
};
