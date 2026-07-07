"""Domain entities persisted by the repositories."""

from dataclasses import dataclass


@dataclass
class User:
    """A registered account. ``password_hash`` is a salted PBKDF2 digest, never plaintext."""

    id: str
    email: str
    password_hash: str
    name: str
    phone: str


@dataclass
class Address:
    """A delivery address belonging to a user."""

    id: str
    user_id: str
    label: str
    street: str
    city: str
    lat: float
    lng: float
