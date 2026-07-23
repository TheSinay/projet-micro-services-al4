"""Domain errors, translated to normalized ``{"detail": ...}`` HTTP responses in main.py."""


class DomainError(Exception):
    """Base class for business errors carrying their HTTP mapping."""

    status_code: int = 500
    detail: str = "Internal server error"
    headers: dict[str, str] | None = None

    def __init__(self) -> None:
        super().__init__(self.detail)


class RestaurantNotFoundError(DomainError):
    """Raised when a restaurant id does not exist."""

    status_code = 404
    detail = "Restaurant not found"


class MenuItemNotFoundError(DomainError):
    """Raised when a menu item does not exist or belongs to another restaurant."""

    status_code = 404
    detail = "Menu item not found"


class KitchenTicketNotFoundError(DomainError):
    """Raised when a kitchen ticket id does not exist."""

    status_code = 404
    detail = "Kitchen ticket not found"


class TicketRefusedError(DomainError):
    """Raised when the restaurant refuses the order (``auto_accept`` is False).

    The French detail is part of the inter-service contract with the SAGA
    orchestrator (compensation demo).
    """

    status_code = 409
    detail = "commande refusée par le restaurant"


class InvalidTicketTransitionError(DomainError):
    """Raised on a kitchen ticket transition outside ACCEPTED -> PREPARING -> READY."""

    status_code = 409
    detail = "Invalid kitchen ticket status transition"


class InvalidSearchParametersError(DomainError):
    """Raised when only one of lat/lng is provided to the restaurant search."""

    status_code = 422
    detail = "lat and lng must be provided together"
