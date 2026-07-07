"""Abstract repository interfaces (structural typing via Protocol).

Business logic depends only on these contracts, so the in-memory implementations
can later be swapped for a real database / Redis without touching the services.
"""

from typing import Protocol

from app.repositories.entities import KitchenTicket, MenuItem, Restaurant


class RestaurantRepository(Protocol):
    """Persistence contract for restaurants."""

    def add(self, restaurant: Restaurant) -> None: ...

    def get_by_id(self, restaurant_id: str) -> Restaurant | None: ...

    def list_all(self) -> list[Restaurant]: ...

    def update(self, restaurant: Restaurant) -> None: ...


class MenuItemRepository(Protocol):
    """Persistence contract for menu items."""

    def add(self, item: MenuItem) -> None: ...

    def get_by_id(self, item_id: str) -> MenuItem | None: ...

    def list_by_restaurant(self, restaurant_id: str) -> list[MenuItem]: ...

    def update(self, item: MenuItem) -> None: ...

    def delete(self, item_id: str) -> None: ...


class KitchenTicketRepository(Protocol):
    """Persistence contract for kitchen tickets."""

    def add(self, ticket: KitchenTicket) -> None: ...

    def get_by_id(self, ticket_id: str) -> KitchenTicket | None: ...

    def update(self, ticket: KitchenTicket) -> None: ...
