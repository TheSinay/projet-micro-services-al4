"""Abstract repository interfaces (structural typing via Protocol).

Business logic depends only on these contracts, so the in-memory implementations
can later be swapped for a real database / Redis without touching the services.
"""

from typing import Protocol

from app.repositories.entities import Courier, Delivery


class CourierRepository(Protocol):
    """Persistence contract for couriers."""

    def add(self, courier: Courier) -> None: ...

    def get_by_id(self, courier_id: str) -> Courier | None: ...

    def list_all(self) -> list[Courier]: ...

    def update(self, courier: Courier) -> None: ...


class DeliveryRepository(Protocol):
    """Persistence contract for deliveries."""

    def add(self, delivery: Delivery) -> None: ...

    def get_by_id(self, delivery_id: str) -> Delivery | None: ...

    def list_by_order(self, order_id: str) -> list[Delivery]: ...

    def list_all(self) -> list[Delivery]: ...

    def update(self, delivery: Delivery) -> None: ...
