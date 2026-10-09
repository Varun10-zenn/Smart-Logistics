import apiClient from '../lib/apiClient';
import type { WarehouseGraphRead } from '../types/api';

export interface ImportResult {
  created: number;
  updated: number;
  errors: Array<{
    row: number;
    message: string;
  }>;
}

export interface LayoutGeneratePayload {
  aisles: number;
  shelves_per_aisle: number;
  aisle_spacing_m: number;
  shelf_spacing_m: number;
  replace_existing: boolean;
}

export const importApi = {
  // Layout Generator
  generateLayout: (warehouseId: number, data: LayoutGeneratePayload) =>
    apiClient
      .post<WarehouseGraphRead>(`/api/v1/warehouses/${warehouseId}/layout/generate`, data)
      .then((r) => r.data),

  // CSV Product Import
  importProducts: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient
      .post<ImportResult>('/api/v1/products/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data);
  },

  getProductImportTemplateUrl: () => '/api/v1/products/import/template',

  // CSV Inventory Import
  importInventory: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient
      .post<ImportResult>('/api/v1/inventory/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data);
  },

  getInventoryImportTemplateUrl: () => '/api/v1/inventory/import/template',

  // CSV Stores Import
  importStores: (file: File, options?: { generate_layout?: boolean; aisles?: number; shelves_per_aisle?: number }) => {
    const formData = new FormData();
    formData.append('file', file);
    const params = new URLSearchParams();
    if (options?.generate_layout !== undefined) params.append('generate_layout', String(options.generate_layout));
    if (options?.aisles !== undefined) params.append('aisles', String(options.aisles));
    if (options?.shelves_per_aisle !== undefined) params.append('shelves_per_aisle', String(options.shelves_per_aisle));
    return apiClient
      .post<ImportResult & { skipped: number }>(`/api/v1/warehouses/import?${params.toString()}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data);
  },
};
