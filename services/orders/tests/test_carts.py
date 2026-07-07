"""Tests for the cart endpoints: add/merge/remove/clear and the single-restaurant rule."""

from fastapi.testclient import TestClient

from tests.conftest import PIZZA_ITEM, SODA_ITEM, USER_ID, add_item


def test_get_unknown_cart_returns_empty_cart(client: TestClient) -> None:
    response = client.get(f"/api/v1/carts/{USER_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == USER_ID
    assert body["restaurant_id"] is None
    assert body["items"] == []


def test_add_item_creates_cart_line(client: TestClient) -> None:
    response = add_item(client, USER_ID, PIZZA_ITEM)
    assert response.status_code == 201
    body = response.json()
    assert body["restaurant_id"] == "resto-1"
    assert len(body["items"]) == 1
    line = body["items"][0]
    assert line["menu_item_id"] == "pizza-margherita"
    assert line["quantity"] == 2
    assert line["unit_price"] == 10.0
    assert {option["name"] for option in line["options"]} == {"extra cheese", "no basil"}


def test_add_same_item_and_options_merges_quantities(client: TestClient) -> None:
    add_item(client, USER_ID, PIZZA_ITEM)
    response = add_item(client, USER_ID, {**PIZZA_ITEM, "quantity": 3})
    assert response.status_code == 201
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 5


def test_same_item_with_different_options_creates_a_second_line(client: TestClient) -> None:
    add_item(client, USER_ID, PIZZA_ITEM)
    response = add_item(client, USER_ID, {**PIZZA_ITEM, "options": []})
    assert response.status_code == 201
    assert len(response.json()["items"]) == 2


def test_adding_item_from_another_restaurant_is_rejected(client: TestClient) -> None:
    add_item(client, USER_ID, PIZZA_ITEM)
    response = add_item(client, USER_ID, {**SODA_ITEM, "restaurant_id": "resto-2"})
    assert response.status_code == 409
    assert "restaurant" in response.json()["detail"].lower()


def test_cart_can_switch_restaurant_after_being_cleared(client: TestClient) -> None:
    add_item(client, USER_ID, PIZZA_ITEM)
    assert client.delete(f"/api/v1/carts/{USER_ID}").status_code == 204
    response = add_item(client, USER_ID, {**SODA_ITEM, "restaurant_id": "resto-2"})
    assert response.status_code == 201
    assert response.json()["restaurant_id"] == "resto-2"


def test_remove_item_deletes_the_line(client: TestClient) -> None:
    add_item(client, USER_ID, PIZZA_ITEM)
    add_item(client, USER_ID, SODA_ITEM)
    response = client.delete(f"/api/v1/carts/{USER_ID}/items/{PIZZA_ITEM['menu_item_id']}")
    assert response.status_code == 200
    body = response.json()
    assert [item["menu_item_id"] for item in body["items"]] == ["soda-cola"]


def test_removing_last_item_unbinds_the_restaurant(client: TestClient) -> None:
    add_item(client, USER_ID, PIZZA_ITEM)
    response = client.delete(f"/api/v1/carts/{USER_ID}/items/{PIZZA_ITEM['menu_item_id']}")
    assert response.status_code == 200
    assert response.json()["restaurant_id"] is None
    # A different restaurant is now accepted.
    response = add_item(client, USER_ID, {**SODA_ITEM, "restaurant_id": "resto-2"})
    assert response.status_code == 201


def test_remove_unknown_item_returns_404(client: TestClient) -> None:
    add_item(client, USER_ID, PIZZA_ITEM)
    response = client.delete(f"/api/v1/carts/{USER_ID}/items/unknown-item")
    assert response.status_code == 404


def test_clear_cart_empties_it(client: TestClient) -> None:
    add_item(client, USER_ID, PIZZA_ITEM)
    assert client.delete(f"/api/v1/carts/{USER_ID}").status_code == 204
    body = client.get(f"/api/v1/carts/{USER_ID}").json()
    assert body["items"] == []
    assert body["restaurant_id"] is None


def test_clear_is_idempotent_on_unknown_cart(client: TestClient) -> None:
    assert client.delete(f"/api/v1/carts/{USER_ID}").status_code == 204


def test_invalid_quantity_is_rejected(client: TestClient) -> None:
    response = add_item(client, USER_ID, {**PIZZA_ITEM, "quantity": 0})
    assert response.status_code == 422


def test_negative_quantity_is_rejected(client: TestClient) -> None:
    response = add_item(client, USER_ID, {**PIZZA_ITEM, "quantity": -2})
    assert response.status_code == 422


def test_options_in_a_different_order_merge_into_the_same_line(client: TestClient) -> None:
    # The option signature must be order-insensitive: same options, shuffled order.
    add_item(client, USER_ID, PIZZA_ITEM)
    shuffled = {**PIZZA_ITEM, "options": list(reversed(PIZZA_ITEM["options"])), "quantity": 1}
    response = add_item(client, USER_ID, shuffled)
    assert response.status_code == 201
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == PIZZA_ITEM["quantity"] + 1


def test_same_option_name_with_different_delta_is_a_distinct_line(client: TestClient) -> None:
    add_item(client, USER_ID, {**PIZZA_ITEM, "options": [{"name": "cheese", "price_delta": 1.0}]})
    response = add_item(
        client, USER_ID, {**PIZZA_ITEM, "options": [{"name": "cheese", "price_delta": 2.0}]}
    )
    assert response.status_code == 201
    assert len(response.json()["items"]) == 2


def test_restaurant_coordinates_are_recorded_on_the_cart(client: TestClient) -> None:
    response = add_item(
        client, USER_ID, {**PIZZA_ITEM, "restaurant_lat": 48.0, "restaurant_lng": 2.0}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["restaurant_lat"] == 48.0
    assert body["restaurant_lng"] == 2.0
