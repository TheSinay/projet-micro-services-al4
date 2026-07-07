"""Domain entities persisted by the repositories."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class PaymentStatus(StrEnum):
    """Lifecycle of a payment.

    Prototype note: an accepted charge goes straight AUTHORIZED -> CAPTURED
    (instant capture simulated by the fake PSP), so AUTHORIZED is transient
    and never persisted between requests.
    """

    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"


@dataclass
class Refund:
    """A (partial or total) refund applied to a captured payment."""

    id: str
    amount: float
    reason: str
    created_at: datetime


@dataclass
class Payment:
    """A payment attempt for an order. Amounts are expressed in ``currency`` (EUR)."""

    id: str
    order_id: str
    amount: float
    currency: str
    status: PaymentStatus
    created_at: datetime
    refunds: list[Refund] = field(default_factory=list)

    @property
    def refunded_amount(self) -> float:
        """Total already refunded, rounded to cents."""
        return round(sum(refund.amount for refund in self.refunds), 2)
