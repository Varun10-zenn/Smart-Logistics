from typing import Optional
from pydantic import BaseModel, Field


class DatabaseHealthResponse(BaseModel):
    status: str = Field(..., description="Status of DB connection: connected, connected_fallback, or disconnected")
    database_type: str = Field(..., description="Dialect name: mysql, sqlite, etc.")
    url: Optional[str] = Field(None, description="Masked DB connection endpoint")
    latency_ms: Optional[float] = Field(None, description="Connection latency in milliseconds")
    error: Optional[str] = Field(None, description="Error message if disconnected")


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Application status", json_schema_extra={"example": "healthy"})
    environment: str = Field(..., description="Environment name", json_schema_extra={"example": "development"})
    version: str = Field(..., description="API Version", json_schema_extra={"example": "1.0.0"})
    database: DatabaseHealthResponse
