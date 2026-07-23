"""Domain errors, translated to normalized ``{"detail": ...}`` HTTP responses in main.py."""


class DomainError(Exception):
    """Base class for business errors carrying their HTTP mapping."""

    status_code: int = 500
    detail: str = "Internal server error"
    headers: dict[str, str] | None = None

    def __init__(self) -> None:
        super().__init__(self.detail)


class CourierNotFoundError(DomainError):
    """Raised when a courier id does not exist."""

    status_code = 404
    detail = "Courier not found"


class DeliveryNotFoundError(DomainError):
    """Raised when a delivery id does not exist."""

    status_code = 404
    detail = "Delivery not found"


class NoCourierAvailableError(DomainError):
    """Raised when no courier is available for assignment.

    The 409 is the compensation trigger for the orders-side saga orchestrator.
    The French detail is part of the inter-service contract (plan T07).
    """

    status_code = 409
    detail = "aucun livreur disponible"


class InvalidDeliveryTransitionError(DomainError):
    """Raised on a status change outside ACCEPTED -> PICKED_UP -> DELIVERED."""

    status_code = 409
    detail = "Invalid delivery status transition"
