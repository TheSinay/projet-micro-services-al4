"""Tests for the saga continuation (T12): order.ready and delivery.completed handlers.

The handlers are called directly (they are plain async methods of the orchestrator),
with the downstream deliveries/payments services faked through httpx.MockTransport —
exactly how the Redis subscriber invokes them in production, minus Redis.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi.testclient import TestClient

from app.clients import DeliveriesClient, PaymentsClient, RestaurantsClient
from app.events import InMemoryEventBus
from app.repositories.entities import DeliveryAddress, Order, OrderStatus
from app.repositories.memory import InMemoryOrderRepository
from app.services.resilience import CircuitBreaker
from app.services.saga import SagaOrchestrator
from tests.conftest import (
    DELIVERY_ADDRESS,
    PIZZA_ITEM,
    USER_ID,
    FakeDownstream,
    add_item,
    place_order,
)


def _seed_preparing_order(orders: InMemoryOrderRepository) -> Order:
    now = datetime.now(UTC)
    order = Order(
        id=uuid.uuid4().hex,
        user_id=USER_ID,
        restaurant_id="resto-1",
        items=[],
        delivery_address=DeliveryAddress(lat=48.0, lng=2.0),
        subtotal=10.0,
        delivery_fee=2.5,
        total=12.5,
        status=OrderStatus.PREPARING,
        saga_state="CONFIRMED",
        created_at=now,
        updated_at=now,
        payment_id="pay-1",
    )
    orders.add(order)
    return order


ORDER_READY_DATA: dict[str, Any] = {
    "restaurant_id": "resto-1",
    "pickup_address": "3 rue des Rosiers, Paris",
}


def _confirmed_order(client: TestClient) -> str:
    add_item(client, USER_ID, PIZZA_ITEM)
    response = place_order(client, restaurant_lat=48.85, restaurant_lng=2.35)
    body = response.json()
    assert body["status"] == "PREPARING"
    order_id: str = body["id"]
    return order_id


def _order(client: TestClient, order_id: str) -> dict[str, Any]:
    body: dict[str, Any] = client.get(f"/api/v1/orders/{order_id}").json()
    return body


def _published(client: TestClient) -> list[tuple[str, dict[str, Any]]]:
    published: list[tuple[str, dict[str, Any]]] = client.app.state.event_bus.published  # type: ignore[attr-defined]
    return published


# ------------------------------------------------------------------ order.ready


async def test_order_ready_requests_a_delivery_and_moves_to_delivering(
    client: TestClient, downstream: FakeDownstream
) -> None:
    order_id = _confirmed_order(client)
    saga: SagaOrchestrator = client.app.state.saga  # type: ignore[attr-defined]

    await saga.handle_order_ready({"order_id": order_id, **ORDER_READY_DATA})

    body = _order(client, order_id)
    assert body["status"] == "DELIVERING"
    assert body["saga_state"] == "DELIVERING"
    assert body["delivery_id"] == "dlv-1"
    # The delivery request carries the order id, the restaurant pickup point and
    # the client delivery address as dropoff.
    delivery_bodies = [payload for label, payload in downstream.bodies if label == "delivery"]
    assert delivery_bodies == [
        {
            "order_id": order_id,
            # Forwarded so deliveries can echo it in delivery.* events for notifications.
            "user_id": USER_ID,
            "pickup_address": {
                "label": "3 rue des Rosiers, Paris",
                "lat": 48.85,
                "lng": 2.35,
            },
            "dropoff_address": {
                "label": DELIVERY_ADDRESS["label"],
                "lat": DELIVERY_ADDRESS["lat"],
                "lng": DELIVERY_ADDRESS["lng"],
            },
        }
    ]


async def test_order_ready_retries_when_no_courier_then_succeeds(
    client: TestClient, downstream: FakeDownstream
) -> None:
    order_id = _confirmed_order(client)
    downstream.courier_available_on_attempt = 2
    saga: SagaOrchestrator = client.app.state.saga  # type: ignore[attr-defined]

    await saga.handle_order_ready({"order_id": order_id, **ORDER_READY_DATA})

    body = _order(client, order_id)
    assert body["status"] == "DELIVERING"
    assert body["delivery_id"] == "dlv-1"
    assert downstream.calls.count("delivery") == 2  # one 409, then success


async def test_no_courier_at_all_triggers_late_refund_and_cancellation(
    client: TestClient, downstream: FakeDownstream
) -> None:
    order_id = _confirmed_order(client)
    downstream.courier_available_on_attempt = None
    saga: SagaOrchestrator = client.app.state.saga  # type: ignore[attr-defined]

    await saga.handle_order_ready({"order_id": order_id, **ORDER_READY_DATA})

    body = _order(client, order_id)
    assert body["status"] == "CANCELLED"
    assert body["saga_state"] == "CANCELLED_NO_COURIER"
    assert body["cancellation_reason"] == "aucun livreur disponible, remboursement effectué"
    # 3 deferred attempts (configurable), then total refund of the captured payment.
    assert downstream.calls.count("delivery") == 3
    refund_bodies = [payload for label, payload in downstream.bodies if label == "refund"]
    assert refund_bodies[0]["amount"] == body["total"]
    assert [channel for channel, _ in _published(client)] == [
        "order.confirmed",
        "order.cancelled",
    ]


async def test_order_ready_is_ignored_for_unknown_or_non_preparing_orders(
    client: TestClient, downstream: FakeDownstream
) -> None:
    saga: SagaOrchestrator = client.app.state.saga  # type: ignore[attr-defined]
    await saga.handle_order_ready({"order_id": "nope", **ORDER_READY_DATA})
    assert downstream.calls.count("delivery") == 0

    # An order already DELIVERING must not trigger a second assignment.
    order_id = _confirmed_order(client)
    await saga.handle_order_ready({"order_id": order_id, **ORDER_READY_DATA})
    assert downstream.calls.count("delivery") == 1
    await saga.handle_order_ready({"order_id": order_id, **ORDER_READY_DATA})
    assert downstream.calls.count("delivery") == 1  # ignored, no new call


async def test_deferred_retry_uses_the_configured_delay_via_injected_sleep(
    downstream: FakeDownstream,
) -> None:
    # Unit-style wiring: the orchestrator is built directly with a recording sleep.
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    downstream.courier_available_on_attempt = None
    orders = InMemoryOrderRepository()
    async with httpx.AsyncClient(transport=downstream.transport) as http:
        saga = SagaOrchestrator(
            orders=orders,
            event_bus=InMemoryEventBus(),
            restaurants=RestaurantsClient(http, "http://restaurants"),
            payments=PaymentsClient(http, "http://payments"),
            deliveries=DeliveriesClient(http, "http://deliveries"),
            payment_breaker=CircuitBreaker(name="payments"),
            retry_base_delay=0.0,
            delivery_attempts=3,
            delivery_retry_delay=7.5,
            sleep=record_sleep,
        )
        # Seed a PREPARING order with a captured payment directly in the repository.
        order = _seed_preparing_order(orders)

        await saga.handle_order_ready({"order_id": order.id, "pickup_address": None})

    assert delays == [7.5, 7.5]  # deferred delay between the 3 attempts
    assert order.status is OrderStatus.CANCELLED
    assert order.saga_state == "CANCELLED_NO_COURIER"


# ---------------------------------------------------------- delivery.completed


async def test_delivery_completed_moves_the_order_to_delivered(
    client: TestClient, downstream: FakeDownstream
) -> None:
    order_id = _confirmed_order(client)
    saga: SagaOrchestrator = client.app.state.saga  # type: ignore[attr-defined]
    await saga.handle_order_ready({"order_id": order_id, **ORDER_READY_DATA})

    await saga.handle_delivery_completed({"order_id": order_id, "delivery_id": "dlv-1"})

    body = _order(client, order_id)
    assert body["status"] == "DELIVERED"
    assert body["saga_state"] == "DELIVERED"
    channels = [channel for channel, _ in _published(client)]
    assert channels == ["order.confirmed", "order.delivered"]
    _, envelope = _published(client)[-1]
    assert envelope["data"] == {"order_id": order_id, "user_id": USER_ID}


async def test_delivery_completed_is_ignored_unless_delivering(
    client: TestClient, downstream: FakeDownstream
) -> None:
    saga: SagaOrchestrator = client.app.state.saga  # type: ignore[attr-defined]
    await saga.handle_delivery_completed({"order_id": "nope"})  # unknown: no crash

    order_id = _confirmed_order(client)  # PREPARING, not DELIVERING yet
    await saga.handle_delivery_completed({"order_id": order_id})
    assert _order(client, order_id)["status"] == "PREPARING"
