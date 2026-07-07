"""Shared fixtures — each test gets a fresh application, hence a clean in-memory state.

No test requires Redis: the default backends are the in-memory implementations.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

USER_ID = "user-1"

PIZZA_ITEM: dict[str, Any] = {
    "restaurant_id": "resto-1",
    "menu_item_id": "pizza-margherita",
    "name": "Pizza Margherita",
    "unit_price": 10.0,
    "quantity": 2,
    "options": [
        {"name": "extra cheese", "price_delta": 1.5},
        {"name": "no basil", "price_delta": -0.5},
    ],
}

SODA_ITEM: dict[str, Any] = {
    "restaurant_id": "resto-1",
    "menu_item_id": "soda-cola",
    "name": "Cola",
    "unit_price": 3.5,
    "quantity": 1,
    "options": [],
}

DELIVERY_ADDRESS: dict[str, Any] = {
    "label": "Home",
    "street": "10 rue de la Paix",
    "city": "Paris",
    "lat": 48.8698,
    "lng": 2.3311,
}


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient bound to a brand new application instance (in-memory backends)."""
    with TestClient(create_app()) as test_client:
        yield test_client


def add_item(client: TestClient, user_id: str, item: dict[str, Any]) -> Any:
    """Helper: add an item to a user's cart."""
    return client.post(f"/api/v1/carts/{user_id}/items", json=item)


def place_order(
    client: TestClient,
    user_id: str = USER_ID,
    delivery_address: dict[str, Any] | None = None,
    **extra: Any,
) -> Any:
    """Helper: place an order for a user."""
    payload: dict[str, Any] = {
        "user_id": user_id,
        "delivery_address": delivery_address or DELIVERY_ADDRESS,
        **extra,
    }
    return client.post("/api/v1/orders", json=payload)
