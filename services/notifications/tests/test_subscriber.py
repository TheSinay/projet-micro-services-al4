"""Tests for the pub/sub consumption loop, driven by a fake client (no Redis)."""

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

import app.subscriber as subscriber_module
from app.repositories.memory import InMemoryNotificationRepository
from app.services.dispatch import NotificationDispatcher
from app.subscriber import SUBSCRIBED_CHANNELS, handle_raw_message, run_subscriber
from tests.conftest import RecordingLogger, make_event


class FakePubSub:
    """In-memory stand-in for ``redis.asyncio.client.PubSub``."""

    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self._messages = messages
        self.subscribed: list[str] = []

    async def subscribe(self, *channels: str) -> None:
        self.subscribed.extend(channels)

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        for message in self._messages:
            yield message


def _message(payload: dict[str, Any]) -> dict[str, Any]:
    return {"type": "message", "data": json.dumps(payload).encode()}


async def test_run_subscriber_subscribes_to_all_platform_channels(
    dispatcher: NotificationDispatcher,
) -> None:
    pubsub = FakePubSub([])
    await run_subscriber(pubsub, dispatcher)
    assert pubsub.subscribed == list(SUBSCRIBED_CHANNELS)
    assert set(pubsub.subscribed) == {
        "order.confirmed",
        "order.cancelled",
        "order.delivered",
        "order.ready",
        "delivery.assigned",
        "delivery.picked_up",
        "delivery.completed",
    }


async def test_run_subscriber_dispatches_messages_and_skips_confirmations(
    dispatcher: NotificationDispatcher,
    repository: InMemoryNotificationRepository,
) -> None:
    envelope = make_event(
        "delivery.picked_up",
        {"order_id": "order-1", "user_id": "user-1"},
        correlation_id="corr-sub",
    )
    pubsub = FakePubSub(
        [
            {"type": "subscribe", "channel": b"delivery.picked_up", "data": 1},
            _message(envelope),
        ]
    )
    await run_subscriber(pubsub, dispatcher)
    stored = repository.list_filtered()
    assert len(stored) == 1
    assert stored[0].event == "delivery.picked_up"
    assert stored[0].recipient_id == "user-1"
    assert stored[0].correlation_id == "corr-sub"


async def test_run_subscriber_survives_invalid_json(
    dispatcher: NotificationDispatcher,
    repository: InMemoryNotificationRepository,
) -> None:
    envelope = make_event("order.delivered", {"order_id": "order-1", "user_id": "user-1"})
    pubsub = FakePubSub(
        [
            {"type": "message", "data": b"{not json"},
            _message(envelope),
        ]
    )
    await run_subscriber(pubsub, dispatcher)
    assert {n.event for n in repository.list_filtered()} == {"order.delivered"}


def test_handle_raw_message_accepts_str_payloads(
    dispatcher: NotificationDispatcher,
    repository: InMemoryNotificationRepository,
) -> None:
    envelope = make_event("delivery.completed", {"order_id": "order-1", "user_id": "user-1"})
    handle_raw_message(json.dumps(envelope), dispatcher)
    assert len(repository.list_filtered()) == 2  # email + push


def test_handle_raw_message_ignores_non_object_json(
    dispatcher: NotificationDispatcher,
    repository: InMemoryNotificationRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = RecordingLogger()
    monkeypatch.setattr(subscriber_module, "logger", fake)
    handle_raw_message(b"[1, 2, 3]", dispatcher)
    handle_raw_message(12, dispatcher)
    assert repository.list_filtered() == []
    assert fake.events("warning") == [
        "invalid_event_payload_ignored",
        "invalid_event_payload_ignored",
    ]
