"""Domain errors, translated to normalized ``{"detail": ...}`` HTTP responses in main.py."""


class DomainError(Exception):
    """Base class for business errors carrying their HTTP mapping."""

    status_code: int = 500
    detail: str = "Internal server error"
    headers: dict[str, str] | None = None

    def __init__(self) -> None:
        super().__init__(self.detail)


class PaymentNotFoundError(DomainError):
    """Raised when a payment id does not exist."""

    status_code = 404
    detail = "Payment not found"


class PspUnavailableError(DomainError):
    """Raised when the simulated PSP rejects the charge (flaky external dependency).

    502 Bad Gateway: the failure comes from the upstream provider, not from this
    service — this is the error the orders orchestrator retries / circuit-breaks on.
    French detail kept on purpose: it is part of the API contract used by the demo.
    """

    status_code = 502
    detail = "PSP indisponible"


class RefundNotAllowedError(DomainError):
    """Raised when refunding a payment that is not CAPTURED / PARTIALLY_REFUNDED."""

    status_code = 409
    detail = "Payment cannot be refunded in its current status"


class RefundExceedsCapturedError(DomainError):
    """Raised when cumulated refunds would exceed the captured amount."""

    status_code = 422
    detail = "Cumulated refunds exceed captured amount"
