"""Schemas for delivery assignment and tracking."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.repositories.entities import DeliveryStatus


class DeliveryAddress(BaseModel):
    """A pickup or dropoff point (optional human-readable label)."""

    model_config = ConfigDict(from_attributes=True)

    label: str | None = Field(default=None, max_length=200)
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)


class DeliveryCreate(BaseModel):
    """Payload for ``POST /api/v1/deliveries`` (sent by the orders service)."""

    order_id: str = Field(min_length=1, max_length=64)
    # Client owning the order: forwarded so ``delivery.*`` events can target the client
    # in the notifications service. Optional for backward compatibility with older callers.
    user_id: str | None = Field(default=None, max_length=64)
    pickup_address: DeliveryAddress
    dropoff_address: DeliveryAddress


class DeliveryStatusUpdate(BaseModel):
    """Payload for ``PATCH /api/v1/deliveries/{id}``."""

    status: DeliveryStatus


class DeliveryEventRead(BaseModel):
    """A timestamped status change (audit trail)."""

    model_config = ConfigDict(from_attributes=True)

    status: DeliveryStatus
    at: datetime


class DeliveryRead(BaseModel):
    """Public representation of a delivery."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    order_id: str
    courier_id: str
    status: DeliveryStatus
    pickup_address: DeliveryAddress
    dropoff_address: DeliveryAddress
    events: list[DeliveryEventRead]
    created_at: datetime
