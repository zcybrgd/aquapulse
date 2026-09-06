from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AquaPulse API"
    app_env: str = "development"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    database_url: str = Field(
        default="postgresql+psycopg://aquapulse:aquapulse@127.0.0.1:5432/aquapulse",
        description="SQLAlchemy URL. Development default matches docker-compose.yml.",
    )
    sql_echo: bool = False
    telemetry_simulator_enabled: bool = False
    telemetry_simulator_interval_seconds: float = 5
    telemetry_simulator_speed: float = 1

    agent_integration_enabled: bool = False
    investigation_agent_enabled: bool = False
    investigation_agent_mode: str = "disabled"
    investigation_agent_url: str = ""
    investigation_agent_timeout_seconds: float = 30
    investigation_agent_contract_version: str = "1.0"
    investigation_agent_investigate_path: str = "/v1/investigate"
    response_agent_enabled: bool = False
    response_agent_mode: str = "disabled"
    response_agent_url: str = ""
    response_agent_timeout_seconds: float = 30
    response_agent_contract_version: str = "1.0"
    response_agent_recommend_path: str = "/v1/recommend-response"
    agent_result_ingest_enabled: bool = False
    agent_support_services_mode: str = "mock"
    physical_commands_enabled: bool = False
    real_notifications_enabled: bool = False
    camara_enabled: bool = False
    agent_http_max_retries: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def database_url_must_be_set(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "DATABASE_URL is empty. Copy backend/.env.example to backend/.env "
                "and start PostgreSQL with docker compose up -d."
            )
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
