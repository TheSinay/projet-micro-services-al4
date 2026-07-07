"""Schemas for authentication."""

from pydantic import BaseModel, Field

from app.schemas.users import Email


class LoginRequest(BaseModel):
    """Credentials payload for ``POST /api/v1/auth/login``."""

    email: Email
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Opaque bearer token returned on successful login."""

    access_token: str
    token_type: str = "bearer"
