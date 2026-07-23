"""Tests for the EventBus abstraction (in-memory and Redis-backed, with a fake client)."""

import json
from typing import Any

from app.events import InMemoryEventBus, RedisEventBus


class FakePubSubClient:
    """Hermetic stand-in for redis.Redis.publish (no running Redis required)."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def publish(self, channel: str, message: str, /) -> int:
        self.messages.append((channel, message))
        return 1


def _payload() -> dict[str, Any]:
    return {"event": "order.confirmed", "correlation_id": "corr-1", "data": {"order_id": "o-1"}}


def test_in_memory_event_bus_records_events() -> None:
    bus = InMemoryEventBus()
    bus.publish("order.confirmed", _payload())
    assert bus.published == [("order.confirmed", _payload())]


def test_redis_event_bus_publishes_json() -> None:
    client = FakePubSubClient()
    bus = RedisEventBus(client)
    bus.publish("order.confirmed", _payload())
    assert len(client.messages) == 1
    channel, message = client.messages[0]
    assert channel == "order.confirmed"
    assert json.loads(message) == _payload()
