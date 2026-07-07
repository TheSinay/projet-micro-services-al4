"""Abstract store interfaces (structural typing via Protocol).

Business logic depends only on these contracts, so the in-memory implementations
(tests, default) can be swapped for the Redis-backed ones (production) through
configuration without touching the services.
"""

from typing import Protocol

from app.repositories.entities import Cart, Order


class CartStore(Protocol):
    """Persistence contract for carts (one cart per user)."""

    def get(self, user_id: str) -> Cart | None: ...

    def save(self, cart: Cart) -> None: ...

    def clear(self, user_id: str) -> None: ...


class OrderRepository(Protocol):
    """Persistence contract for orders."""

    def add(self, order: Order) -> None: ...

    def get_by_id(self, order_id: str) -> Order | None: ...

    def list_by_user(self, user_id: str) -> list[Order]: ...

    def update(self, order: Order) -> None: ...
