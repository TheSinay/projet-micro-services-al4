"""In-memory implementations — stand-ins for a real database (ADR 0005).

Instances are created per application in ``create_app`` (stored on ``app.state``),
never as module-level globals, so every test starts from a clean state.
"""

from app.repositories.entities import Courier, Delivery


class InMemoryCourierRepository:
    """Dict-backed courier store."""

    def __init__(self) -> None:
        self._couriers: dict[str, Courier] = {}

    def add(self, courier: Courier) -> None:
        self._couriers[courier.id] = courier

    def get_by_id(self, courier_id: str) -> Courier | None:
        return self._couriers.get(courier_id)

    def list_all(self) -> list[Courier]:
        return list(self._couriers.values())

    def update(self, courier: Courier) -> None:
        self._couriers[courier.id] = courier


class InMemoryDeliveryRepository:
    """Dict-backed delivery store."""

    def __init__(self) -> None:
        self._deliveries: dict[str, Delivery] = {}

    def add(self, delivery: Delivery) -> None:
        self._deliveries[delivery.id] = delivery

    def get_by_id(self, delivery_id: str) -> Delivery | None:
        return self._deliveries.get(delivery_id)

    def list_by_order(self, order_id: str) -> list[Delivery]:
        return [d for d in self._deliveries.values() if d.order_id == order_id]

    def list_all(self) -> list[Delivery]:
        return list(self._deliveries.values())

    def update(self, delivery: Delivery) -> None:
        self._deliveries[delivery.id] = delivery
