"""Cart use cases: single-restaurant cart with line merging on identical item+options."""

from app.repositories.entities import Cart, CartItem, ItemOption
from app.repositories.interfaces import CartStore
from app.schemas.carts import CartItemAdd
from app.services.exceptions import CartItemNotFoundError, CartRestaurantConflictError


def _options_signature(options: list[ItemOption]) -> tuple[tuple[str, float], ...]:
    """Order-insensitive identity of a set of options (used to merge cart lines)."""
    return tuple(sorted((option.name, option.price_delta) for option in options))


class CartService:
    """Cart management for a user (one cart per user, one restaurant per cart)."""

    def __init__(self, carts: CartStore) -> None:
        self._carts = carts

    def get_cart(self, user_id: str) -> Cart:
        """Return the user's cart (an empty one if the user has none yet)."""
        return self._carts.get(user_id) or Cart(user_id=user_id)

    def add_item(self, user_id: str, data: CartItemAdd) -> Cart:
        """Add an item; merge quantities on identical (menu_item_id, options) lines.

        The cart is single-restaurant: adding an item from another restaurant while
        the cart is not empty raises a 409 (the client must clear the cart first).
        """
        cart = self.get_cart(user_id)
        if cart.items and cart.restaurant_id != data.restaurant_id:
            raise CartRestaurantConflictError()

        cart.restaurant_id = data.restaurant_id
        if data.restaurant_lat is not None:
            cart.restaurant_lat = data.restaurant_lat
        if data.restaurant_lng is not None:
            cart.restaurant_lng = data.restaurant_lng

        options = [ItemOption(name=o.name, price_delta=o.price_delta) for o in data.options]
        signature = _options_signature(options)
        existing = next(
            (
                item
                for item in cart.items
                if item.menu_item_id == data.menu_item_id
                and _options_signature(item.options) == signature
            ),
            None,
        )
        if existing is not None:
            existing.quantity += data.quantity
        else:
            cart.items.append(
                CartItem(
                    menu_item_id=data.menu_item_id,
                    name=data.name,
                    unit_price=data.unit_price,
                    quantity=data.quantity,
                    options=options,
                )
            )
        self._carts.save(cart)
        return cart

    def remove_item(self, user_id: str, menu_item_id: str) -> Cart:
        """Remove every line of the given menu item; 404 when the item is not in the cart."""
        cart = self.get_cart(user_id)
        remaining = [item for item in cart.items if item.menu_item_id != menu_item_id]
        if len(remaining) == len(cart.items):
            raise CartItemNotFoundError()
        cart.items = remaining
        if not cart.items:
            # An emptied cart is no longer bound to a restaurant.
            cart.restaurant_id = None
            cart.restaurant_lat = None
            cart.restaurant_lng = None
        self._carts.save(cart)
        return cart

    def clear(self, user_id: str) -> None:
        """Empty the cart (idempotent)."""
        self._carts.clear(user_id)
