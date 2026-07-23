"""Domain errors, translated to normalized ``{"detail": ...}`` HTTP responses in main.py."""


class DomainError(Exception):
    """Base class for business errors carrying their HTTP mapping."""

    status_code: int = 500
    detail: str = "Internal server error"
    headers: dict[str, str] | None = None

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class CartRestaurantConflictError(DomainError):
    """Raised when adding an item from another restaurant to a non-empty cart."""

    status_code = 409
    detail = "Cart already contains items from another restaurant (clear it first)"


class CartItemNotFoundError(DomainError):
    """Raised when removing a menu item that is not in the cart."""

    status_code = 404
    detail = "Item not found in cart"


class EmptyCartError(DomainError):
    """Raised when placing an order while the cart is empty."""

    status_code = 422
    detail = "Cannot place an order from an empty cart"


class OrderNotFoundError(DomainError):
    """Raised when an order id does not exist."""

    status_code = 404
    detail = "Order not found"


class IllegalStatusTransitionError(DomainError):
    """Raised on a transition forbidden by the order state machine."""

    status_code = 409
    detail = "Illegal order status transition"

    def __init__(self, current: str, requested: str) -> None:
        super().__init__(f"Illegal order status transition: {current} -> {requested}")
