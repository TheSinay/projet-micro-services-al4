"""Schemas for restaurant profiles (opening hours included)."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.menu_items import MenuItemRead

TIME_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"


class OpeningHourSchema(BaseModel):
    """A weekly opening slot; ``day`` uses 0 = Monday … 6 = Sunday."""

    model_config = ConfigDict(from_attributes=True)

    day: int = Field(ge=0, le=6)
    open: str = Field(pattern=TIME_PATTERN)
    close: str = Field(pattern=TIME_PATTERN)

    @model_validator(mode="after")
    def check_open_before_close(self) -> "OpeningHourSchema":
        if self.open >= self.close:
            raise ValueError("open must be strictly before close")
        return self


class RestaurantBase(BaseModel):
    """Fields shared by create/update payloads and responses."""

    name: str = Field(min_length=1, max_length=100)
    cuisine_type: str = Field(min_length=1, max_length=50)
    address: str = Field(min_length=1, max_length=200)
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)
    opening_hours: list[OpeningHourSchema] = Field(default_factory=list)
    auto_accept: bool = True
    owner_id: str | None = Field(default=None, max_length=100)


class RestaurantCreate(RestaurantBase):
    """Payload for ``POST /api/v1/restaurants``."""


class RestaurantUpdate(RestaurantBase):
    """Payload for ``PUT /api/v1/restaurants/{id}`` (full replacement, hours included)."""


class RestaurantRead(RestaurantBase):
    """Public representation of a restaurant (without its menu)."""

    model_config = ConfigDict(from_attributes=True)

    id: str


class RestaurantDetail(RestaurantRead):
    """Restaurant profile with its detailed menu (``GET /api/v1/restaurants/{id}``)."""

    menu: list[MenuItemRead]
