"""Abstract repository interfaces (structural typing via Protocol).

Business logic depends only on these contracts, so the in-memory implementation
can later be swapped for a real database without touching the services.
"""

from typing import Protocol

from app.repositories.entities import Payment


class PaymentRepository(Protocol):
    """Persistence contract for payments."""

    def add(self, payment: Payment) -> None: ...

    def get_by_id(self, payment_id: str) -> Payment | None: ...

    def list_by_order(self, order_id: str) -> list[Payment]: ...

    def list_all(self) -> list[Payment]: ...

    def update(self, payment: Payment) -> None: ...
