"""Domain entities persisted by the repositories."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class DeliveryStatus(StrEnum):
    """Lifecycle of a delivery; transitions are enforced by the delivery service."""

    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    PICKED_UP = "PICKED_UP"
    DELIVERED = "DELIVERED"


@dataclass
class Location:
    """Simulated GPS position of a courier."""

    lat: float
    lng: float


@dataclass
class Courier:
    """A delivery person; ``available`` gates the assignment algorithm."""

    id: str
    name: str
    phone: str
    available: bool
    location: Location


@dataclass
class GeoAddress:
    """A pickup or dropoff point (optional human-readable label)."""

    lat: float
    lng: float
    label: str | None = None


@dataclass
class DeliveryEvent:
    """A timestamped status change, kept as the delivery audit trail."""

    status: DeliveryStatus
    at: datetime


@dataclass
class Delivery:
    """A delivery assignment linking an order to a courier."""

    id: str
    order_id: str
    courier_id: str
    status: DeliveryStatus
    pickup_address: GeoAddress
    dropoff_address: GeoAddress
    created_at: datetime
    events: list[DeliveryEvent] = field(default_factory=list)
