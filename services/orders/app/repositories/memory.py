"""In-memory implementations — stand-ins for Redis / a real database (ADR 0005).

Instances are created per application in ``create_app`` (stored on ``app.state``),
never as module-level globals, so every test starts from a clean state.
"""

from app.repositories.entities import Cart, Order


class InMemoryCartStore:
    """Dict-backed cart store (default backend; production uses ``RedisCartStore``)."""

    def __init__(self) -> None:
        self._carts: dict[str, Cart] = {}

    def get(self, user_id: str) -> Cart | None:
        return self._carts.get(user_id)

    def save(self, cart: Cart) -> None:
        self._carts[cart.user_id] = cart

    def clear(self, user_id: str) -> None:
        self._carts.pop(user_id, None)


class InMemoryOrderRepository:
    """Dict-backed order store (insertion-ordered, which ``dict`` guarantees)."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def add(self, order: Order) -> None:
        self._orders[order.id] = order

    def get_by_id(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def list_by_user(self, user_id: str) -> list[Order]:
        return [order for order in self._orders.values() if order.user_id == user_id]

    def update(self, order: Order) -> None:
        self._orders[order.id] = order
