"""Menu item logic; items are always scoped to their restaurant."""

import uuid

from app.repositories.entities import MenuItem, MenuItemOption
from app.repositories.interfaces import MenuItemRepository, RestaurantRepository
from app.schemas.menu_items import MenuItemCreate, MenuItemUpdate
from app.services.exceptions import MenuItemNotFoundError, RestaurantNotFoundError


class MenuItemService:
    """CRUD use cases for a restaurant's menu (availability included)."""

    def __init__(self, restaurants: RestaurantRepository, menu_items: MenuItemRepository) -> None:
        self._restaurants = restaurants
        self._menu_items = menu_items

    def list_for_restaurant(self, restaurant_id: str) -> list[MenuItem]:
        self._ensure_restaurant(restaurant_id)
        return self._menu_items.list_by_restaurant(restaurant_id)

    def create(self, restaurant_id: str, data: MenuItemCreate) -> MenuItem:
        self._ensure_restaurant(restaurant_id)
        item = MenuItem(
            id=uuid.uuid4().hex,
            restaurant_id=restaurant_id,
            name=data.name,
            description=data.description,
            price=round(data.price, 2),
            options=[MenuItemOption(name=o.name, price_delta=o.price_delta) for o in data.options],
            available=data.available,
        )
        self._menu_items.add(item)
        return item

    def update(self, restaurant_id: str, item_id: str, data: MenuItemUpdate) -> MenuItem:
        """Full replacement of the dish (availability toggling goes through here)."""
        item = self._get_owned(restaurant_id, item_id)
        item.name = data.name
        item.description = data.description
        item.price = round(data.price, 2)
        item.options = [
            MenuItemOption(name=o.name, price_delta=o.price_delta) for o in data.options
        ]
        item.available = data.available
        self._menu_items.update(item)
        return item

    def delete(self, restaurant_id: str, item_id: str) -> None:
        self._get_owned(restaurant_id, item_id)
        self._menu_items.delete(item_id)

    def _ensure_restaurant(self, restaurant_id: str) -> None:
        if self._restaurants.get_by_id(restaurant_id) is None:
            raise RestaurantNotFoundError()

    def _get_owned(self, restaurant_id: str, item_id: str) -> MenuItem:
        """Return the item if it exists and belongs to the restaurant, else 404."""
        self._ensure_restaurant(restaurant_id)
        item = self._menu_items.get_by_id(item_id)
        if item is None or item.restaurant_id != restaurant_id:
            raise MenuItemNotFoundError()
        return item
