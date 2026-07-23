"""Schemas for menu items (dishes) and their options."""

from pydantic import BaseModel, ConfigDict, Field


class MenuItemOptionSchema(BaseModel):
    """An option on a dish (e.g. extra topping) with its price delta."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(min_length=1, max_length=100)
    price_delta: float = Field(ge=0.0, le=1000.0)


class MenuItemBase(BaseModel):
    """Fields shared by create/update payloads and responses."""

    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    price: float = Field(gt=0.0, le=10000.0)
    options: list[MenuItemOptionSchema] = Field(default_factory=list)
    available: bool = True


class MenuItemCreate(MenuItemBase):
    """Payload for ``POST /api/v1/restaurants/{id}/menu-items``."""


class MenuItemUpdate(MenuItemBase):
    """Payload for ``PUT .../menu-items/{itemId}`` (full replacement, availability included)."""


class MenuItemRead(MenuItemBase):
    """Public representation of a menu item."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    restaurant_id: str
