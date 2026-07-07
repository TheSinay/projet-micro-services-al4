"""Schemas for payments and refunds."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.repositories.entities import PaymentStatus


class PaymentCreate(BaseModel):
    """Payload for ``POST /api/v1/payments`` (amount must be strictly positive)."""

    order_id: str = Field(min_length=1, max_length=64)
    amount: float = Field(gt=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)


class RefundCreate(BaseModel):
    """Payload for ``POST /api/v1/payments/{id}/refunds``.

    ``amount`` omitted -> total refund of the remaining refundable amount.
    """

    amount: float | None = Field(default=None, gt=0)
    reason: str = Field(min_length=1, max_length=200)


class RefundRead(BaseModel):
    """Public representation of a refund."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    amount: float
    reason: str
    created_at: datetime


class PaymentRead(BaseModel):
    """Public representation of a payment (refunds included)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    order_id: str
    amount: float
    currency: str
    status: PaymentStatus
    refunds: list[RefundRead]
    refunded_amount: float
    created_at: datetime
