"""Shared fixtures — each test gets a fresh application (clean in-memory state)."""

from collections.abc import Iterator
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.repositories.memory import InMemoryNotificationRepository
from app.services.dispatch import NotificationDispatcher


def make_event(
    event: str,
    data: dict[str, Any] | None = None,
    correlation_id: str | None = "corr-test-1",
) -> dict[str, Any]:
    """Build a platform event envelope ``{"event", "correlation_id", "data"}``."""
    return {"event": event, "correlation_id": correlation_id, "data": data or {}}


class RecordingLogger:
    """Minimal structlog stand-in recording ``(level, event, kwargs)`` tuples."""

    def __init__(self) -> None:
        self.entries: list[tuple[str, str, dict[str, Any]]] = []

    def debug(self, event: str, **kwargs: Any) -> None:
        self.entries.append(("debug", event, kwargs))

    def info(self, event: str, **kwargs: Any) -> None:
        self.entries.append(("info", event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self.entries.append(("warning", event, kwargs))

    def events(self, level: str) -> list[str]:
        return [event for entry_level, event, _ in self.entries if entry_level == level]


@pytest.fixture
def test_settings() -> Settings:
    """Hermetic settings: in-memory event backend, no Redis."""
    return Settings(event_backend="memory")


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """A brand new application instance per test."""
    return create_app(test_settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """A TestClient bound to the fresh application instance (lifespan included)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def repository(app: FastAPI) -> InMemoryNotificationRepository:
    """The in-memory notification store wired into the application under test."""
    return cast(InMemoryNotificationRepository, app.state.notification_repository)


@pytest.fixture
def dispatcher(app: FastAPI) -> NotificationDispatcher:
    """The dispatcher wired into the application under test."""
    return cast(NotificationDispatcher, app.state.dispatcher)
