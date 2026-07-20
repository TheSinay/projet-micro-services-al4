"""Tests for the event bus implementations and their wiring (no Redis server required)."""

import json

from app.config import Settings
from app.events import InMemoryEventBus, RedisEventBus
from app.main import create_app


class FakeRedisClient:
    """Minimal stand-in for redis.asyncio.Redis capturing published messages."""

    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    async def publish(self, channel: str, message: str) -> int:
        self.published.append((channel, message))
        return 1


async def test_in_memory_bus_records_events() -> None:
    bus = InMemoryEventBus()
    await bus.publish("order.ready", {"event": "order.ready"})
    assert bus.published == [("order.ready", {"event": "order.ready"})]


async def test_redis_bus_publishes_json_payloads() -> None:
    fake = FakeRedisClient()
    bus = RedisEventBus(fake)  # type: ignore[arg-type]
    payload: dict[str, object] = {
        "event": "order.ready",
        "correlation_id": "c1",
        "data": {"order_id": "o1"},
    }
    await bus.publish("order.ready", payload)
    assert len(fake.published) == 1
    channel, message = fake.published[0]
    assert channel == "order.ready"
    assert json.loads(message) == payload


def test_create_app_uses_memory_bus_by_default() -> None:
    app = create_app(Settings(seed_data=False))
    assert isinstance(app.state.event_bus, InMemoryEventBus)


def test_create_app_uses_redis_bus_when_configured() -> None:
    # Connection is lazy: no Redis server is contacted here.
    app = create_app(Settings(seed_data=False, event_bus="redis"))
    assert isinstance(app.state.event_bus, RedisEventBus)
