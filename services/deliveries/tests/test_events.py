"""Tests for event publication (in-memory bus) and the Redis bus serialization."""

import json
from typing import Any

from fastapi.testclient import TestClient

from app.events import InMemoryEventBus, RedisEventBus, build_payload
from tests.conftest import DELIVERY_PAYLOAD, create_courier


def _events_by_channel(bus: InMemoryEventBus) -> dict[str, dict[str, Any]]:
    return dict(bus.published)


def test_assignment_publishes_proposed_then_assigned(
    client: TestClient, event_bus: InMemoryEventBus
) -> None:
    courier_id = create_courier(client, name="Marco")
    response = client.post(
        "/api/v1/deliveries", json=DELIVERY_PAYLOAD, headers={"X-Correlation-Id": "corr-42"}
    )
    delivery_id = response.json()["id"]

    channels = [channel for channel, _ in event_bus.published]
    assert channels == ["delivery.proposed", "delivery.assigned"]

    assigned = _events_by_channel(event_bus)["delivery.assigned"]
    assert assigned == {
        "event": "delivery.assigned",
        "correlation_id": "corr-42",
        "data": {
            "order_id": "order-1",
            "delivery_id": delivery_id,
            "courier_id": courier_id,
            "courier_name": "Marco",
        },
    }


def test_picked_up_and_completed_events(client: TestClient, event_bus: InMemoryEventBus) -> None:
    courier_id = create_courier(client)
    delivery_id = client.post("/api/v1/deliveries", json=DELIVERY_PAYLOAD).json()["id"]

    client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": "PICKED_UP"})
    client.patch(f"/api/v1/deliveries/{delivery_id}", json={"status": "DELIVERED"})

    events = _events_by_channel(event_bus)
    assert events["delivery.picked_up"]["data"] == {
        "order_id": "order-1",
        "delivery_id": delivery_id,
        "courier_id": courier_id,
    }
    assert events["delivery.completed"]["data"] == {
        "order_id": "order-1",
        "delivery_id": delivery_id,
    }
    # Every payload carries the platform envelope.
    for payload in events.values():
        assert set(payload) == {"event", "correlation_id", "data"}


def test_no_event_published_on_failed_assignment(
    client: TestClient, event_bus: InMemoryEventBus
) -> None:
    response = client.post("/api/v1/deliveries", json=DELIVERY_PAYLOAD)
    assert response.status_code == 409
    assert event_bus.published == []


def test_build_payload_without_request_context_has_no_correlation_id() -> None:
    payload = build_payload("delivery.assigned", {"order_id": "o-1"})
    assert payload == {
        "event": "delivery.assigned",
        "correlation_id": None,
        "data": {"order_id": "o-1"},
    }


class _StubRedisClient:
    """Minimal async stand-in for redis.asyncio.Redis (no server involved)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def publish(self, channel: str, message: str) -> int:
        self.calls.append((channel, message))
        return 1


async def test_redis_event_bus_publishes_json_payload() -> None:
    bus = RedisEventBus("redis://localhost:6379/0")  # lazy: nothing is connected
    stub = _StubRedisClient()
    bus._client = stub  # type: ignore[assignment]

    payload = {"event": "delivery.completed", "correlation_id": "corr-1", "data": {"a": 1}}
    await bus.publish("delivery.completed", payload)

    assert stub.calls == [("delivery.completed", json.dumps(payload))]
