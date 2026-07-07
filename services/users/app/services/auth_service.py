"""Authentication logic: login and opaque token resolution."""

import secrets

from app.repositories.entities import User
from app.repositories.interfaces import TokenStore, UserRepository
from app.services.exceptions import InvalidCredentialsError, InvalidTokenError
from app.services.security import verify_password


class AuthService:
    """Issues and resolves opaque bearer tokens (``secrets.token_urlsafe``)."""

    def __init__(self, users: UserRepository, tokens: TokenStore) -> None:
        self._users = users
        self._tokens = tokens

    def login(self, email: str, password: str) -> str:
        """Verify credentials and return a new opaque token."""
        user = self._users.get_by_email(email.lower())
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        token = secrets.token_urlsafe(32)
        self._tokens.save(token, user.id)
        return token

    def resolve_token(self, token: str) -> User:
        """Return the user owning the token, or raise ``InvalidTokenError``."""
        user_id = self._tokens.get_user_id(token)
        user = self._users.get_by_id(user_id) if user_id is not None else None
        if user is None:
            raise InvalidTokenError()
        return user
