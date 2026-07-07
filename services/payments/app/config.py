"""Application configuration via pydantic-settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, overridable through environment variables (prefix ``PAYMENTS_``)."""

    model_config = SettingsConfigDict(env_prefix="PAYMENTS_", env_file=".env", extra="ignore")

    service_name: str = "payments"
    log_level: str = "INFO"
    # Probability that the simulated PSP rejects a charge (chaos engineering knob).
    # Also tunable at runtime through ``POST /api/v1/_chaos`` (dev/demo only).
    failure_rate: float = Field(default=0.0, ge=0.0, le=1.0)


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
