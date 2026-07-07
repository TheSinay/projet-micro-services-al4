"""Domain errors, translated to normalized ``{"detail": ...}`` HTTP responses in main.py."""


class DomainError(Exception):
    """Base class for business errors carrying their HTTP mapping."""

    status_code: int = 500
    detail: str = "Internal server error"
    headers: dict[str, str] | None = None

    def __init__(self) -> None:
        super().__init__(self.detail)


class EmailAlreadyRegisteredError(DomainError):
    """Raised when registering with an email that already exists."""

    status_code = 409
    detail = "Email already registered"


class InvalidCredentialsError(DomainError):
    """Raised when login credentials do not match any account."""

    status_code = 401
    detail = "Invalid email or password"
    headers: dict[str, str] | None = {"WWW-Authenticate": "Bearer"}


class InvalidTokenError(DomainError):
    """Raised when the bearer token is missing, malformed or unknown."""

    status_code = 401
    detail = "Invalid or missing authentication token"
    headers: dict[str, str] | None = {"WWW-Authenticate": "Bearer"}


class AddressNotFoundError(DomainError):
    """Raised when an address does not exist or belongs to another user."""

    status_code = 404
    detail = "Address not found"
