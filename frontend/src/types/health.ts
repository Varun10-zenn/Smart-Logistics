export interface DatabaseHealth {
  status: 'connected' | 'connected_fallback' | 'disconnected' | string;
  database_type: string;
  url?: string;
  latency_ms?: number;
  error?: string;
}

export interface HealthCheck {
  status: 'healthy' | 'degraded' | string;
  environment: string;
  version: string;
  database: DatabaseHealth;
}
