"""Application configuration via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, overridable through env variables (prefix ``RESTAURANTS_``)."""

    model_config = SettingsConfigDict(env_prefix="RESTAURANTS_", env_file=".env", extra="ignore")

    service_name: str = "restaurants"
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    # "redis" publishes domain events on Redis pub/sub (production / docker-compose);
    # "memory" records them in-process (default, keeps the test suite hermetic).
    event_bus: Literal["memory", "redis"] = "memory"
    # Populate the catalogue with demo restaurants at startup (disabled in tests).
    seed_data: bool = True


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
