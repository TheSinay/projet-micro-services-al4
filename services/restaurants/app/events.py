"""Event bus abstraction (Redis pub/sub in production, in-memory recorder in tests).

Domain events follow the shared envelope::

    {"event": "<channel>", "correlation_id": "<id>", "data": {...}}

The concrete implementation is chosen in ``create_app`` from ``Settings.event_bus``
and stored on ``app.state.event_bus``; no test ever requires a running Redis.
"""

import json
from typing import Protocol

import redis.asyncio as aioredis


class EventBus(Protocol):
    """Publishing contract used by the business layer."""

    async def publish(self, channel: str, payload: dict[str, object]) -> None: ...


class InMemoryEventBus:
    """Records published events in memory — used by the test suite to assert on them."""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, object]]] = []

    async def publish(self, channel: str, payload: dict[str, object]) -> None:
        self.published.append((channel, payload))


class RedisEventBus:
    """Publishes JSON payloads on Redis pub/sub channels (production implementation)."""

    def __init__(self, client: aioredis.Redis) -> None:
        self._client = client

    @classmethod
    def from_url(cls, url: str) -> "RedisEventBus":
        """Build a bus from a Redis URL; the connection is established lazily."""
        return cls(aioredis.Redis.from_url(url))

    async def publish(self, channel: str, payload: dict[str, object]) -> None:
        await self._client.publish(channel, json.dumps(payload))
