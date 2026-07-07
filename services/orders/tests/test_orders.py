"""Tests for checkout: pricing, snapshot semantics, cart emptying, history."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import DELIVERY_ADDRESS, PIZZA_ITEM, SODA_ITEM, USER_ID, add_item, place_order


def test_order_from_empty_cart_is_rejected(client: TestClient) -> None:
    response = place_order(client)
    assert response.status_code == 422
    assert "empty" in response.json()["detail"].lower()


def test_place_order_computes_prices_and_freezes_the_cart(client: TestClient) -> None:
    add_item(client, USER_ID, PIZZA_ITEM)  # (10.0 + 1.5 - 0.5) * 2 = 22.0
    add_item(client, USER_ID, SODA_ITEM)  # 3.5 * 1 = 3.5
    response = place_order(client)
    assert response.status_code == 201
    body = response.json()
    assert body["subtotal"] == 25.5
    # No restaurant coordinates anywhere: flat base fee only.
    assert body["delivery_fee"] == 2.5
    assert body["total"] == 28.0
    assert body["status"] == "RECEIVED"
    assert body["saga_state"] == "PENDING"
    assert body["payment_id"] is None
    assert body["delivery_id"] is None
    assert body["restaurant_id"] == "resto-1"
    assert body["delivery_address"]["city"] == "Paris"
    # The cart is emptied by the checkout.
    assert client.get(f"/api/v1/carts/{USER_ID}").json()["items"] == []
    # ... so a second checkout fails with 422.
    assert place_order(client).status_code == 422


def test_delivery_fee_uses_haversine_distance(client: TestClient) -> None:
    # Restaurant and delivery address are exactly 1 degree of latitude apart:
    # distance = 6371 * pi / 180 = 111.19492664... km
    # fee = 2.50 + 0.50 * 111.19492664... = 58.097... -> round(x, 2) = 58.10
    add_item(client, USER_ID, SODA_ITEM)
    response = place_order(
        client,
        delivery_address={"lat": 49.0, "lng": 2.0},
        restaurant_lat=48.0,
        restaurant_lng=2.0,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["subtotal"] == 3.5
    assert body["delivery_fee"] == 58.1
    assert body["total"] == 61.6


def test_delivery_fee_is_flat_when_restaurant_at_delivery_point(client: TestClient) -> None:
    add_item(client, USER_ID, SODA_ITEM)
    response = place_order(
        client,
        delivery_address={"lat": 48.8698, "lng": 2.3311},
        restaurant_lat=48.8698,
        restaurant_lng=2.3311,
    )
    assert response.status_code == 201
    assert response.json()["delivery_fee"] == 2.5


def test_restaurant_coordinates_from_the_cart_are_used(client: TestClient) -> None:
    add_item(client, USER_ID, {**SODA_ITEM, "restaurant_lat": 48.0, "restaurant_lng": 2.0})
    response = place_order(client, delivery_address={"lat": 49.0, "lng": 2.0})
    assert response.status_code == 201
    assert response.json()["delivery_fee"] == 58.1


def test_order_items_are_a_snapshot_with_frozen_prices(client: TestClient) -> None:
    add_item(client, USER_ID, PIZZA_ITEM)
    order = place_order(client).json()
    # Mutate the cart after checkout with the same item at another price.
    add_item(client, USER_ID, {**PIZZA_ITEM, "unit_price": 99.0, "quantity": 7})
    fetched = client.get(f"/api/v1/orders/{order['id']}").json()
    assert fetched["items"] == order["items"]
    assert fetched["items"][0]["unit_price"] == 10.0
    assert fetched["subtotal"] == order["subtotal"]
    assert fetched["total"] == order["total"]


def test_checkout_unbinds_the_restaurant_for_the_next_cart(client: TestClient) -> None:
    # After a checkout the cart is fully cleared: a new cart can bind another restaurant.
    add_item(client, USER_ID, PIZZA_ITEM)
    assert place_order(client).status_code == 201
    response = add_item(client, USER_ID, {**SODA_ITEM, "restaurant_id": "resto-2"})
    assert response.status_code == 201
    assert response.json()["restaurant_id"] == "resto-2"
    # ... and a second order for the same user goes through.
    assert place_order(client).status_code == 201


def test_delivery_fee_parameters_come_from_settings(client: TestClient) -> None:
    # base fee and per-km rate are env-configurable (ORDERS_BASE_DELIVERY_FEE / _PER_KM).
    settings = Settings(base_delivery_fee=4.0, delivery_fee_per_km=1.0)
    with TestClient(create_app(settings)) as custom_client:
        add_item(custom_client, USER_ID, SODA_ITEM)
        response = place_order(
            custom_client,
            delivery_address={"lat": 49.0, "lng": 2.0},
            restaurant_lat=48.0,
            restaurant_lng=2.0,
        )
        assert response.status_code == 201
        # 4.00 + 1.00 * 111.19492664... -> 115.19
        assert response.json()["delivery_fee"] == 115.19


def test_get_unknown_order_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/orders/nope")
    assert response.status_code == 404


def test_history_is_sorted_most_recent_first(client: TestClient) -> None:
    add_item(client, USER_ID, PIZZA_ITEM)
    first = place_order(client).json()
    add_item(client, USER_ID, SODA_ITEM)
    second = place_order(client).json()
    # Another user's order must not appear in the history.
    add_item(client, "user-2", SODA_ITEM)
    place_order(client, user_id="user-2")

    response = client.get("/api/v1/orders", params={"user_id": USER_ID})
    assert response.status_code == 200
    ids = [order["id"] for order in response.json()]
    assert ids == [second["id"], first["id"]]


def test_history_requires_user_id(client: TestClient) -> None:
    assert client.get("/api/v1/orders").status_code == 422


def test_delivery_address_requires_coordinates(client: TestClient) -> None:
    add_item(client, USER_ID, SODA_ITEM)
    response = place_order(client, delivery_address={"label": "Home"})
    assert response.status_code == 422


def test_no_event_is_published_by_checkout_before_the_saga(client: TestClient) -> None:
    # T08 wires the EventBus but publishes nothing: the saga (T09) will emit events.
    add_item(client, USER_ID, PIZZA_ITEM)
    assert place_order(client).status_code == 201
    assert client.app.state.event_bus.published == []  # type: ignore[attr-defined]


DELIVERY_ADDRESS_KEYS = {"label", "street", "city", "lat", "lng"}


def test_order_exposes_the_full_delivery_address(client: TestClient) -> None:
    add_item(client, USER_ID, PIZZA_ITEM)
    body = place_order(client).json()
    assert set(body["delivery_address"]) == DELIVERY_ADDRESS_KEYS
    assert body["delivery_address"]["lat"] == DELIVERY_ADDRESS["lat"]
