"""Shared fixtures — each test gets a fresh application, hence a clean in-memory state."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

RESTAURANT_PAYLOAD: dict[str, object] = {
    "name": "Le Bistrot Test",
    "cuisine_type": "french",
    "address": "1 rue des Tests, 75001 Paris",
    "lat": 48.8566,
    "lng": 2.3522,
    "opening_hours": [{"day": day, "open": "10:00", "close": "22:00"} for day in range(7)],
    "auto_accept": True,
}

MENU_ITEM_PAYLOAD: dict[str, object] = {
    "name": "Plat du jour",
    "description": "Le plat maison",
    "price": 12.5,
    "options": [{"name": "Supplement fromage", "price_delta": 1.5}],
    "available": True,
}

# Monday (weekday 0) at lunch / late night — deterministic instants for validations.
MONDAY_NOON = "2026-07-06T12:00:00"
MONDAY_LATE = "2026-07-06T23:30:00"


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient bound to a brand new application (no seed, in-memory event bus)."""
    settings = Settings(seed_data=False, event_bus="memory")
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def seeded_client() -> Iterator[TestClient]:
    """A TestClient on an application populated with the demo catalogue."""
    settings = Settings(seed_data=True, event_bus="memory")
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def create_restaurant(client: TestClient, **overrides: object) -> dict[str, Any]:
    """POST a restaurant built from the default payload and return the response body."""
    payload = {**RESTAURANT_PAYLOAD, **overrides}
    response = client.post("/api/v1/restaurants", json=payload)
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body


def create_menu_item(client: TestClient, restaurant_id: str, **overrides: object) -> dict[str, Any]:
    """POST a menu item built from the default payload and return the response body."""
    payload = {**MENU_ITEM_PAYLOAD, **overrides}
    response = client.post(f"/api/v1/restaurants/{restaurant_id}/menu-items", json=payload)
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body
