"""FastAPI dependency wiring: repositories (from app.state), services, authentication."""

from typing import Annotated

from fastapi import Depends, Header, Request

from app.repositories.entities import User
from app.repositories.interfaces import AddressRepository, TokenStore, UserRepository
from app.services.address_service import AddressService
from app.services.auth_service import AuthService
from app.services.exceptions import InvalidTokenError
from app.services.user_service import UserService


def get_user_repository(request: Request) -> UserRepository:
    repository: UserRepository = request.app.state.user_repository
    return repository


def get_address_repository(request: Request) -> AddressRepository:
    repository: AddressRepository = request.app.state.address_repository
    return repository


def get_token_store(request: Request) -> TokenStore:
    store: TokenStore = request.app.state.token_store
    return store


def get_user_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(users)


def get_auth_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    tokens: Annotated[TokenStore, Depends(get_token_store)],
) -> AuthService:
    return AuthService(users, tokens)


def get_address_service(
    addresses: Annotated[AddressRepository, Depends(get_address_repository)],
) -> AddressService:
    return AddressService(addresses)


def get_current_user(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Resolve the ``Authorization: Bearer <token>`` header into a user (401 otherwise)."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise InvalidTokenError()
    return auth_service.resolve_token(token.strip())


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
AddressServiceDep = Annotated[AddressService, Depends(get_address_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]
