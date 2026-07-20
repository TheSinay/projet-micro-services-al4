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
    # Downstream services called by the saga orchestrator (T09).
    restaurants_url: str = "http://localhost:8002"
    payments_url: str = "http://localhost:8004"
    deliveries_url: str = "http://localhost:8005"
    # Resilience (ADR 0007): timeout on every outgoing call, retry x3 with
    # exponential backoff + jitter, circuit breaker on the payment call.
    http_timeout: float = Field(default=2.0, gt=0.0)
    retry_attempts: int = Field(default=3, ge=1)
    retry_base_delay: float = Field(default=0.1, ge=0.0)
    breaker_failure_threshold: int = Field(default=5, ge=1)
    breaker_window_seconds: float = Field(default=30.0, gt=0.0)
    breaker_recovery_timeout: float = Field(default=15.0, gt=0.0)
    # Continuation (T12): deferred retries when no courier is available.
    delivery_assign_attempts: int = Field(default=3, ge=1)
    delivery_assign_retry_delay: float = Field(default=2.0, ge=0.0)


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
