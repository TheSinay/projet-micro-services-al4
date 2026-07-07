"""Application configuration via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, overridable through environment variables (prefix ``USERS_``)."""

    model_config = SettingsConfigDict(env_prefix="USERS_", env_file=".env", extra="ignore")

    service_name: str = "users"
    log_level: str = "INFO"
    # In production the opaque token store would live in Redis (see README / ADR 0005).
    redis_url: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
