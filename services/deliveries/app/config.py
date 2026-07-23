"""Application configuration via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, overridable through environment variables (prefix ``DELIVERIES_``)."""

    model_config = SettingsConfigDict(env_prefix="DELIVERIES_", env_file=".env", extra="ignore")

    service_name: str = "deliveries"
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    # "redis" publishes events over Redis pub/sub; "memory" records them in-process (tests).
    event_backend: Literal["redis", "memory"] = "redis"
    # Seed three demo couriers at startup (disabled in tests).
    seed_data: bool = True


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
