"""Schemas for order validation (called by the orders SAGA orchestrator)."""

from datetime import datetime

from pydantic import BaseModel, Field


class OrderValidationItem(BaseModel):
    """A line of the order to validate against the catalogue."""

    menu_item_id: str
    unit_price: float = Field(ge=0.0)
    quantity: int = Field(ge=1)


class OrderValidationRequest(BaseModel):
    """Payload for ``POST /api/v1/restaurants/{id}/order-validations``."""

    items: list[OrderValidationItem] = Field(min_length=1)
    # Validation instant (defaults to "now"); lets the saga replay a deterministic time.
    at: datetime | None = None


class OrderValidationResponse(BaseModel):
    """Verdict returned with HTTP 200 in both cases (see README: simpler for the orchestrator)."""

    valid: bool
    subtotal: float | None = None
    reasons: list[str] = Field(default_factory=list)
