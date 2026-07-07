"""In-memory implementations — stand-ins for a real database (ADR 0005).

Instances are created per application in ``create_app`` (stored on ``app.state``),
never as module-level globals, so every test starts from a clean state.
"""

from app.repositories.entities import Payment


class InMemoryPaymentRepository:
    """Dict-backed payment store (insertion order preserved)."""

    def __init__(self) -> None:
        self._payments: dict[str, Payment] = {}

    def add(self, payment: Payment) -> None:
        self._payments[payment.id] = payment

    def get_by_id(self, payment_id: str) -> Payment | None:
        return self._payments.get(payment_id)

    def list_by_order(self, order_id: str) -> list[Payment]:
        return [payment for payment in self._payments.values() if payment.order_id == order_id]

    def list_all(self) -> list[Payment]:
        return list(self._payments.values())

    def update(self, payment: Payment) -> None:
        self._payments[payment.id] = payment
