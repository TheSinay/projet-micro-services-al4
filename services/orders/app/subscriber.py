"""Redis pub/sub subscription driving the saga continuation (T12).

Started by the application lifespan ONLY when ``ORDERS_EVENT_BUS_BACKEND=redis``:
the default in-memory backend keeps the whole test suite hermetic (no Redis).

The subscriber is deliberately thin: it parses the platform envelope
``{"event", "correlation_id", "data"}``, binds the correlation id and dispatches
to the injected handlers. The handlers themselves live on
:class:`app.services.saga.SagaOrchestrator` and are directly callable in tests.
"""

import asyncio
import contextlib
import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Protocol

import structlog

from app.logging import logger

Handler = Callable[[dict[str, Any]], Awaitable[None]]

ORDER_READY_CHANNEL = "order.ready"
DELIVERY_COMPLETED_CHANNEL = "delivery.completed"


class PubSubLike(Protocol):
    """The subset of ``redis.asyncio.client.PubSub`` used by the subscriber."""

    async def subscribe(self, *channels: str) -> None: ...

    def listen(self) -> AsyncIterator[dict[str, Any]]: ...

    async def aclose(self) -> None: ...


class RedisClientLike(Protocol):
    """The subset of ``redis.asyncio.Redis`` used by the subscriber."""

    def pubsub(self) -> PubSubLike: ...

    async def aclose(self) -> None: ...


class RedisSubscriber:
    """Listens on Redis pub/sub channels and dispatches events to async handlers."""

    def __init__(self, client: RedisClientLike, handlers: dict[str, Handler]) -> None:
        self._client = client
        self._handlers = handlers
        self._pubsub: PubSubLike | None = None
        self._task: asyncio.Task[None] | None = None

    @classmethod
    def from_url(cls, url: str, handlers: dict[str, Handler]) -> "RedisSubscriber":
        """Production factory (lazy connection, decoded str payloads)."""
        import redis.asyncio as aioredis

        client = aioredis.Redis.from_url(url, decode_responses=True)
        return cls(client, handlers)

    async def start(self) -> None:
        """Subscribe to every handled channel and start the background listener."""
        self._pubsub = self._client.pubsub()
        await self._pubsub.subscribe(*self._handlers)
        self._task = asyncio.create_task(self._listen(self._pubsub))
        logger.info("subscriber_started", channels=sorted(self._handlers))

    async def stop(self) -> None:
        """Cancel the listener and release the Redis resources."""
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._pubsub is not None:
            await self._pubsub.aclose()
            self._pubsub = None
        await self._client.aclose()
        logger.info("subscriber_stopped")

    async def _listen(self, pubsub: PubSubLike) -> None:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            await self.handle_message(str(message["channel"]), str(message["data"]))

    async def handle_message(self, channel: str, raw: str) -> None:
        """Parse one envelope and dispatch it (directly callable in tests).

        Malformed payloads and handler errors are logged and swallowed: one bad
        event must never kill the subscription loop.
        """
        handler = self._handlers.get(channel)
        if handler is None:
            logger.warning("event_channel_ignored", channel=channel)
            return
        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("event_payload_invalid", channel=channel)
            return
        if not isinstance(envelope, dict):
            logger.warning("event_payload_invalid", channel=channel)
            return
        data = envelope.get("data")
        if not isinstance(data, dict):
            logger.warning("event_payload_invalid", channel=channel)
            return
        correlation_id = str(envelope.get("correlation_id") or uuid.uuid4().hex)
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        try:
            await handler(data)
        except Exception as exc:  # the loop must survive any handler error
            logger.error("event_handler_failed", channel=channel, error=str(exc))
        finally:
            structlog.contextvars.clear_contextvars()
