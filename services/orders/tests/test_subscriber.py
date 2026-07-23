"""Tests for the Redis pub/sub subscriber (T12) — with a fake Redis client only."""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from app.config import Settings
from app.main import create_app
from app.subscriber import RedisSubscriber


class HandlerRecorder:
    """Async handler that records the payloads it receives."""

    def __init__(self, error: Exception | None = None) -> None:
        self.received: list[dict[str, Any]] = []
        self.error = error

    async def __call__(self, data: dict[str, Any]) -> None:
        self.received.append(data)
        if self.error is not None:
            raise self.error


class FakePubSub:
    """Hermetic stand-in for redis.asyncio PubSub: replays scripted messages."""

    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self.messages = messages
        self.subscribed: list[str] = []
        self.closed = False
        self.drained = asyncio.Event()

    async def subscribe(self, *channels: str) -> None:
        self.subscribed.extend(channels)

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        for message in self.messages:
            yield message
        self.drained.set()
        await asyncio.Event().wait()  # block forever, like a real subscription

    async def aclose(self) -> None:
        self.closed = True


class FakeRedisClient:
    """Hermetic stand-in for redis.asyncio.Redis (pubsub factory + aclose)."""

    def __init__(self, messages: list[dict[str, Any]] | None = None) -> None:
        self.pubsub_instance = FakePubSub(messages or [])
        self.closed = False

    def pubsub(self) -> FakePubSub:
        return self.pubsub_instance

    async def aclose(self) -> None:
        self.closed = True


def _envelope(event: str, data: dict[str, Any], correlation_id: str | None = "corr-1") -> str:
    return json.dumps({"event": event, "correlation_id": correlation_id, "data": data})


async def test_handle_message_dispatches_to_the_right_handler() -> None:
    ready = HandlerRecorder()
    completed = HandlerRecorder()
    subscriber = RedisSubscriber(
        FakeRedisClient(), {"order.ready": ready, "delivery.completed": completed}
    )
    await subscriber.handle_message("order.ready", _envelope("order.ready", {"order_id": "o-1"}))
    assert ready.received == [{"order_id": "o-1"}]
    assert completed.received == []


async def test_handle_message_ignores_unknown_channels() -> None:
    ready = HandlerRecorder()
    subscriber = RedisSubscriber(FakeRedisClient(), {"order.ready": ready})
    await subscriber.handle_message("order.exotic", _envelope("order.exotic", {"order_id": "o-1"}))
    assert ready.received == []


async def test_handle_message_ignores_malformed_payloads() -> None:
    ready = HandlerRecorder()
    subscriber = RedisSubscriber(FakeRedisClient(), {"order.ready": ready})
    await subscriber.handle_message("order.ready", "{not json")
    await subscriber.handle_message("order.ready", json.dumps(["not", "a", "dict"]))
    await subscriber.handle_message("order.ready", json.dumps({"data": "not-a-dict"}))
    assert ready.received == []


async def test_handler_errors_never_kill_the_dispatch() -> None:
    ready = HandlerRecorder(error=RuntimeError("handler exploded"))
    subscriber = RedisSubscriber(FakeRedisClient(), {"order.ready": ready})
    await subscriber.handle_message(
        "order.ready", _envelope("order.ready", {"order_id": "o-1"})
    )  # must not raise
    assert ready.received == [{"order_id": "o-1"}]


async def test_missing_correlation_id_is_tolerated() -> None:
    ready = HandlerRecorder()
    subscriber = RedisSubscriber(FakeRedisClient(), {"order.ready": ready})
    await subscriber.handle_message(
        "order.ready", _envelope("order.ready", {"order_id": "o-1"}, correlation_id=None)
    )
    assert ready.received == [{"order_id": "o-1"}]


async def test_start_listens_dispatches_and_stop_cleans_up() -> None:
    ready = HandlerRecorder()
    client = FakeRedisClient(
        [
            {"type": "subscribe", "channel": "order.ready", "data": 1},
            {
                "type": "message",
                "channel": "order.ready",
                "data": _envelope("order.ready", {"order_id": "o-42"}),
            },
        ]
    )
    subscriber = RedisSubscriber(client, {"order.ready": ready})
    await subscriber.start()
    await asyncio.wait_for(client.pubsub_instance.drained.wait(), timeout=1.0)
    await subscriber.stop()
    assert client.pubsub_instance.subscribed == ["order.ready"]
    assert ready.received == [{"order_id": "o-42"}]  # non-message frames were skipped
    assert client.pubsub_instance.closed
    assert client.closed


def test_app_builds_a_subscriber_only_with_the_redis_backend() -> None:
    # In-memory backend (tests, default): no Redis subscription at all.
    memory_app = create_app(Settings(event_bus_backend="memory"))
    assert memory_app.state.subscriber is None
    # Redis backend: the subscriber exists (lazy connection, started by the lifespan).
    redis_app = create_app(Settings(event_bus_backend="redis"))
    assert isinstance(redis_app.state.subscriber, RedisSubscriber)
