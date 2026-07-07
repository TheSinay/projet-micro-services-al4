"""Tests for kitchen tickets: acceptance/refusal, strict transitions, order.ready event."""

from typing import Any

from fastapi.testclient import TestClient

from app.events import InMemoryEventBus
from tests.conftest import create_restaurant

TICKET_PAYLOAD: dict[str, object] = {
    "order_id": "order-123",
    "items": [{"menu_item_id": "dish-1", "quantity": 2}],
}


def _create_ticket(client: TestClient, restaurant_id: str) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/restaurants/{restaurant_id}/kitchen-tickets", json=TICKET_PAYLOAD
    )
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body


def _patch_status(client: TestClient, ticket_id: str, new_status: str) -> Any:
    return client.patch(f"/api/v1/kitchen-tickets/{ticket_id}", json={"status": new_status})


def test_ticket_is_accepted_when_auto_accept_is_on(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    body = _create_ticket(client, restaurant["id"])
    assert body["status"] == "ACCEPTED"
    assert body["order_id"] == "order-123"
    assert body["restaurant_id"] == restaurant["id"]
    assert body["items"] == [{"menu_item_id": "dish-1", "quantity": 2}]
    assert body["created_at"]


def test_ticket_is_refused_when_auto_accept_is_off(client: TestClient) -> None:
    restaurant = create_restaurant(client, name="Chez Refus", auto_accept=False)
    response = client.post(
        f"/api/v1/restaurants/{restaurant['id']}/kitchen-tickets", json=TICKET_PAYLOAD
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "commande refusée par le restaurant"}


def test_ticket_for_unknown_restaurant_returns_404(client: TestClient) -> None:
    response = client.post("/api/v1/restaurants/unknown-id/kitchen-tickets", json=TICKET_PAYLOAD)
    assert response.status_code == 404


def test_nominal_transitions_accepted_preparing_ready(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    ticket = _create_ticket(client, restaurant["id"])
    response = _patch_status(client, ticket["id"], "PREPARING")
    assert response.status_code == 200
    assert response.json()["status"] == "PREPARING"
    response = _patch_status(client, ticket["id"], "READY")
    assert response.status_code == 200
    assert response.json()["status"] == "READY"


def test_invalid_transitions_return_409(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    ticket = _create_ticket(client, restaurant["id"])
    # ACCEPTED -> READY skips PREPARING.
    assert _patch_status(client, ticket["id"], "READY").status_code == 409
    assert _patch_status(client, ticket["id"], "PREPARING").status_code == 200
    # PREPARING -> ACCEPTED goes backwards.
    assert _patch_status(client, ticket["id"], "ACCEPTED").status_code == 409
    assert _patch_status(client, ticket["id"], "READY").status_code == 200
    # READY is terminal.
    assert _patch_status(client, ticket["id"], "PREPARING").status_code == 409


def test_unknown_status_value_returns_422(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    ticket = _create_ticket(client, restaurant["id"])
    assert _patch_status(client, ticket["id"], "BURNED").status_code == 422


def test_patch_unknown_ticket_returns_404(client: TestClient) -> None:
    response = _patch_status(client, "unknown-id", "PREPARING")
    assert response.status_code == 404
    assert response.json() == {"detail": "Kitchen ticket not found"}


def test_ready_publishes_order_ready_event(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    ticket = _create_ticket(client, restaurant["id"])
    _patch_status(client, ticket["id"], "PREPARING")
    response = client.patch(
        f"/api/v1/kitchen-tickets/{ticket['id']}",
        json={"status": "READY"},
        headers={"X-Correlation-Id": "corr-ready-42"},
    )
    assert response.status_code == 200

    bus = client.app.state.event_bus  # type: ignore[attr-defined]
    assert isinstance(bus, InMemoryEventBus)
    assert len(bus.published) == 1
    channel, payload = bus.published[0]
    assert channel == "order.ready"
    assert payload["event"] == "order.ready"
    assert payload["correlation_id"] == "corr-ready-42"
    assert payload["data"] == {
        "order_id": "order-123",
        "restaurant_id": restaurant["id"],
        "pickup_address": restaurant["address"],
    }


def test_no_event_is_published_before_ready(client: TestClient) -> None:
    restaurant = create_restaurant(client)
    ticket = _create_ticket(client, restaurant["id"])
    _patch_status(client, ticket["id"], "PREPARING")
    bus = client.app.state.event_bus  # type: ignore[attr-defined]
    assert isinstance(bus, InMemoryEventBus)
    assert bus.published == []
