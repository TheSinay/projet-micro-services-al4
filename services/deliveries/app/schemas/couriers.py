"""Schemas for courier management."""

from pydantic import BaseModel, ConfigDict, Field


class LocationSchema(BaseModel):
    """Simulated GPS position."""

    model_config = ConfigDict(from_attributes=True)

    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)


class CourierCreate(BaseModel):
    """Payload for ``POST /api/v1/couriers``."""

    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=30)
    available: bool = True
    location: LocationSchema


class CourierUpdate(BaseModel):
    """Payload for ``PATCH /api/v1/couriers/{id}`` (availability and/or simulated location)."""

    available: bool | None = None
    location: LocationSchema | None = None


class CourierRead(BaseModel):
    """Public representation of a courier."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    phone: str
    available: bool
    location: LocationSchema
