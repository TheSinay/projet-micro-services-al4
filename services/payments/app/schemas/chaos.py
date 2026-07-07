"""Schemas for the chaos endpoint (dev/demo only)."""

from pydantic import BaseModel, Field


class ChaosUpdate(BaseModel):
    """Payload for ``POST /api/v1/_chaos``: new PSP failure probability."""

    failure_rate: float = Field(ge=0.0, le=1.0)


class ChaosRead(BaseModel):
    """Currently applied failure rate."""

    failure_rate: float
