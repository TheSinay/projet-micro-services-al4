"""Shared fixtures — each test gets a fresh application (clean state, in-memory event bus)."""

from collections.abc import Iterator
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.events import InMemoryEventBus
from app.main import create_app

PICKUP: dict[str, Any] = {"label": "Chez Momo", "lat": 48.8600, "lng": 2.3400}
DROPOFF: dict[str, Any] = {"label": "Client - 5 rue des Lilas", "lat": 48.8500, "lng": 2.3550}

DELIVERY_PAYLOAD: dict[str, Any] = {
    "order_id": "order-1",
    "pickup_address": PICKUP,
    "dropoff_address": DROPOFF,
}


def make_courier_payload(
    name: str = "Marco Rossi",
    lat: float = 48.8867,
    lng: float = 2.3431,
    available: bool = True,
) -> dict[str, Any]:
    """Build a valid POST /couriers payload."""
    return {
        "name": name,
        "phone": "+33611111111",
        "available": available,
        "location": {"lat": lat, "lng": lng},
    }


def create_courier(
    client: TestClient,
    name: str = "Marco Rossi",
    lat: float = 48.8867,
    lng: float = 2.3431,
    available: bool = True,
) -> str:
    """Create a courier through the API and return its id."""
    response = client.post("/api/v1/couriers", json=make_courier_payload(name, lat, lng, available))
    assert response.status_code == 201
    courier_id: str = response.json()["id"]
    return courier_id


@pytest.fixture
def test_settings() -> Settings:
    """Hermetic settings: no Redis, no seed data."""
    return Settings(event_backend="memory", seed_data=False)


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """A brand new application instance per test."""
    return create_app(test_settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """A TestClient bound to the fresh application instance."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def event_bus(app: FastAPI) -> InMemoryEventBus:
    """The in-memory event bus wired into the application under test."""
    return cast(InMemoryEventBus, app.state.event_bus)
