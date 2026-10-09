import { HealthCheck, DatabaseHealth } from '../types/health';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export async function fetchHealth(): Promise<HealthCheck> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
  }
  return response.json();
}

export async function fetchDatabaseHealth(): Promise<DatabaseHealth> {
  const response = await fetch(`${API_BASE_URL}/health/db`);
  if (!response.ok) {
    throw new Error(`Database health check failed with status: ${response.status}`);
  }
  return response.json();
}
