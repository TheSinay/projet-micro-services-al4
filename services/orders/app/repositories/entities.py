"""Domain entities persisted by the stores.

Monetary amounts are ``float`` for the prototype; every computed amount is
systematically rounded with ``round(x, 2)`` (see ``app.services.pricing``).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class OrderStatus(StrEnum):
    """Lifecycle of an order (strict state machine, see ``OrderService.transition``)."""

    RECEIVED = "RECEIVED"
    PREPARING = "PREPARING"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


@dataclass
class ItemOption:
    """A chosen option on a cart/order item (e.g. extra cheese, +0.50)."""

    name: str
    price_delta: float


@dataclass
class CartItem:
    """A cart line: menu item snapshot with quantity and chosen options."""

    menu_item_id: str
    name: str
    unit_price: float
    quantity: int
    options: list[ItemOption] = field(default_factory=list)


@dataclass
class Cart:
    """The (single-restaurant) cart of a user.

    ``restaurant_lat``/``restaurant_lng`` are optional restaurant coordinates used
    for the delivery fee; they may also be provided at checkout time instead.
    """

    user_id: str
    restaurant_id: str | None = None
    items: list[CartItem] = field(default_factory=list)
    restaurant_lat: float | None = None
    restaurant_lng: float | None = None


@dataclass
class DeliveryAddress:
    """Where the order must be delivered (coordinates are required for the fee)."""

    lat: float
    lng: float
    label: str | None = None
    street: str | None = None
    city: str | None = None


@dataclass
class Order:
    """An order: immutable snapshot of the cart with frozen prices.

    ``payment_id``/``delivery_id`` stay ``None`` and ``saga_state`` stays ``"PENDING"``
    until the saga orchestrator (T09) drives the checkout across services.
    """

    id: str
    user_id: str
    restaurant_id: str
    items: list[CartItem]
    delivery_address: DeliveryAddress
    subtotal: float
    delivery_fee: float
    total: float
    status: OrderStatus
    saga_state: str
    created_at: datetime
    updated_at: datetime
    payment_id: str | None = None
    delivery_id: str | None = None
