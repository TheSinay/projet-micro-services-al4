"""Event bus abstraction (Redis pub/sub in production, in-memory in tests).

Convention for payloads on the platform (see plan / ADR 0004):
``{"event": str, "correlation_id": str, "data": {...}}`` on channels such as
``order.confirmed``, ``order.cancelled``, ``order.ready``...

T08 wires the abstraction but publishes nothing yet: the saga orchestrator (T09)
will emit ``order.confirmed`` / ``order.cancelled`` through this bus.
"""

import json
from typing import Any, Protocol

from app.logging import logger


class EventBus(Protocol):
    """Publishing contract used by the business layer."""

    def publish(self, channel: str, payload: dict[str, Any]) -> None: ...


class InMemoryEventBus:
    """Records published events in memory (default backend; used by the tests)."""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, Any]]] = []

    def publish(self, channel: str, payload: dict[str, Any]) -> None:
        self.published.append((channel, payload))
        logger.info("event_published", channel=channel, event_name=payload.get("event"))


class RedisPubSubClient(Protocol):
    """The tiny subset of ``redis.Redis`` used by the event bus."""

    def publish(self, channel: str, message: str, /) -> Any: ...


class RedisEventBus:
    """Publishes JSON events on Redis pub/sub channels (production backend)."""

    def __init__(self, client: RedisPubSubClient) -> None:
        self._client = client

    def publish(self, channel: str, payload: dict[str, Any]) -> None:
        self._client.publish(channel, json.dumps(payload))
        logger.info("event_published", channel=channel, event_name=payload.get("event"))
