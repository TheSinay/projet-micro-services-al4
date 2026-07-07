"""Application configuration via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, overridable through env variables (prefix ``NOTIFICATIONS_``)."""

    model_config = SettingsConfigDict(env_prefix="NOTIFICATIONS_", env_file=".env", extra="ignore")

    service_name: str = "notifications"
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    # "redis" starts the pub/sub consumer loop in the lifespan; "memory" (default, used by
    # the tests) starts nothing — handlers are then only reachable directly (hermetic tests).
    # The Docker image overrides this to "redis" for production.
    event_backend: Literal["redis", "memory"] = "memory"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
