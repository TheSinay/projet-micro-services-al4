"""Tests for the restaurant search: cuisine, free text (dish or name), distance."""

from fastapi.testclient import TestClient

from tests.conftest import create_menu_item, create_restaurant

PARIS_11 = {"lat": 48.8555, "lng": 2.3730}
PARIS_13 = {"lat": 48.8210, "lng": 2.3652}
LYON = {"lat": 45.7640, "lng": 4.8357}


def _seed_catalogue(client: TestClient) -> dict[str, str]:
    bella = create_restaurant(client, name="La Bella Napoli", cuisine_type="italian", **PARIS_11)
    sakura = create_restaurant(client, name="Sakura Sushi", cuisine_type="japanese", **PARIS_13)
    bouchon = create_restaurant(client, name="Bouchon Lyonnais", cuisine_type="french", **LYON)
    create_menu_item(client, bella["id"], name="Pizza Margherita")
    create_menu_item(client, sakura["id"], name="Ramen tonkotsu")
    create_menu_item(client, bouchon["id"], name="Quenelle de brochet")
    return {"bella": bella["id"], "sakura": sakura["id"], "bouchon": bouchon["id"]}


def _names(client: TestClient, query: str) -> set[str]:
    response = client.get(f"/api/v1/restaurants?{query}")
    assert response.status_code == 200
    return {restaurant["name"] for restaurant in response.json()}


def test_search_without_filters_returns_everything(client: TestClient) -> None:
    _seed_catalogue(client)
    assert _names(client, "") == {"La Bella Napoli", "Sakura Sushi", "Bouchon Lyonnais"}


def test_search_by_cuisine_is_case_insensitive(client: TestClient) -> None:
    _seed_catalogue(client)
    assert _names(client, "cuisine=Italian") == {"La Bella Napoli"}


def test_search_by_text_matches_dish_name(client: TestClient) -> None:
    _seed_catalogue(client)
    assert _names(client, "q=ramen") == {"Sakura Sushi"}


def test_search_by_text_matches_restaurant_name(client: TestClient) -> None:
    _seed_catalogue(client)
    assert _names(client, "q=bella") == {"La Bella Napoli"}


def test_search_by_text_without_match_returns_empty_list(client: TestClient) -> None:
    _seed_catalogue(client)
    assert _names(client, "q=couscous") == set()


def test_search_by_distance_uses_default_radius_of_5km(client: TestClient) -> None:
    _seed_catalogue(client)
    # Paris 11e -> Paris 13e is under 5 km; Lyon is ~390 km away.
    names = _names(client, f"lat={PARIS_11['lat']}&lng={PARIS_11['lng']}")
    assert names == {"La Bella Napoli", "Sakura Sushi"}


def test_search_by_distance_with_small_radius(client: TestClient) -> None:
    _seed_catalogue(client)
    names = _names(client, f"lat={PARIS_11['lat']}&lng={PARIS_11['lng']}&radius_km=2")
    assert names == {"La Bella Napoli"}


def test_search_by_distance_with_large_radius_includes_everything(client: TestClient) -> None:
    _seed_catalogue(client)
    names = _names(client, f"lat={PARIS_11['lat']}&lng={PARIS_11['lng']}&radius_km=500")
    assert names == {"La Bella Napoli", "Sakura Sushi", "Bouchon Lyonnais"}


def test_search_filters_are_combinable(client: TestClient) -> None:
    _seed_catalogue(client)
    query = f"cuisine=japanese&q=ramen&lat={PARIS_11['lat']}&lng={PARIS_11['lng']}&radius_km=10"
    assert _names(client, query) == {"Sakura Sushi"}


def test_search_with_lat_but_no_lng_returns_422(client: TestClient) -> None:
    _seed_catalogue(client)
    response = client.get("/api/v1/restaurants?lat=48.85")
    assert response.status_code == 422
    assert response.json() == {"detail": "lat and lng must be provided together"}
