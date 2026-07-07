"""User account logic: registration and profile management."""

import uuid

from app.repositories.entities import User
from app.repositories.interfaces import UserRepository
from app.schemas.users import UserCreate, UserUpdate
from app.services.exceptions import EmailAlreadyRegisteredError
from app.services.security import hash_password


class UserService:
    """Registration and profile use cases."""

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def register(self, data: UserCreate) -> User:
        """Create an account; emails are unique (case-insensitive)."""
        email = data.email.lower()
        if self._users.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError()
        user = User(
            id=uuid.uuid4().hex,
            email=email,
            password_hash=hash_password(data.password),
            name=data.name,
            phone=data.phone,
        )
        self._users.add(user)
        return user

    def update_profile(self, user: User, data: UserUpdate) -> User:
        """Replace the mutable profile fields of the authenticated user."""
        user.name = data.name
        user.phone = data.phone
        self._users.update(user)
        return user
