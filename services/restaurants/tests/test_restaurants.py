"""Tests for restaurant profile CRUD (opening hours included)."""

from fastapi.testclient import TestClient

from tests.conftest import RESTAURANT_PAYLOAD, create_menu_item, create_restaurant


def test_create_restaurant_returns_201_with_profile(client: TestClient) -> None:
    body = create_restaurant(client)
    assert body["id"]
    assert body["name"] == RESTAURANT_PAYLOAD["name"]
    assert body["cuisine_type"] == "french"
    assert body["auto_accept"] is True
    assert len(body["opening_hours"]) == 7


def test_auto_accept_defaults_to_true(client: TestClient) -> None:
    payload = {k: v for k, v in RESTAURANT_PAYLOAD.items() if k != "auto_accept"}
    response = client.post("/api/v1/restaurants", json=payload)
    assert response.status_code == 201
    assert response.json()["auto_accept"] is True


def test_read_restaurant_includes_detailed_menu(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    item = create_menu_item(client, restaurant["id"])
    response = client.get(f"/api/v1/restaurants/{restaurant['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == restaurant["id"]
    assert len(body["menu"]) == 1
    assert body["menu"][0]["id"] == item["id"]
    assert body["menu"][0]["options"] == [{"name": "Supplement fromage", "price_delta": 1.5}]


def test_read_unknown_restaurant_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/restaurants/unknown-id")
    assert response.status_code == 404
    assert response.json() == {"detail": "Restaurant not found"}


def test_update_restaurant_replaces_profile_and_hours(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    payload = {
        **RESTAURANT_PAYLOAD,
        "name": "Le Bistrot Renomme",
        "opening_hours": [{"day": 4, "open": "18:00", "close": "23:00"}],
        "auto_accept": False,
    }
    response = client.put(f"/api/v1/restaurants/{restaurant['id']}", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Le Bistrot Renomme"
    assert body["opening_hours"] == [{"day": 4, "open": "18:00", "close": "23:00"}]
    assert body["auto_accept"] is False


def test_update_unknown_restaurant_returns_404(client: TestClient) -> None:
    response = client.put("/api/v1/restaurants/unknown-id", json=RESTAURANT_PAYLOAD)
    assert response.status_code == 404


def test_invalid_opening_hours_are_rejected(client: TestClient) -> None:
    bad_day = {
        **RESTAURANT_PAYLOAD,
        "opening_hours": [{"day": 7, "open": "10:00", "close": "22:00"}],
    }
    assert client.post("/api/v1/restaurants", json=bad_day).status_code == 422

    bad_time = {
        **RESTAURANT_PAYLOAD,
        "opening_hours": [{"day": 0, "open": "25:00", "close": "26:00"}],
    }
    assert client.post("/api/v1/restaurants", json=bad_time).status_code == 422

    open_after_close = {
        **RESTAURANT_PAYLOAD,
        "opening_hours": [{"day": 0, "open": "22:00", "close": "10:00"}],
    }
    assert client.post("/api/v1/restaurants", json=open_after_close).status_code == 422
