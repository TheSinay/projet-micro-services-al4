"""Schemas for kitchen tickets (restaurant-side order lifecycle)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.repositories.entities import TicketStatus


class TicketItemSchema(BaseModel):
    """A line of a kitchen ticket."""

    model_config = ConfigDict(from_attributes=True)

    menu_item_id: str
    quantity: int = Field(ge=1)


class KitchenTicketCreate(BaseModel):
    """Payload for ``POST /api/v1/restaurants/{id}/kitchen-tickets``."""

    order_id: str = Field(min_length=1)
    items: list[TicketItemSchema] = Field(min_length=1)


class KitchenTicketStatusUpdate(BaseModel):
    """Payload for ``PATCH /api/v1/kitchen-tickets/{id}``."""

    status: TicketStatus


class KitchenTicketRead(BaseModel):
    """Public representation of a kitchen ticket."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    order_id: str
    restaurant_id: str
    status: TicketStatus
    items: list[TicketItemSchema]
    created_at: datetime
