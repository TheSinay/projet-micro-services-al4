"""Payment use cases: charge (idempotent per order), refunds, lookups."""

import uuid
from datetime import UTC, datetime

from app.logging import logger
from app.repositories.entities import Payment, PaymentStatus, Refund
from app.repositories.interfaces import PaymentRepository
from app.schemas.payments import PaymentCreate, RefundCreate
from app.services.exceptions import (
    PaymentNotFoundError,
    PspUnavailableError,
    RefundExceedsCapturedError,
    RefundNotAllowedError,
)
from app.services.psp import PspGateway

# Statuses meaning "the order has already been charged" (idempotency barrier).
_ACTIVE_CAPTURE_STATUSES = frozenset({PaymentStatus.CAPTURED, PaymentStatus.PARTIALLY_REFUNDED})
# Statuses from which a refund is allowed.
_REFUNDABLE_STATUSES = frozenset({PaymentStatus.CAPTURED, PaymentStatus.PARTIALLY_REFUNDED})


class PaymentService:
    """Business logic for payments and refunds."""

    def __init__(self, payments: PaymentRepository, psp: PspGateway) -> None:
        self._payments = payments
        self._psp = psp

    def create_payment(self, data: PaymentCreate) -> tuple[Payment, bool]:
        """Charge an order; returns ``(payment, created)``.

        Idempotency per ``order_id``: if a payment with money still captured
        already exists for the order (CAPTURED or PARTIALLY_REFUNDED), it is
        returned as-is (``created=False``) — never a double debit. FAILED
        attempts do not block a retry with the same ``order_id``.

        If the simulated PSP rejects the charge, the attempt is recorded as
        FAILED (audit trail) and ``PspUnavailableError`` (502) is raised.
        On success the payment goes straight AUTHORIZED -> CAPTURED (instant
        capture simulated for the prototype).
        """
        existing = next(
            (
                payment
                for payment in self._payments.list_by_order(data.order_id)
                if payment.status in _ACTIVE_CAPTURE_STATUSES
            ),
            None,
        )
        if existing is not None:
            logger.info("payment_replayed", order_id=data.order_id, payment_id=existing.id)
            return existing, False

        payment = Payment(
            id=uuid.uuid4().hex,
            order_id=data.order_id,
            amount=round(data.amount, 2),
            currency=data.currency,
            status=PaymentStatus.AUTHORIZED,
            created_at=datetime.now(UTC),
        )
        if not self._psp.charge(data.order_id, payment.amount, payment.currency):
            payment.status = PaymentStatus.FAILED
            self._payments.add(payment)
            logger.warning("payment_failed", order_id=data.order_id, payment_id=payment.id)
            raise PspUnavailableError()

        # Prototype: instant capture (AUTHORIZED is transient, see PaymentStatus docstring).
        payment.status = PaymentStatus.CAPTURED
        self._payments.add(payment)
        logger.info(
            "payment_captured",
            order_id=data.order_id,
            payment_id=payment.id,
            amount=payment.amount,
        )
        return payment, True

    def refund(self, payment_id: str, data: RefundCreate) -> Payment:
        """Apply a partial or total refund to a captured payment.

        Without an explicit ``amount``, the whole remaining refundable amount
        is refunded. Cumulated refunds can never exceed the captured amount
        (422); refunding a payment that is not CAPTURED / PARTIALLY_REFUNDED
        is a conflict (409).
        """
        payment = self.get_payment(payment_id)
        if payment.status not in _REFUNDABLE_STATUSES:
            raise RefundNotAllowedError()

        remaining = round(payment.amount - payment.refunded_amount, 2)
        requested = round(data.amount, 2) if data.amount is not None else remaining
        if requested > remaining:
            raise RefundExceedsCapturedError()

        payment.refunds.append(
            Refund(
                id=uuid.uuid4().hex,
                amount=requested,
                reason=data.reason,
                created_at=datetime.now(UTC),
            )
        )
        payment.status = (
            PaymentStatus.REFUNDED
            if payment.refunded_amount >= round(payment.amount, 2)
            else PaymentStatus.PARTIALLY_REFUNDED
        )
        self._payments.update(payment)
        logger.info(
            "payment_refunded",
            payment_id=payment.id,
            refund_amount=requested,
            refunded_total=payment.refunded_amount,
            status=payment.status,
        )
        return payment

    def get_payment(self, payment_id: str) -> Payment:
        """Return the payment or raise 404."""
        payment = self._payments.get_by_id(payment_id)
        if payment is None:
            raise PaymentNotFoundError()
        return payment

    def list_payments(self, order_id: str | None = None) -> list[Payment]:
        """List payments, optionally filtered by ``order_id`` (all attempts, FAILED included)."""
        if order_id is not None:
            return self._payments.list_by_order(order_id)
        return self._payments.list_all()
