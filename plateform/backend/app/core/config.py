from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_PROJECT_ROOT = _BACKEND_DIR.parent.parent
_DEFAULT_NOKIA_HOST = "network-as-code.p-eu.rapidapi.com"
_LEGACY_NOKIA_HOSTS = {"network-as-code.nokia.rapidapi.com"}


def _strip_env_quotes(value: object) -> object:
    if not isinstance(value, str):
        return value
    return value.strip().strip('"').strip("'")


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
    investigation_agent_health_path: str = "/health"
    investigation_agent_contract_path: str = "/v1/contract"
    investigation_agent_investigate_path: str = "/v1/investigate"
    network_agent_enabled: bool = False
    network_agent_url: str = ""
    network_agent_health_path: str = "/health"
    network_agent_contract_path: str = "/v1/contract"
    response_agent_enabled: bool = False
    response_agent_mode: str = "disabled"
    response_agent_url: str = ""
    response_agent_timeout_seconds: float = 30
    response_agent_contract_version: str = "1.0"
    response_agent_health_path: str = "/health"
    response_agent_contract_path: str = "/v1/contract"
    response_agent_recommend_path: str = "/v1/recommend-response"
    agent_health_timeout_seconds: float = 2
    agent_health_cache_seconds: int = 15
    seed_agent_demo_data: bool = False
    agent_result_ingest_enabled: bool = True
    agent_support_services_mode: str = "mock"
    physical_commands_enabled: bool = False
    real_notifications_enabled: bool = False
    camara_enabled: bool = False
    agent_http_max_retries: int = 2

    nokia_network_api_enabled: bool = False
    nokia_network_api_mode: str = "mock"
    nokia_network_api_base_url: str = ""
    nokia_network_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("NOKIA_NETWORK_API_KEY", "RAPIDAPI_KEY"),
    )
    nokia_network_api_host: str = Field(
        default="",
        validation_alias=AliasChoices("NOKIA_NETWORK_API_HOST", "RAPIDAPI_HOST"),
    )
    nokia_location_path: str = "/location-retrieval/v0/retrieve"
    nokia_reachability_path: str = "/device-status/device-reachability-status/v1/retrieve"
    nokia_network_timeout_seconds: float = 10
    nokia_network_cache_seconds: int = 300
    nokia_network_max_retries: int = 1
    nokia_network_bulk_limit: int = 20
    nokia_network_concurrency: int = 4

    model_config = SettingsConfigDict(
        env_file=(str(_PROJECT_ROOT / ".env"), str(_BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
        populate_by_name=True,
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

    @field_validator("nokia_network_api_key", "nokia_network_api_host", "nokia_network_api_base_url", mode="before")
    @classmethod
    def strip_nokia_env(cls, value: object) -> object:
        return _strip_env_quotes(value)

    @model_validator(mode="after")
    def default_nokia_base_url(self) -> "Settings":
        host = self.nokia_network_api_host.strip()
        key = self.nokia_network_api_key.strip()
        base = self.nokia_network_api_base_url.strip()
        if key and not host:
            self.nokia_network_api_host = "network-as-code.nokia.rapidapi.com"
            host = self.nokia_network_api_host
        # RapidAPI API ids such as network-as-code.nokia.rapidapi.com are headers, not DNS names.
        if key and (not base or any(legacy in base for legacy in _LEGACY_NOKIA_HOSTS)):
            connect_host = _DEFAULT_NOKIA_HOST if host in _LEGACY_NOKIA_HOSTS or not host else host
            self.nokia_network_api_base_url = f"https://{connect_host}"
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
