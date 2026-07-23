"""Abstract repository interfaces (structural typing via Protocol).

Business logic depends only on these contracts, so the in-memory implementations
can later be swapped for a real database / Redis without touching the services.
"""

from typing import Protocol

from app.repositories.entities import Address, User


class UserRepository(Protocol):
    """Persistence contract for users."""

    def add(self, user: User) -> None: ...

    def get_by_id(self, user_id: str) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def update(self, user: User) -> None: ...


class AddressRepository(Protocol):
    """Persistence contract for addresses."""

    def add(self, address: Address) -> None: ...

    def get_by_id(self, address_id: str) -> Address | None: ...

    def list_by_user(self, user_id: str) -> list[Address]: ...

    def update(self, address: Address) -> None: ...

    def delete(self, address_id: str) -> None: ...


class TokenStore(Protocol):
    """Opaque token -> user id mapping (would be Redis in production)."""

    def save(self, token: str, user_id: str) -> None: ...

    def get_user_id(self, token: str) -> str | None: ...
