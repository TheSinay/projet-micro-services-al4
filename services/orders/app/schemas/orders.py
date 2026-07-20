"""Schemas for the order endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.repositories.entities import OrderStatus
from app.schemas.carts import CartItemRead


class DeliveryAddressPayload(BaseModel):
    """Delivery address: coordinates are required (used for the distance-based fee)."""

    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)
    label: str | None = Field(default=None, max_length=50)
    street: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=100)


class OrderCreate(BaseModel):
    """Payload for ``POST /api/v1/orders`` — the order is built from the user's cart.

    Restaurant coordinates are optional: when omitted, the ones recorded on the cart
    are used; when unknown everywhere, the delivery fee falls back to the flat base fee.
    """

    user_id: str = Field(min_length=1)
    delivery_address: DeliveryAddressPayload
    restaurant_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    restaurant_lng: float | None = Field(default=None, ge=-180.0, le=180.0)


class DeliveryAddressRead(BaseModel):
    """Public representation of the delivery address."""

    model_config = ConfigDict(from_attributes=True)

    lat: float
    lng: float
    label: str | None
    street: str | None
    city: str | None


class OrderRead(BaseModel):
    """Public representation of an order (prices are frozen at checkout time)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    restaurant_id: str
    items: list[CartItemRead]
    delivery_address: DeliveryAddressRead
    subtotal: float
    delivery_fee: float
    total: float
    status: OrderStatus
    saga_state: str
    payment_id: str | None
    delivery_id: str | None
    # Human-readable reason when the saga cancelled the order (checkout stays 201,
    # the client discovers the failure by consulting the returned/fetched order).
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime


class OrderStatusUpdate(BaseModel):
    """Payload for ``PATCH /api/v1/orders/{order_id}/status``."""

    status: OrderStatus
