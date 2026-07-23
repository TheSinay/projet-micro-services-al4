"""Schemas for the user address book."""

from pydantic import BaseModel, ConfigDict, Field


class AddressBase(BaseModel):
    """Fields shared by create/update payloads and responses."""

    label: str = Field(min_length=1, max_length=50)
    street: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)


class AddressCreate(AddressBase):
    """Payload for ``POST /api/v1/users/me/addresses``."""


class AddressUpdate(AddressBase):
    """Payload for ``PUT /api/v1/users/me/addresses/{id}`` (full replacement)."""


class AddressRead(AddressBase):
    """Public representation of an address."""

    model_config = ConfigDict(from_attributes=True)

    id: str
