"""Tests for courier CRUD, availability and simulated location updates."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import create_courier, make_courier_payload


def test_create_courier_returns_201_with_body(client: TestClient) -> None:
    response = client.post("/api/v1/couriers", json=make_courier_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["name"] == "Marco Rossi"
    assert body["available"] is True
    assert body["location"] == {"lat": 48.8867, "lng": 2.3431}


def test_create_courier_rejects_invalid_latitude(client: TestClient) -> None:
    response = client.post("/api/v1/couriers", json=make_courier_payload(lat=95.0))
    assert response.status_code == 422


def test_list_couriers(client: TestClient) -> None:
    create_courier(client, name="Marco")
    create_courier(client, name="Lina")
    response = client.get("/api/v1/couriers")
    assert response.status_code == 200
    assert {courier["name"] for courier in response.json()} == {"Marco", "Lina"}


def test_get_courier_by_id(client: TestClient) -> None:
    courier_id = create_courier(client)
    response = client.get(f"/api/v1/couriers/{courier_id}")
    assert response.status_code == 200
    assert response.json()["id"] == courier_id


def test_get_unknown_courier_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/couriers/unknown")
    assert response.status_code == 404
    assert response.json() == {"detail": "Courier not found"}


def test_patch_courier_availability(client: TestClient) -> None:
    courier_id = create_courier(client)
    response = client.patch(f"/api/v1/couriers/{courier_id}", json={"available": False})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    # The location must be untouched by a pure availability patch.
    assert body["location"] == {"lat": 48.8867, "lng": 2.3431}


def test_patch_courier_location(client: TestClient) -> None:
    courier_id = create_courier(client)
    response = client.patch(
        f"/api/v1/couriers/{courier_id}",
        json={"location": {"lat": 48.8300, "lng": 2.3100}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["location"] == {"lat": 48.8300, "lng": 2.3100}
    assert body["available"] is True


def test_patch_courier_availability_and_location_together(client: TestClient) -> None:
    courier_id = create_courier(client)
    response = client.patch(
        f"/api/v1/couriers/{courier_id}",
        json={"available": False, "location": {"lat": 48.0, "lng": 2.0}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["location"] == {"lat": 48.0, "lng": 2.0}


def test_patch_unknown_courier_returns_404(client: TestClient) -> None:
    response = client.patch("/api/v1/couriers/unknown", json={"available": True})
    assert response.status_code == 404


def test_seed_populates_four_available_couriers() -> None:
    app = create_app(Settings(event_backend="memory", seed_data=True))
    with TestClient(app) as client:
        response = client.get("/api/v1/couriers")
    assert response.status_code == 200
    couriers = response.json()
    assert len(couriers) == 4
    # The demo fleet is seeded fully available so the assignment flow can run
    # immediately after startup (see seed.py).
    assert all(courier["available"] for courier in couriers)
    locations = {(courier["location"]["lat"], courier["location"]["lng"]) for courier in couriers}
    assert len(locations) == 4  # all seeded at different positions
