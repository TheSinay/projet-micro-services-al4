"""Domain entities persisted by the repositories."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


@dataclass
class OpeningHour:
    """A weekly opening slot. ``day`` follows Python's convention: 0 = Monday … 6 = Sunday."""

    day: int
    open: str  # "HH:MM"
    close: str  # "HH:MM"


@dataclass
class Restaurant:
    """A restaurant profile, including its weekly opening hours."""

    id: str
    name: str
    cuisine_type: str
    address: str
    lat: float
    lng: float
    opening_hours: list[OpeningHour] = field(default_factory=list)
    # When False, incoming kitchen tickets are refused (SAGA compensation demo).
    auto_accept: bool = True


@dataclass
class MenuItemOption:
    """An option on a dish (e.g. extra topping) with its price delta."""

    name: str
    price_delta: float


@dataclass
class MenuItem:
    """A dish on a restaurant menu. Prices are floats rounded to 2 decimals."""

    id: str
    restaurant_id: str
    name: str
    description: str
    price: float
    options: list[MenuItemOption] = field(default_factory=list)
    available: bool = True


class TicketStatus(StrEnum):
    """Kitchen ticket lifecycle. Valid transitions: ACCEPTED -> PREPARING -> READY."""

    ACCEPTED = "ACCEPTED"
    REFUSED = "REFUSED"
    PREPARING = "PREPARING"
    READY = "READY"


@dataclass
class TicketItem:
    """A line of a kitchen ticket."""

    menu_item_id: str
    quantity: int


@dataclass
class KitchenTicket:
    """The restaurant-side view of an order being prepared."""

    id: str
    order_id: str
    restaurant_id: str
    status: TicketStatus
    items: list[TicketItem]
    created_at: datetime
