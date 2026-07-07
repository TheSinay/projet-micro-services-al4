"""QA edge cases: distance ties, pool exhaustion, mid-delivery courier patches,
PROPOSED unreachability and idempotence across active statuses."""

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.repositories.entities import DeliveryStatus
from tests.conftest import DELIVERY_PAYLOAD, DROPOFF, create_courier


def _post_delivery(client: TestClient, **overrides: Any) -> Any:
    payload = {**DELIVERY_PAYLOAD, **overrides}
    return client.post("/api/v1/deliveries", json=payload)


def test_distance_tie_is_deterministic_first_created_wins(client: TestClient) -> None:
    """Two couriers at the exact same spot: min() is stable, the first created wins."""
    first_id = create_courier(client, name="First", lat=48.8610, lng=2.3410)
    second_id = create_courier(client, name="Second", lat=48.8610, lng=2.3410)

    response = _post_delivery(client)
    assert response.status_code == 201
    assert response.json()["courier_id"] == first_id
    assert client.get(f"/api/v1/couriers/{second_id}").json()["available"] is True


def test_successive_deliveries_exhaust_the_pool(client: TestClient) -> None:
    """Each assignment consumes one courier; the fleet exhausts to a 409."""
    create_courier(client, name="Marco")
    create_courier(client, name="Lina", lat=48.8462, lng=2.3372)

    assert _post_delivery(client, order_id="order-1").status_code == 201
    assert _post_delivery(client, order_id="order-2").status_code == 201

    third = _post_delivery(client, order_id="order-3")
    assert third.status_code == 409
    assert third.json() == {"detail": "aucun livreur disponible"}


def test_pool_is_replenished_after_a_delivery_completes(client: TestClient) -> None:
    """After DELIVERED the released courier can be assigned to a new order."""
    create_courier(client)
    first = _post_delivery(client, order_id="order-1")
    delivery_id = first.json()["id"]
    assert _post_delivery(client, order_id="order-2").status_code == 409

    client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": "PICKED_UP"})
    client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": "DELIVERED"})

    retry = _post_delivery(client, order_id="order-2")
    assert retry.status_code == 201
    assert retry.json()["courier_id"] == first.json()["courier_id"]


def test_delivered_overrides_mid_delivery_courier_patch(client: TestClient) -> None:
    """A courier patched (availability/location) mid-delivery is still released
    at the dropoff point when the delivery completes, per the T07 contract."""
    courier_id = create_courier(client)
    delivery_id = _post_delivery(client).json()["id"]

    # Dispatcher fiddles with the courier while the delivery is in flight.
    patched = client.patch(
        f"/api/v1/couriers/{courier_id}",
        json={"available": False, "location": {"lat": 40.0, "lng": 3.0}},
    )
    assert patched.status_code == 200

    client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": "PICKED_UP"})
    client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": "DELIVERED"})

    courier = client.get(f"/api/v1/couriers/{courier_id}").json()
    assert courier["available"] is True
    assert courier["location"] == {"lat": DROPOFF["lat"], "lng": DROPOFF["lng"]}


def test_no_transition_is_accepted_from_proposed(client: TestClient, app: FastAPI) -> None:
    """PROPOSED is internal-only (auto-accept): even PROPOSED -> ACCEPTED is
    rejected through the API, so the state is unreachable from outside."""
    create_courier(client)
    delivery_id = _post_delivery(client).json()["id"]

    # Force the persisted state back to PROPOSED (bypassing the auto-accept).
    delivery = app.state.delivery_repository.get_by_id(delivery_id)
    assert delivery is not None
    delivery.status = DeliveryStatus.PROPOSED
    app.state.delivery_repository.update(delivery)

    for target in ("ACCEPTED", "PICKED_UP", "DELIVERED", "PROPOSED"):
        response = client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": target})
        assert response.status_code == 409
        assert response.json() == {"detail": "Invalid delivery status transition"}


def test_repost_is_idempotent_while_delivery_is_picked_up(client: TestClient) -> None:
    """Idempotence holds for every non-DELIVERED status, not just ACCEPTED."""
    create_courier(client)
    delivery_id = _post_delivery(client).json()["id"]
    client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": "PICKED_UP"})

    repost = _post_delivery(client)
    assert repost.status_code == 200
    assert repost.json()["id"] == delivery_id
    assert repost.json()["status"] == "PICKED_UP"
