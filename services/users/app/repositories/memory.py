"""In-memory implementations — stand-ins for a real database (ADR 0005).

Instances are created per application in ``create_app`` (stored on ``app.state``),
never as module-level globals, so every test starts from a clean state.
"""

from app.repositories.entities import Address, User


class InMemoryUserRepository:
    """Dict-backed user store."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    def add(self, user: User) -> None:
        self._users[user.id] = user

    def get_by_id(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        return next((user for user in self._users.values() if user.email == email), None)

    def update(self, user: User) -> None:
        self._users[user.id] = user


class InMemoryAddressRepository:
    """Dict-backed address store."""

    def __init__(self) -> None:
        self._addresses: dict[str, Address] = {}

    def add(self, address: Address) -> None:
        self._addresses[address.id] = address

    def get_by_id(self, address_id: str) -> Address | None:
        return self._addresses.get(address_id)

    def list_by_user(self, user_id: str) -> list[Address]:
        return [address for address in self._addresses.values() if address.user_id == user_id]

    def update(self, address: Address) -> None:
        self._addresses[address.id] = address

    def delete(self, address_id: str) -> None:
        self._addresses.pop(address_id, None)


class InMemoryTokenStore:
    """Token -> user id map. In production this would live in Redis (stateless service)."""

    def __init__(self) -> None:
        self._tokens: dict[str, str] = {}

    def save(self, token: str, user_id: str) -> None:
        self._tokens[token] = user_id

    def get_user_id(self, token: str) -> str | None:
        return self._tokens.get(token)
