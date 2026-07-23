"""Domain errors, translated to normalized ``{"detail": ...}`` HTTP responses in main.py.

The notifications service is read-only over HTTP, so no concrete business error
exists yet; the base class keeps the error-handling contract of the ``users``
template in place for future endpoints.
"""


class DomainError(Exception):
    """Base class for business errors carrying their HTTP mapping."""

    status_code: int = 500
    detail: str = "Internal server error"
    headers: dict[str, str] | None = None

    def __init__(self) -> None:
        super().__init__(self.detail)
