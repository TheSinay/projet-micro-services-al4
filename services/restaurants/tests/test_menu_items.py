"""Tests for menu item CRUD and availability management."""

from fastapi.testclient import TestClient

from tests.conftest import MENU_ITEM_PAYLOAD, create_menu_item, create_restaurant


def test_create_menu_item_returns_201(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    body = create_menu_item(client, restaurant["id"])
    assert body["id"]
    assert body["restaurant_id"] == restaurant["id"]
    assert body["price"] == 12.5
    assert body["available"] is True


def test_create_menu_item_for_unknown_restaurant_returns_404(client: TestClient) -> None:
    response = client.post("/api/v1/restaurants/unknown-id/menu-items", json=MENU_ITEM_PAYLOAD)
    assert response.status_code == 404


def test_create_menu_item_with_invalid_price_returns_422(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    payload = {**MENU_ITEM_PAYLOAD, "price": 0}
    response = client.post(f"/api/v1/restaurants/{restaurant['id']}/menu-items", json=payload)
    assert response.status_code == 422


def test_update_menu_item_toggles_availability(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    item = create_menu_item(client, restaurant["id"])
    payload = {**MENU_ITEM_PAYLOAD, "available": False, "price": 13.9}
    response = client.put(
        f"/api/v1/restaurants/{restaurant['id']}/menu-items/{item['id']}", json=payload
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["price"] == 13.9


def test_update_unknown_menu_item_returns_404(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    response = client.put(
        f"/api/v1/restaurants/{restaurant['id']}/menu-items/unknown-id", json=MENU_ITEM_PAYLOAD
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Menu item not found"}


def test_update_menu_item_of_another_restaurant_returns_404(client: TestClient) -> None:
    owner = create_restaurant(client)
    other = create_restaurant(client, name="Autre Table")
    item = create_menu_item(client, owner["id"])
    response = client.put(
        f"/api/v1/restaurants/{other['id']}/menu-items/{item['id']}", json=MENU_ITEM_PAYLOAD
    )
    assert response.status_code == 404


def test_delete_menu_item_removes_it_from_the_menu(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    item = create_menu_item(client, restaurant["id"])
    response = client.delete(f"/api/v1/restaurants/{restaurant['id']}/menu-items/{item['id']}")
    assert response.status_code == 204
    detail = client.get(f"/api/v1/restaurants/{restaurant['id']}").json()
    assert detail["menu"] == []


def test_delete_unknown_menu_item_returns_404(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    response = client.delete(f"/api/v1/restaurants/{restaurant['id']}/menu-items/unknown-id")
    assert response.status_code == 404
