"""Tests for delivery assignment, idempotence and status transitions."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services.geo import haversine_km
from tests.conftest import DELIVERY_PAYLOAD, DROPOFF, create_courier


def _post_delivery(client: TestClient, **overrides: Any) -> Any:
    payload = {**DELIVERY_PAYLOAD, **overrides}
    return client.post("/api/v1/deliveries", json=payload)


def test_haversine_known_distance() -> None:
    # Paris -> Lyon is roughly 392 km as the crow flies.
    assert haversine_km(48.8566, 2.3522, 45.7640, 4.8357) == pytest.approx(392, abs=5)


def test_assignment_picks_closest_available_courier(client: TestClient) -> None:
    # Pickup is at (48.8600, 2.3400): "near" is a few hundred metres away, "far" several km.
    far_id = create_courier(client, name="Far", lat=48.9500, lng=2.5000)
    near_id = create_courier(client, name="Near", lat=48.8610, lng=2.3410)

    response = _post_delivery(client)
    assert response.status_code == 201
    body = response.json()
    assert body["courier_id"] == near_id
    assert body["status"] == "ACCEPTED"  # prototype: courier auto-accepts immediately
    assert [event["status"] for event in body["events"]] == ["PROPOSED", "ACCEPTED"]

    # The chosen courier is now busy, the other one is untouched.
    assert client.get(f"/api/v1/couriers/{near_id}").json()["available"] is False
    assert client.get(f"/api/v1/couriers/{far_id}").json()["available"] is True


def test_no_courier_available_returns_409(client: TestClient) -> None:
    response = _post_delivery(client)
    assert response.status_code == 409
    assert response.json() == {"detail": "aucun livreur disponible"}


def test_busy_or_unavailable_couriers_are_never_assigned(client: TestClient) -> None:
    create_courier(client, name="OffShift", available=False)
    response = _post_delivery(client)
    assert response.status_code == 409
    assert response.json() == {"detail": "aucun livreur disponible"}


def test_repost_same_order_id_is_idempotent(client: TestClient) -> None:
    create_courier(client)
    first = _post_delivery(client)
    assert first.status_code == 201

    second = _post_delivery(client)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]

    # No new delivery was created for the order.
    listing = client.get("/api/v1/deliveries", params={"order_id": "order-1"})
    assert len(listing.json()) == 1


def test_full_lifecycle_frees_the_courier_at_dropoff(client: TestClient) -> None:
    courier_id = create_courier(client)
    delivery_id = _post_delivery(client).json()["id"]

    picked = client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": "PICKED_UP"})
    assert picked.status_code == 200
    assert picked.json()["status"] == "PICKED_UP"

    delivered = client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": "DELIVERED"})
    assert delivered.status_code == 200
    body = delivered.json()
    assert body["status"] == "DELIVERED"
    assert [event["status"] for event in body["events"]] == [
        "PROPOSED",
        "ACCEPTED",
        "PICKED_UP",
        "DELIVERED",
    ]

    # The courier is available again, positioned at the dropoff point.
    courier = client.get(f"/api/v1/couriers/{courier_id}").json()
    assert courier["available"] is True
    assert courier["location"] == {"lat": DROPOFF["lat"], "lng": DROPOFF["lng"]}


def test_new_delivery_possible_for_same_order_after_delivered(client: TestClient) -> None:
    create_courier(client)
    first_id = _post_delivery(client).json()["id"]
    client.patch(f"/api/v1/deliveries/{first_id}", json={"status": "PICKED_UP"})
    client.patch(f"/api/v1/deliveries/{first_id}", json={"status": "DELIVERED"})

    # The previous delivery is no longer active: a re-POST creates a new one.
    response = _post_delivery(client)
    assert response.status_code == 201
    assert response.json()["id"] != first_id


def test_invalid_transitions_return_409(client: TestClient) -> None:
    create_courier(client)
    delivery_id = _post_delivery(client).json()["id"]

    # ACCEPTED -> DELIVERED skips PICKED_UP.
    response = client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": "DELIVERED"})
    assert response.status_code == 409
    assert response.json() == {"detail": "Invalid delivery status transition"}

    # Going backwards or re-applying the current status is rejected too.
    for target in ("PROPOSED", "ACCEPTED"):
        response = client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": target})
        assert response.status_code == 409

    # A DELIVERED delivery is terminal.
    client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": "PICKED_UP"})
    client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": "DELIVERED"})
    response = client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": "PICKED_UP"})
    assert response.status_code == 409


def test_patch_with_unknown_status_returns_422(client: TestClient) -> None:
    create_courier(client)
    delivery_id = _post_delivery(client).json()["id"]
    response = client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": "FLYING"})
    assert response.status_code == 422


def test_patch_unknown_delivery_returns_404(client: TestClient) -> None:
    response = client.patch("/api/v1/deliveries/unknown", json={"status": "PICKED_UP"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Delivery not found"}


def test_get_delivery_by_id_and_404(client: TestClient) -> None:
    create_courier(client)
    delivery_id = _post_delivery(client).json()["id"]

    response = client.get(f"/api/v1/deliveries/{delivery_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["order_id"] == "order-1"
    assert body["pickup_address"]["label"] == "Chez Momo"
    assert body["created_at"]

    assert client.get("/api/v1/deliveries/unknown").status_code == 404


def test_list_deliveries_filtered_by_order_id(client: TestClient) -> None:
    create_courier(client, name="Marco")
    create_courier(client, name="Lina", lat=48.80, lng=2.30)
    _post_delivery(client, order_id="order-1")
    _post_delivery(client, order_id="order-2")

    all_deliveries = client.get("/api/v1/deliveries").json()
    assert len(all_deliveries) == 2

    filtered = client.get("/api/v1/deliveries", params={"order_id": "order-2"}).json()
    assert len(filtered) == 1
    assert filtered[0]["order_id"] == "order-2"
