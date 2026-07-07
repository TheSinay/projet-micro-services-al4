"""Schemas for user registration and profile."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Simple RFC-like pattern; avoids the extra ``email-validator`` dependency (stdlib-only rule).
Email = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", max_length=254),
]


class UserCreate(BaseModel):
    """Registration payload."""

    email: Email
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=3, max_length=30)


class UserUpdate(BaseModel):
    """Profile update payload (PUT semantics: full replacement of mutable fields)."""

    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=3, max_length=30)


class UserRead(BaseModel):
    """Public representation of a user — never exposes the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    phone: str
