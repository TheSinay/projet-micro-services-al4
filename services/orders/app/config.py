"""Application configuration via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, overridable through environment variables (prefix ``ORDERS_``)."""

    model_config = SettingsConfigDict(env_prefix="ORDERS_", env_file=".env", extra="ignore")

    service_name: str = "orders"
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    # Backend selection: "memory" (default — tests and standalone runs) or "redis" (production,
    # required for a stateless, horizontally scalable service).
    cart_store_backend: Literal["memory", "redis"] = "memory"
    event_bus_backend: Literal["memory", "redis"] = "memory"
    # Pricing knobs: delivery_fee = base + per_km * haversine_km(restaurant, delivery address).
    base_delivery_fee: float = Field(default=2.50, ge=0.0)
    delivery_fee_per_km: float = Field(default=0.50, ge=0.0)


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
