"""Order validation logic (SAGA step 2): opening hours, availability, price consistency.

Design choice: the verdict is always returned with HTTP 200 (``valid`` + ``reasons``),
which keeps the orchestrator logic simple — see README.
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.repositories.entities import Restaurant
from app.repositories.interfaces import MenuItemRepository, RestaurantRepository
from app.schemas.validations import OrderValidationRequest
from app.services.exceptions import RestaurantNotFoundError


@dataclass
class ValidationResult:
    """Business verdict of an order validation."""

    valid: bool
    subtotal: float | None = None
    reasons: list[str] = field(default_factory=list)


class OrderValidationService:
    """Validates an order draft against the catalogue and the opening hours."""

    def __init__(self, restaurants: RestaurantRepository, menu_items: MenuItemRepository) -> None:
        self._restaurants = restaurants
        self._menu_items = menu_items

    def validate(self, restaurant_id: str, data: OrderValidationRequest) -> ValidationResult:
        restaurant = self._restaurants.get_by_id(restaurant_id)
        if restaurant is None:
            raise RestaurantNotFoundError()

        reasons: list[str] = []
        at = data.at or datetime.now()
        if not self._is_open(restaurant, at):
            reasons.append("restaurant is closed at the requested time")

        subtotal = 0.0
        for line in data.items:
            item = self._menu_items.get_by_id(line.menu_item_id)
            if item is None or item.restaurant_id != restaurant_id:
                reasons.append(f"menu item '{line.menu_item_id}' not found")
                continue
            if not item.available:
                reasons.append(f"menu item '{item.name}' is unavailable")
            if abs(item.price - line.unit_price) > 1e-9:
                reasons.append(
                    f"price mismatch for '{item.name}': "
                    f"expected {item.price}, got {line.unit_price}"
                )
            subtotal += item.price * line.quantity

        if reasons:
            return ValidationResult(valid=False, reasons=reasons)
        return ValidationResult(valid=True, subtotal=round(subtotal, 2))

    @staticmethod
    def _is_open(restaurant: Restaurant, at: datetime) -> bool:
        """True if one opening slot covers ``at`` (day 0 = Monday, "HH:MM" comparison)."""
        hhmm = at.strftime("%H:%M")
        return any(
            slot.day == at.weekday() and slot.open <= hhmm < slot.close
            for slot in restaurant.opening_hours
        )
