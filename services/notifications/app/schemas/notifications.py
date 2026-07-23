"""Schemas for the notifications read API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.repositories.entities import Channel, RecipientType


class NotificationRead(BaseModel):
    """Public representation of a stored (simulated) notification."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    recipient_type: RecipientType
    recipient_id: str
    channel: Channel
    subject: str
    body: str
    event: str
    correlation_id: str | None
    created_at: datetime
