"""Application configuration, loaded from environment variables per environment.

Settings are validated with pydantic-settings and cached, so the environment is
read once. See `.env.example` for the full list of variables.
"""

from enum import StrEnum
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Typed application settings sourced from the environment / `.env` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App / environment
    app_name: str = "BarriApp"
    environment: Environment = Environment.LOCAL
    debug: bool = False

    # API
    api_v1_prefix: str = "/api/v1"
    # Parsed from a comma-separated env value (e.g. "http://a,http://b").
    cors_origins: Annotated[list[str], NoDecode] = []

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            return value
        return []

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "barriapp"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth / JWT
    jwt_secret_key: str = "change-me-in-a-real-environment"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Commerce
    default_commission_rate: float = 0.10  # platform commission when a store has no override
    premium_commission_rate: float = 0.05  # reduced rate for Premium-subscribed stores
    subscription_price: int = 30000  # COP / month for the seller Premium plan

    # Payments (Wompi)
    wompi_public_key: str = "pub_test_change_me"
    wompi_events_secret: str = "change-me-wompi-events-secret"
    payment_currency: str = "COP"

    # Rate limiting (Redis fixed-window, per client IP)
    login_rate_limit: int = 10
    login_rate_window: int = 300  # seconds
    ai_chat_rate_limit: int = 30
    ai_chat_rate_window: int = 60  # seconds

    # AI assistant (phase 2)
    anthropic_api_key: str | None = None  # when unset, a deterministic fallback LLM is used
    ai_model: str = "claude-sonnet-4-6"
    ai_top_k: int = 3  # retrieved knowledge chunks per query

    # Observability
    sentry_dsn: str | None = None

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
