"""Tests for the strict order state machine (PATCH /orders/{id}/status).

Orders are seeded directly in the repository in ``RECEIVED``: since T09 a checkout
runs the saga and lands in ``PREPARING`` (nominal), so the exhaustive transition
matrix from ``RECEIVED`` can only be exercised on a saga-free order.
"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.repositories.entities import DeliveryAddress, Order, OrderStatus
from tests.conftest import USER_ID


def _create_order(client: TestClient) -> str:
    now = datetime.now(UTC)
    order = Order(
        id=uuid.uuid4().hex,
        user_id=USER_ID,
        restaurant_id="resto-1",
        items=[],
        delivery_address=DeliveryAddress(lat=48.8698, lng=2.3311),
        subtotal=10.0,
        delivery_fee=2.5,
        total=12.5,
        status=OrderStatus.RECEIVED,
        saga_state="PENDING",
        created_at=now,
        updated_at=now,
    )
    client.app.state.order_repository.add(order)  # type: ignore[attr-defined]
    return order.id


def _patch_status(client: TestClient, order_id: str, status: str) -> int:
    response = client.patch(f"/api/v1/orders/{order_id}/status", json={"status": status})
    return int(response.status_code)


def test_full_legal_lifecycle(client: TestClient) -> None:
    order_id = _create_order(client)
    for status in ("PREPARING", "DELIVERING", "DELIVERED"):
        response = client.patch(f"/api/v1/orders/{order_id}/status", json={"status": status})
        assert response.status_code == 200
        assert response.json()["status"] == status


@pytest.mark.parametrize("status", ["CANCELLED", "PREPARING"])
def test_cancellation_is_allowed_from_received_and_preparing(
    client: TestClient, status: str
) -> None:
    order_id = _create_order(client)
    if status == "PREPARING":
        assert _patch_status(client, order_id, "PREPARING") == 200
    assert _patch_status(client, order_id, "CANCELLED") == 200


def test_skipping_a_step_is_rejected(client: TestClient) -> None:
    order_id = _create_order(client)
    assert _patch_status(client, order_id, "DELIVERING") == 409
    assert _patch_status(client, order_id, "DELIVERED") == 409


def test_cancellation_is_forbidden_once_delivering(client: TestClient) -> None:
    order_id = _create_order(client)
    assert _patch_status(client, order_id, "PREPARING") == 200
    assert _patch_status(client, order_id, "DELIVERING") == 200
    response = client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "CANCELLED"})
    assert response.status_code == 409
    assert "DELIVERING -> CANCELLED" in response.json()["detail"]


def test_terminal_states_accept_no_transition(client: TestClient) -> None:
    order_id = _create_order(client)
    assert _patch_status(client, order_id, "CANCELLED") == 200
    assert _patch_status(client, order_id, "PREPARING") == 409

    other_id = _create_order(client)
    for status in ("PREPARING", "DELIVERING", "DELIVERED"):
        assert _patch_status(client, other_id, status) == 200
    assert _patch_status(client, other_id, "DELIVERING") == 409


def test_transition_to_same_status_is_rejected(client: TestClient) -> None:
    order_id = _create_order(client)
    assert _patch_status(client, order_id, "RECEIVED") == 409


def test_unknown_status_value_is_rejected(client: TestClient) -> None:
    order_id = _create_order(client)
    assert _patch_status(client, order_id, "TELEPORTED") == 422


def test_transition_on_unknown_order_returns_404(client: TestClient) -> None:
    assert _patch_status(client, "nope", "PREPARING") == 404


def test_transition_updates_updated_at(client: TestClient) -> None:
    order_id = _create_order(client)
    before = client.get(f"/api/v1/orders/{order_id}").json()
    response = client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "PREPARING"})
    after = response.json()
    assert after["updated_at"] >= before["updated_at"]
    assert after["created_at"] == before["created_at"]
