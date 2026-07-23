"""Tests for order validation (opening hours, availability, price consistency)."""

from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import MONDAY_LATE, MONDAY_NOON, create_menu_item, create_restaurant


def _validate(
    client: TestClient, restaurant_id: str, items: list[dict[str, object]], at: str | None
) -> dict[str, Any]:
    payload: dict[str, object] = {"items": items}
    if at is not None:
        payload["at"] = at
    response = client.post(f"/api/v1/restaurants/{restaurant_id}/order-validations", json=payload)
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


def test_valid_order_returns_subtotal(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    dish = create_menu_item(client, restaurant["id"], price=12.5)
    dessert = create_menu_item(client, restaurant["id"], name="Dessert", price=6.0)
    body = _validate(
        client,
        restaurant["id"],
        [
            {"menu_item_id": dish["id"], "unit_price": 12.5, "quantity": 2},
            {"menu_item_id": dessert["id"], "unit_price": 6.0, "quantity": 1},
        ],
        at=MONDAY_NOON,
    )
    assert body == {"valid": True, "subtotal": 31.0, "reasons": []}


def test_valid_order_with_default_time_when_always_open(client: TestClient) -> None:
    hours = [{"day": day, "open": "00:00", "close": "23:59"} for day in range(7)]
    restaurant = create_restaurant(client, opening_hours=hours)
    dish = create_menu_item(client, restaurant["id"])
    body = _validate(
        client,
        restaurant["id"],
        [{"menu_item_id": dish["id"], "unit_price": 12.5, "quantity": 1}],
        at=None,
    )
    assert body["valid"] is True
    assert body["subtotal"] == 12.5


def test_unavailable_item_invalidates_the_order(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    dish = create_menu_item(client, restaurant["id"], name="Rupture", available=False)
    body = _validate(
        client,
        restaurant["id"],
        [{"menu_item_id": dish["id"], "unit_price": 12.5, "quantity": 1}],
        at=MONDAY_NOON,
    )
    assert body["valid"] is False
    assert body["subtotal"] is None
    assert "menu item 'Rupture' is unavailable" in body["reasons"]


def test_closed_restaurant_invalidates_the_order(client: TestClient) -> None:
    restaurant = create_restaurant(client)  # open 10:00-22:00
    dish = create_menu_item(client, restaurant["id"])
    body = _validate(
        client,
        restaurant["id"],
        [{"menu_item_id": dish["id"], "unit_price": 12.5, "quantity": 1}],
        at=MONDAY_LATE,
    )
    assert body["valid"] is False
    assert "restaurant is closed at the requested time" in body["reasons"]


def test_restaurant_without_opening_hours_is_always_closed(client: TestClient) -> None:
    restaurant = create_restaurant(client, opening_hours=[])
    dish = create_menu_item(client, restaurant["id"])
    body = _validate(
        client,
        restaurant["id"],
        [{"menu_item_id": dish["id"], "unit_price": 12.5, "quantity": 1}],
        at=MONDAY_NOON,
    )
    assert body["valid"] is False


def test_price_mismatch_invalidates_the_order(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    dish = create_menu_item(client, restaurant["id"], price=12.5)
    body = _validate(
        client,
        restaurant["id"],
        [{"menu_item_id": dish["id"], "unit_price": 9.99, "quantity": 1}],
        at=MONDAY_NOON,
    )
    assert body["valid"] is False
    assert body["reasons"] == [f"price mismatch for '{dish['name']}': expected 12.5, got 9.99"]


def test_unknown_menu_item_invalidates_the_order(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    body = _validate(
        client,
        restaurant["id"],
        [{"menu_item_id": "ghost-dish", "unit_price": 5.0, "quantity": 1}],
        at=MONDAY_NOON,
    )
    assert body["valid"] is False
    assert "menu item 'ghost-dish' not found" in body["reasons"]


def test_multiple_reasons_are_cumulative(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    dish = create_menu_item(client, restaurant["id"], available=False)
    body = _validate(
        client,
        restaurant["id"],
        [{"menu_item_id": dish["id"], "unit_price": 1.0, "quantity": 1}],
        at=MONDAY_LATE,
    )
    assert body["valid"] is False
    assert len(body["reasons"]) == 3  # closed + unavailable + price mismatch


def test_validation_for_unknown_restaurant_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/restaurants/unknown-id/order-validations",
        json={"items": [{"menu_item_id": "x", "unit_price": 1.0, "quantity": 1}]},
    )
    assert response.status_code == 404


def test_validation_requires_at_least_one_item(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    response = client.post(
        f"/api/v1/restaurants/{restaurant['id']}/order-validations", json={"items": []}
    )
    assert response.status_code == 422
