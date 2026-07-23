"""Tests for the PLACE_ORDER saga orchestrator (T09) — downstream services faked.

Every scenario goes through the real HTTP checkout (POST /api/v1/orders) with the
three downstream services simulated by ``FakeDownstream`` (httpx.MockTransport):
no real network, no Redis.
"""

from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import (
    PIZZA_ITEM,
    USER_ID,
    FakeDownstream,
    add_item,
    build_client,
    place_order,
)


def _checkout(client: TestClient) -> dict[str, Any]:
    add_item(client, USER_ID, PIZZA_ITEM)
    response = place_order(client)
    assert response.status_code == 201  # the checkout always answers 201 (see README)
    body: dict[str, Any] = response.json()
    return body


def _published(client: TestClient) -> list[tuple[str, dict[str, Any]]]:
    published: list[tuple[str, dict[str, Any]]] = client.app.state.event_bus.published  # type: ignore[attr-defined]
    return published


def _cart_items(client: TestClient) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = client.get(f"/api/v1/carts/{USER_ID}").json()["items"]
    return items


# ---------------------------------------------------------------- nominal path


def test_nominal_saga_confirms_the_order(client: TestClient, downstream: FakeDownstream) -> None:
    body = _checkout(client)
    assert body["status"] == "PREPARING"
    assert body["saga_state"] == "CONFIRMED"
    assert body["payment_id"] == "pay-1"
    assert body["cancellation_reason"] is None
    # Saga sequence: validation -> payment -> kitchen ticket.
    assert downstream.calls == ["validate", "payment", "ticket"]
    # order.confirmed carries the platform envelope and the business payload.
    assert [channel for channel, _ in _published(client)] == ["order.confirmed"]
    _, envelope = _published(client)[0]
    assert envelope["event"] == "order.confirmed"
    assert envelope["data"] == {
        "order_id": body["id"],
        "user_id": USER_ID,
        "restaurant_id": "resto-1",
        "total": body["total"],
    }
    # The cart is emptied only on a confirmed checkout.
    assert _cart_items(client) == []


def test_payment_amount_is_the_order_total(client: TestClient, downstream: FakeDownstream) -> None:
    body = _checkout(client)
    payment_bodies = [payload for label, payload in downstream.bodies if label == "payment"]
    assert payment_bodies == [{"order_id": body["id"], "amount": body["total"]}]


def test_correlation_id_is_propagated_to_downstream_calls(
    client: TestClient, downstream: FakeDownstream
) -> None:
    add_item(client, USER_ID, PIZZA_ITEM)
    response = place_order(client)
    correlation_id = response.headers["X-Correlation-Id"]
    assert len(downstream.requests) == 3
    assert all(
        request.headers.get("X-Correlation-Id") == correlation_id for request in downstream.requests
    )


# --------------------------------------------------------- step 2: validation


def test_invalid_order_is_cancelled_with_reason_and_cart_kept(
    client: TestClient, downstream: FakeDownstream
) -> None:
    downstream.validation_valid = False
    body = _checkout(client)
    assert body["status"] == "CANCELLED"
    assert body["saga_state"] == "CANCELLED_VALIDATION"
    assert "pizza-margherita" in body["cancellation_reason"]
    assert body["payment_id"] is None
    # No payment was ever attempted, nothing to refund.
    assert downstream.calls == ["validate"]
    # order.cancelled is published with the readable reason.
    channel, envelope = _published(client)[0]
    assert channel == "order.cancelled"
    assert envelope["data"]["order_id"] == body["id"]
    assert envelope["data"]["reason"] == body["cancellation_reason"]
    # The client keeps their cart to retry later.
    assert len(_cart_items(client)) == 1


def test_unknown_restaurant_cancels_the_order(
    client: TestClient, downstream: FakeDownstream
) -> None:
    downstream.unknown_restaurant = True
    body = _checkout(client)
    assert body["status"] == "CANCELLED"
    assert body["saga_state"] == "CANCELLED_VALIDATION"
    assert "restaurant inconnu" in body["cancellation_reason"]
    assert downstream.calls == ["validate"]


def test_unreachable_restaurants_service_cancels_after_retries(
    client: TestClient, downstream: FakeDownstream
) -> None:
    downstream.restaurants_down = True
    body = _checkout(client)
    assert body["status"] == "CANCELLED"
    assert body["saga_state"] == "CANCELLED_VALIDATION"
    assert "indisponible" in body["cancellation_reason"]
    assert downstream.calls == ["validate"] * 3  # retried then gave up
    assert len(_cart_items(client)) == 1


# ------------------------------------------------------------ step 3: payment


def test_payment_failure_after_retries_cancels_without_refund(
    client: TestClient, downstream: FakeDownstream
) -> None:
    downstream.payment_fail_always = True
    body = _checkout(client)
    assert body["status"] == "CANCELLED"
    assert body["saga_state"] == "CANCELLED_PAYMENT"
    assert "sans débit" in body["cancellation_reason"]
    assert body["payment_id"] is None
    # 3 retried attempts, then compensation WITHOUT refund (nothing captured).
    assert downstream.calls == ["validate", "payment", "payment", "payment"]
    assert [channel for channel, _ in _published(client)] == ["order.cancelled"]
    # The cart is preserved for a retry.
    assert len(_cart_items(client)) == 1


def test_transient_payment_failure_is_retried_then_succeeds(
    client: TestClient, downstream: FakeDownstream
) -> None:
    downstream.payment_status_queue = [502, 201]
    body = _checkout(client)
    assert body["status"] == "PREPARING"
    assert body["saga_state"] == "CONFIRMED"
    assert downstream.calls == ["validate", "payment", "payment", "ticket"]


def test_open_circuit_fails_fast_without_calling_payments(
    downstream: FakeDownstream,
) -> None:
    downstream.payment_fail_always = True
    # Threshold 3 = the 3 payment attempts of the first order open the circuit.
    with build_client(downstream, breaker_failure_threshold=3) as client:
        first = _checkout(client)
        assert first["saga_state"] == "CANCELLED_PAYMENT"
        assert downstream.calls.count("payment") == 3

        second = _checkout(client)
        assert second["status"] == "CANCELLED"
        assert second["saga_state"] == "CANCELLED_PAYMENT"
        assert "circuit ouvert" in second["cancellation_reason"]
        # Fail fast: no additional network call reached the payments service.
        assert downstream.calls.count("payment") == 3


# ------------------------------------------------- step 4: kitchen ticket


def test_refused_ticket_triggers_total_refund_then_cancellation(
    client: TestClient, downstream: FakeDownstream
) -> None:
    downstream.accept_ticket = False
    body = _checkout(client)
    assert body["status"] == "CANCELLED"
    assert body["saga_state"] == "CANCELLED_REFUSED"
    assert body["cancellation_reason"] == "refusée par le restaurant, remboursement effectué"
    assert body["payment_id"] == "pay-1"
    # Compensation: the refund targets the captured payment, full amount.
    assert downstream.calls == ["validate", "payment", "ticket", "refund"]
    refund_request = downstream.requests[-1]
    assert refund_request.url.path == "/api/v1/payments/pay-1/refunds"
    refund_bodies = [payload for label, payload in downstream.bodies if label == "refund"]
    assert refund_bodies[0]["amount"] == body["total"]
    assert [channel for channel, _ in _published(client)] == ["order.cancelled"]
    assert len(_cart_items(client)) == 1


def test_failed_refund_is_logged_as_debt_with_dedicated_saga_state(
    client: TestClient, downstream: FakeDownstream
) -> None:
    downstream.accept_ticket = False
    downstream.refund_status = 502
    body = _checkout(client)
    assert body["status"] == "CANCELLED"
    assert body["saga_state"] == "REFUND_FAILED"
    assert "intervention manuelle" in body["cancellation_reason"]
    # The refund itself was retried before being recorded as debt.
    assert downstream.calls == ["validate", "payment", "ticket", "refund", "refund", "refund"]
    assert [channel for channel, _ in _published(client)] == ["order.cancelled"]


def test_saga_states_are_persisted_on_the_order(
    client: TestClient, downstream: FakeDownstream
) -> None:
    body = _checkout(client)
    fetched = client.get(f"/api/v1/orders/{body['id']}").json()
    assert fetched["saga_state"] == "CONFIRMED"
    assert fetched["payment_id"] == "pay-1"
