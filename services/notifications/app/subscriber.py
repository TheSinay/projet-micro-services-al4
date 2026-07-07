"""Redis pub/sub consumption loop (production transport).

The loop is deliberately transport-thin: every business decision lives in
``NotificationDispatcher.handle_event`` (pure with respect to Redis). The loop
itself only depends on the tiny ``PubSubClient`` Protocol, so tests drive it
with a fake client — no Redis is ever required.
"""

import json
from collections.abc import AsyncIterator
from typing import Any, Protocol

from app.logging import logger
from app.services.dispatch import NotificationDispatcher

SUBSCRIBED_CHANNELS: tuple[str, ...] = (
    "order.confirmed",
    "order.cancelled",
    "order.delivered",
    "order.ready",
    "delivery.assigned",
    "delivery.picked_up",
    "delivery.completed",
)


class PubSubClient(Protocol):
    """The tiny subset of ``redis.asyncio.client.PubSub`` used by the loop."""

    async def subscribe(self, *channels: str) -> None: ...

    def listen(self) -> AsyncIterator[dict[str, Any]]: ...


def handle_raw_message(raw: object, dispatcher: NotificationDispatcher) -> None:
    """Decode one pub/sub message body and hand it to the dispatcher.

    Malformed messages (invalid JSON, non-object payloads) are logged and
    dropped: a broken producer must never crash the consumer loop.
    """
    if isinstance(raw, bytes | bytearray):
        raw = raw.decode("utf-8", errors="replace")
    payload: Any = None
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None
    if not isinstance(payload, dict):
        logger.warning("invalid_event_payload_ignored", raw=str(raw)[:200])
        return
    dispatcher.handle_event(payload)


async def run_subscriber(pubsub: PubSubClient, dispatcher: NotificationDispatcher) -> None:
    """Consume event messages until cancelled (task started in the app lifespan)."""
    await pubsub.subscribe(*SUBSCRIBED_CHANNELS)
    logger.info("subscriber_started", channels=list(SUBSCRIBED_CHANNELS))
    async for message in pubsub.listen():
        # Redis interleaves subscription confirmations with actual messages.
        if message.get("type") != "message":
            continue
        handle_raw_message(message.get("data"), dispatcher)
