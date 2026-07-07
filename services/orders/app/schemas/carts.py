"""Schemas for the cart endpoints."""

from pydantic import BaseModel, ConfigDict, Field


class ItemOptionPayload(BaseModel):
    """A chosen option on a menu item (``price_delta`` may be negative, e.g. 'no sauce')."""

    name: str = Field(min_length=1, max_length=100)
    price_delta: float = 0.0


class CartItemAdd(BaseModel):
    """Payload for ``POST /api/v1/carts/{user_id}/items``.

    ``restaurant_lat``/``restaurant_lng`` optionally record the restaurant position on
    the cart, so the delivery fee can be distance-based at checkout time.
    """

    restaurant_id: str = Field(min_length=1)
    menu_item_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=200)
    unit_price: float = Field(ge=0.0)
    quantity: int = Field(ge=1)
    options: list[ItemOptionPayload] = Field(default_factory=list)
    restaurant_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    restaurant_lng: float | None = Field(default=None, ge=-180.0, le=180.0)


class ItemOptionRead(BaseModel):
    """Public representation of a chosen option."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    price_delta: float


class CartItemRead(BaseModel):
    """Public representation of a cart line."""

    model_config = ConfigDict(from_attributes=True)

    menu_item_id: str
    name: str
    unit_price: float
    quantity: int
    options: list[ItemOptionRead]


class CartRead(BaseModel):
    """Public representation of a user's cart."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    restaurant_id: str | None
    items: list[CartItemRead]
    restaurant_lat: float | None
    restaurant_lng: float | None
