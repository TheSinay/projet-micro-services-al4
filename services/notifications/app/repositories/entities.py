"""Domain entities persisted by the repositories."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RecipientType(StrEnum):
    """Who a notification is addressed to."""

    CLIENT = "client"
    RESTAURANT = "restaurant"
    COURIER = "courier"


class Channel(StrEnum):
    """Simulated delivery channel of a notification."""

    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


@dataclass
class Notification:
    """A simulated notification, kept for the demo and the frontend.

    ``correlation_id`` is propagated from the event envelope so a notification
    can be traced back to the originating HTTP request across services.
    """

    id: str
    recipient_type: RecipientType
    recipient_id: str
    channel: Channel
    subject: str
    body: str
    event: str
    correlation_id: str | None
    created_at: datetime
