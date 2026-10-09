import os
from typing import List, Union, Optional
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Smart Logistics Platform"
    APP_ENV: str = "prod"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Temporary Development Bypass Flag (Disabled by default, requires APP_ENV="local")
    DEV_AUTH_BYPASS: bool = False

    # Service Configuration
    SERVICE_RADIUS_KM: float = 10.0

    # Database Settings (MySQL 8.0)
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/smart_logistics"
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "password"
    MYSQL_DB: str = "smart_logistics"
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306

    # JWT Settings
    JWT_SECRET: str = "supersecret_jwt_key_change_in_production_32bytes_min"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Provider Settings
    LLM_PROVIDER: str = "mock"
    LLM_API_KEY: str = ""
    MAP_PROVIDER: str = "mock"
    WEATHER_PROVIDER: str = "mock"
    TRAFFIC_PROVIDER: str = "mock"

    # Auto-Batching Configuration
    AUTO_BATCH_ENABLED: bool = True
    AUTO_BATCH_INTERVAL_SECONDS: int = 30
    AUTO_BATCH_MIN_ORDERS: int = 1
    AUTO_BATCH_MAX_WAIT_SECONDS: int = 120
    AUTO_BATCH_MAX_ORDERS: int = 5
    AUTO_BATCH_MAX_WEIGHT_KG: float = 50.0
    AUTO_BATCH_MAX_VOLUME_CBM: float = 2.0

    # Safety & Telemetry Configuration
    SAFETY_ALERT_SCORE: float = 70.0

    # Simulator Configuration (Default True when APP_ENV is "local" or "staging"; False in prod)
    SIMULATOR_ENABLED: Optional[bool] = None
    SIM_INTERVAL_SECONDS: int = 2
    SIM_SPEED_MULTIPLIER: float = 10.0
    EV_CONSUMPTION_KWH_PER_KM: float = 0.12

    # Charging Configuration
    CHARGING_SLOT_HORIZON_HOURS: int = 24
    LOW_SOC_THRESHOLD: float = 25.0

    # Time-of-Day Traffic Factors for ETA
    PEAK_HOURS_AM: tuple = (8, 10)
    PEAK_HOURS_PM: tuple = (17, 20)
    PEAK_TRAFFIC_FACTOR: float = 1.4
    OFF_PEAK_TRAFFIC_FACTOR: float = 1.1

    @property
    def is_simulator_enabled(self) -> bool:
        if self.SIMULATOR_ENABLED is not None:
            return self.SIMULATOR_ENABLED
        return self.APP_ENV.lower() in ("local", "staging")

    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS Settings
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            import json
            try:
                return json.loads(v)
            except Exception:
                return ["http://localhost:3000", "http://localhost:5173"]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
