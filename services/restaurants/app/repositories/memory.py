"""In-memory implementations — stand-ins for a real database (ADR 0005).

Instances are created per application in ``create_app`` (stored on ``app.state``),
never as module-level globals, so every test starts from a clean state.
"""

from app.repositories.entities import KitchenTicket, MenuItem, Restaurant


class InMemoryRestaurantRepository:
    """Dict-backed restaurant store."""

    def __init__(self) -> None:
        self._restaurants: dict[str, Restaurant] = {}

    def add(self, restaurant: Restaurant) -> None:
        self._restaurants[restaurant.id] = restaurant

    def get_by_id(self, restaurant_id: str) -> Restaurant | None:
        return self._restaurants.get(restaurant_id)

    def list_all(self) -> list[Restaurant]:
        return list(self._restaurants.values())

    def update(self, restaurant: Restaurant) -> None:
        self._restaurants[restaurant.id] = restaurant


class InMemoryMenuItemRepository:
    """Dict-backed menu item store."""

    def __init__(self) -> None:
        self._items: dict[str, MenuItem] = {}

    def add(self, item: MenuItem) -> None:
        self._items[item.id] = item

    def get_by_id(self, item_id: str) -> MenuItem | None:
        return self._items.get(item_id)

    def list_by_restaurant(self, restaurant_id: str) -> list[MenuItem]:
        return [item for item in self._items.values() if item.restaurant_id == restaurant_id]

    def update(self, item: MenuItem) -> None:
        self._items[item.id] = item

    def delete(self, item_id: str) -> None:
        self._items.pop(item_id, None)


class InMemoryKitchenTicketRepository:
    """Dict-backed kitchen ticket store."""

    def __init__(self) -> None:
        self._tickets: dict[str, KitchenTicket] = {}

    def add(self, ticket: KitchenTicket) -> None:
        self._tickets[ticket.id] = ticket

    def get_by_id(self, ticket_id: str) -> KitchenTicket | None:
        return self._tickets.get(ticket_id)

    def update(self, ticket: KitchenTicket) -> None:
        self._tickets[ticket.id] = ticket
