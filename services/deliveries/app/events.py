"""Event bus abstraction: Redis pub/sub in production, in-memory recorder in tests.

Every payload follows the platform envelope::

    {"event": "<channel>", "correlation_id": "<id>", "data": {...}}

The correlation id is taken from the structlog contextvars bound by the
``CorrelationIdMiddleware``, so published events can be traced back to the
originating HTTP request.
"""

import json
from typing import Any, Protocol

import redis.asyncio as aioredis
import structlog


def build_payload(channel: str, data: dict[str, Any]) -> dict[str, Any]:
    """Wrap event data in the platform envelope ``{event, correlation_id, data}``."""
    correlation_id = structlog.contextvars.get_contextvars().get("correlation_id")
    return {"event": channel, "correlation_id": correlation_id, "data": data}


class EventBus(Protocol):
    """Publishing contract — business logic never depends on a concrete broker."""

    async def publish(self, channel: str, payload: dict[str, Any]) -> None: ...


class InMemoryEventBus:
    """Records published events so tests can assert on them (no broker required)."""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, Any]]] = []

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        self.published.append((channel, payload))


class RedisEventBus:
    """Publishes JSON events on Redis pub/sub channels (production backend)."""

    def __init__(self, redis_url: str) -> None:
        # The connection is lazy: nothing is established until the first publish.
        self._client: aioredis.Redis = aioredis.Redis.from_url(redis_url)

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        await self._client.publish(channel, json.dumps(payload))
