"""Restaurant profile logic: CRUD (hours included) and catalogue search."""

import uuid

from app.repositories.entities import OpeningHour, Restaurant
from app.repositories.interfaces import MenuItemRepository, RestaurantRepository
from app.schemas.restaurants import RestaurantCreate, RestaurantUpdate
from app.services.exceptions import InvalidSearchParametersError, RestaurantNotFoundError
from app.services.geo import haversine_km

DEFAULT_RADIUS_KM = 5.0


class RestaurantService:
    """CRUD and search use cases for restaurant profiles."""

    def __init__(self, restaurants: RestaurantRepository, menu_items: MenuItemRepository) -> None:
        self._restaurants = restaurants
        self._menu_items = menu_items

    def create(self, data: RestaurantCreate) -> Restaurant:
        restaurant = Restaurant(
            id=uuid.uuid4().hex,
            name=data.name,
            cuisine_type=data.cuisine_type,
            address=data.address,
            lat=data.lat,
            lng=data.lng,
            opening_hours=[
                OpeningHour(day=h.day, open=h.open, close=h.close) for h in data.opening_hours
            ],
            auto_accept=data.auto_accept,
            owner_id=data.owner_id,
        )
        self._restaurants.add(restaurant)
        return restaurant

    def get(self, restaurant_id: str) -> Restaurant:
        restaurant = self._restaurants.get_by_id(restaurant_id)
        if restaurant is None:
            raise RestaurantNotFoundError()
        return restaurant

    def update(self, restaurant_id: str, data: RestaurantUpdate) -> Restaurant:
        """Full replacement of the profile, opening hours and auto_accept included."""
        restaurant = self.get(restaurant_id)
        restaurant.name = data.name
        restaurant.cuisine_type = data.cuisine_type
        restaurant.address = data.address
        restaurant.lat = data.lat
        restaurant.lng = data.lng
        restaurant.opening_hours = [
            OpeningHour(day=h.day, open=h.open, close=h.close) for h in data.opening_hours
        ]
        restaurant.auto_accept = data.auto_accept
        if data.owner_id is not None:
            restaurant.owner_id = data.owner_id
        self._restaurants.update(restaurant)
        return restaurant

    def search(
        self,
        cuisine: str | None = None,
        q: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        radius_km: float = DEFAULT_RADIUS_KM,
    ) -> list[Restaurant]:
        """Combinable filters: cuisine type, free text (restaurant OR dish name), distance."""
        if (lat is None) != (lng is None):
            raise InvalidSearchParametersError()
        results = self._restaurants.list_all()
        if cuisine is not None:
            results = [r for r in results if r.cuisine_type.lower() == cuisine.lower()]
        if q is not None:
            needle = q.lower()
            results = [r for r in results if self._matches_text(r, needle)]
        if lat is not None and lng is not None:
            results = [r for r in results if haversine_km(lat, lng, r.lat, r.lng) <= radius_km]
        return results

    def _matches_text(self, restaurant: Restaurant, needle: str) -> bool:
        """True if the text matches the restaurant name or one of its dish names."""
        if needle in restaurant.name.lower():
            return True
        return any(
            needle in item.name.lower()
            for item in self._menu_items.list_by_restaurant(restaurant.id)
        )
