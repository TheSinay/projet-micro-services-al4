"""QA complementary tests: boundary and adversarial cases (added by the testeur agent).

Covers: opening-hour boundaries, cross-restaurant text search, invalid quantities,
one-cent price mismatch, foreign menu item in a validation, radius without lat/lng.
"""

from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import create_menu_item, create_restaurant

# 2026-07-06 is a Monday (weekday 0). Default restaurant hours: 10:00 -> 22:00 every day.
MONDAY_AT_OPEN = "2026-07-06T10:00:00"
MONDAY_JUST_BEFORE_OPEN = "2026-07-06T09:59:59"
MONDAY_AT_CLOSE = "2026-07-06T22:00:00"
MONDAY_JUST_BEFORE_CLOSE = "2026-07-06T21:59:59"


def _validate(
    client: TestClient, restaurant_id: str, items: list[dict[str, object]], at: str
) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/restaurants/{restaurant_id}/order-validations",
        json={"items": items, "at": at},
    )
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


# --- Opening hour boundaries -------------------------------------------------


def test_order_exactly_at_opening_time_is_valid(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    dish = create_menu_item(client, restaurant["id"])
    body = _validate(
        client,
        restaurant["id"],
        [{"menu_item_id": dish["id"], "unit_price": 12.5, "quantity": 1}],
        at=MONDAY_AT_OPEN,
    )
    assert body["valid"] is True


def test_order_just_before_opening_time_is_rejected(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    dish = create_menu_item(client, restaurant["id"])
    body = _validate(
        client,
        restaurant["id"],
        [{"menu_item_id": dish["id"], "unit_price": 12.5, "quantity": 1}],
        at=MONDAY_JUST_BEFORE_OPEN,
    )
    assert body["valid"] is False
    assert "restaurant is closed at the requested time" in body["reasons"]


def test_order_exactly_at_closing_time_is_rejected(client: TestClient) -> None:
    """Close bound is exclusive: at 22:00 sharp the restaurant is already closed."""
    restaurant = create_restaurant(client)
    dish = create_menu_item(client, restaurant["id"])
    body = _validate(
        client,
        restaurant["id"],
        [{"menu_item_id": dish["id"], "unit_price": 12.5, "quantity": 1}],
        at=MONDAY_AT_CLOSE,
    )
    assert body["valid"] is False
    assert "restaurant is closed at the requested time" in body["reasons"]


def test_order_just_before_closing_time_is_valid(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    dish = create_menu_item(client, restaurant["id"])
    body = _validate(
        client,
        restaurant["id"],
        [{"menu_item_id": dish["id"], "unit_price": 12.5, "quantity": 1}],
        at=MONDAY_JUST_BEFORE_CLOSE,
    )
    assert body["valid"] is True


def test_opening_slot_of_another_day_does_not_open_today(client: TestClient) -> None:
    """A slot on Tuesday (day 1) must not make the restaurant open on Monday noon."""
    restaurant = create_restaurant(
        client, opening_hours=[{"day": 1, "open": "10:00", "close": "22:00"}]
    )
    dish = create_menu_item(client, restaurant["id"])
    body = _validate(
        client,
        restaurant["id"],
        [{"menu_item_id": dish["id"], "unit_price": 12.5, "quantity": 1}],
        at="2026-07-06T12:00:00",  # Monday
    )
    assert body["valid"] is False


# --- Search: cross-restaurant text match, radius without coordinates ----------


def test_search_text_matches_dish_of_one_and_name_of_another(client: TestClient) -> None:
    """q= must return BOTH the restaurant named after the dish and the one serving it."""
    named = create_restaurant(client, name="Ramen House", cuisine_type="japanese")
    serving = create_restaurant(client, name="Sakura Sushi", cuisine_type="japanese")
    unrelated = create_restaurant(client, name="La Bella Napoli", cuisine_type="italian")
    create_menu_item(client, serving["id"], name="Ramen tonkotsu")
    create_menu_item(client, unrelated["id"], name="Pizza Margherita")
    create_menu_item(client, named["id"], name="Gyoza")

    response = client.get("/api/v1/restaurants?q=ramen")
    assert response.status_code == 200
    names = {restaurant["name"] for restaurant in response.json()}
    assert names == {"Ramen House", "Sakura Sushi"}


def test_search_radius_without_lat_lng_ignores_the_radius(client: TestClient) -> None:
    """radius_km alone has no coordinates to apply to: documented as a no-op filter."""
    create_restaurant(client, name="Le Bistrot Test", lat=48.8566, lng=2.3522)
    create_restaurant(client, name="Bouchon Lyonnais", lat=45.7640, lng=4.8357)
    response = client.get("/api/v1/restaurants?radius_km=1")
    assert response.status_code == 200
    names = {restaurant["name"] for restaurant in response.json()}
    assert names == {"Le Bistrot Test", "Bouchon Lyonnais"}


def test_search_with_lng_but_no_lat_returns_422(client: TestClient) -> None:
    """Symmetric of the lat-only case already covered in test_search.py."""
    create_restaurant(client)
    response = client.get("/api/v1/restaurants?lng=2.35")
    assert response.status_code == 422
    assert response.json() == {"detail": "lat and lng must be provided together"}


# --- Validation: quantities, one-cent mismatch, foreign menu item -------------


def test_validation_rejects_zero_and_negative_quantities(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    dish = create_menu_item(client, restaurant["id"])
    for quantity in (0, -1):
        response = client.post(
            f"/api/v1/restaurants/{restaurant['id']}/order-validations",
            json={
                "items": [{"menu_item_id": dish["id"], "unit_price": 12.5, "quantity": quantity}]
            },
        )
        assert response.status_code == 422, f"quantity={quantity} should be rejected"


def test_validation_detects_one_cent_price_mismatch(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    dish = create_menu_item(client, restaurant["id"], price=12.5)
    body = _validate(
        client,
        restaurant["id"],
        [{"menu_item_id": dish["id"], "unit_price": 12.49, "quantity": 1}],
        at=MONDAY_AT_OPEN,
    )
    assert body["valid"] is False
    assert body["subtotal"] is None
    assert any("price mismatch" in reason for reason in body["reasons"])


def test_validation_rejects_menu_item_of_another_restaurant(client: TestClient) -> None:
    """A dish that exists but belongs to another restaurant must not validate."""
    target = create_restaurant(client)
    other = create_restaurant(client, name="Autre Table")
    foreign_dish = create_menu_item(client, other["id"], price=12.5)
    body = _validate(
        client,
        target["id"],
        [{"menu_item_id": foreign_dish["id"], "unit_price": 12.5, "quantity": 1}],
        at=MONDAY_AT_OPEN,
    )
    assert body["valid"] is False
    assert f"menu item '{foreign_dish['id']}' not found" in body["reasons"]


def test_refused_ticket_is_persisted_for_audit(client: TestClient) -> None:
    """The 409 refusal must still record a REFUSED ticket (auditability requirement)."""
    restaurant = create_restaurant(client, name="Chez Refus", auto_accept=False)
    response = client.post(
        f"/api/v1/restaurants/{restaurant['id']}/kitchen-tickets",
        json={"order_id": "order-audit", "items": [{"menu_item_id": "dish-1", "quantity": 1}]},
    )
    assert response.status_code == 409

    repository = client.app.state.ticket_repository  # type: ignore[attr-defined]
    tickets = list(repository._tickets.values())
    assert len(tickets) == 1
    assert tickets[0].status == "REFUSED"
    assert tickets[0].order_id == "order-audit"
