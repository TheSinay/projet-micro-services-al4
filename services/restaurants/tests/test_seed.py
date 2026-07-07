"""Tests for the demo catalogue seeded at startup."""

from fastapi.testclient import TestClient


def test_seed_creates_three_restaurants_with_distinct_cuisines(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/restaurants")
    assert response.status_code == 200
    restaurants = response.json()
    assert len(restaurants) == 3
    assert {r["cuisine_type"] for r in restaurants} == {"italian", "japanese", "french"}


def test_seed_menus_have_four_to_six_dishes_with_options(seeded_client: TestClient) -> None:
    restaurants = seeded_client.get("/api/v1/restaurants").json()
    for restaurant in restaurants:
        detail = seeded_client.get(f"/api/v1/restaurants/{restaurant['id']}").json()
        assert 4 <= len(detail["menu"]) <= 6
        assert any(dish["options"] for dish in detail["menu"])


def test_chez_refus_refuses_kitchen_tickets(seeded_client: TestClient) -> None:
    restaurants = seeded_client.get("/api/v1/restaurants?q=refus").json()
    assert len(restaurants) == 1
    chez_refus = restaurants[0]
    assert chez_refus["name"] == "Chez Refus"
    assert chez_refus["auto_accept"] is False
    response = seeded_client.post(
        f"/api/v1/restaurants/{chez_refus['id']}/kitchen-tickets",
        json={
            "order_id": "order-demo",
            "items": [{"menu_item_id": "dish-refus-canard", "quantity": 1}],
        },
    )
    assert response.status_code == 409


def test_seed_is_disabled_for_tests_by_default(client: TestClient) -> None:
    assert client.get("/api/v1/restaurants").json() == []
