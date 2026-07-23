"""Tests for the declarative event -> notification routing rules."""

from typing import Any

import pytest

import app.services.dispatch as dispatch_module
from app.repositories.entities import Channel, RecipientType
from app.repositories.memory import InMemoryNotificationRepository
from app.services.dispatch import NotificationDispatcher
from tests.conftest import RecordingLogger, make_event

FULL_ORDER_DATA: dict[str, Any] = {
    "order_id": "order-1",
    "user_id": "user-1",
    "restaurant_id": "resto-1",
}


@pytest.fixture
def recording_logger(monkeypatch: pytest.MonkeyPatch) -> RecordingLogger:
    """Replace the dispatch module logger with a deterministic recorder."""
    fake = RecordingLogger()
    monkeypatch.setattr(dispatch_module, "logger", fake)
    return fake


def _routing(notifications: list[Any]) -> set[tuple[RecipientType, str, Channel, str]]:
    return {(n.recipient_type, n.recipient_id, n.channel, n.subject) for n in notifications}


def test_order_confirmed_notifies_client_and_restaurant(
    dispatcher: NotificationDispatcher,
) -> None:
    created = dispatcher.handle_event(make_event("order.confirmed", FULL_ORDER_DATA))
    assert _routing(created) == {
        (RecipientType.CLIENT, "user-1", Channel.EMAIL, "Votre commande est confirmée"),
        (RecipientType.CLIENT, "user-1", Channel.PUSH, "Votre commande est confirmée"),
        (RecipientType.RESTAURANT, "resto-1", Channel.PUSH, "Nouvelle commande à préparer"),
    }


def test_order_cancelled_notifies_client_with_reason_and_refund(
    dispatcher: NotificationDispatcher,
) -> None:
    data = {
        "order_id": "order-1",
        "user_id": "user-1",
        "reason": "paiement refusé",
        "refund_amount": 25.5,
    }
    created = dispatcher.handle_event(make_event("order.cancelled", data))
    assert _routing(created) == {
        (RecipientType.CLIENT, "user-1", Channel.EMAIL, "Votre commande est annulée"),
        (RecipientType.CLIENT, "user-1", Channel.PUSH, "Votre commande est annulée"),
    }
    for notification in created:
        assert "paiement refusé" in notification.body
        assert "remboursement de 25.5 €" in notification.body


def test_order_cancelled_body_mentions_refund_without_amount(
    dispatcher: NotificationDispatcher,
) -> None:
    data = {"order_id": "order-1", "user_id": "user-1", "refunded": True}
    created = dispatcher.handle_event(make_event("order.cancelled", data))
    assert created
    for notification in created:
        assert "raison non précisée" in notification.body
        assert "Un remboursement a été effectué." in notification.body


def test_order_ready_is_silently_ignored_with_debug_log(
    dispatcher: NotificationDispatcher,
    repository: InMemoryNotificationRepository,
    recording_logger: RecordingLogger,
) -> None:
    created = dispatcher.handle_event(make_event("order.ready", FULL_ORDER_DATA))
    assert created == []
    assert repository.list_filtered() == []
    assert recording_logger.events("debug") == ["technical_event_ignored"]
    assert recording_logger.events("warning") == []


def test_delivery_assigned_notifies_client_and_courier(
    dispatcher: NotificationDispatcher,
) -> None:
    data = {
        "order_id": "order-1",
        "user_id": "user-1",
        "courier_id": "courier-1",
        "courier_name": "Marco",
    }
    created = dispatcher.handle_event(make_event("delivery.assigned", data))
    assert _routing(created) == {
        (
            RecipientType.CLIENT,
            "user-1",
            Channel.PUSH,
            "Votre livreur est en route vers le restaurant",
        ),
        (RecipientType.COURIER, "courier-1", Channel.PUSH, "Nouvelle course assignée"),
    }
    client_body = next(n.body for n in created if n.recipient_type is RecipientType.CLIENT)
    assert "Marco" in client_body


def test_delivery_picked_up_notifies_client_only(dispatcher: NotificationDispatcher) -> None:
    data = {"order_id": "order-1", "user_id": "user-1", "courier_id": "courier-1"}
    created = dispatcher.handle_event(make_event("delivery.picked_up", data))
    assert _routing(created) == {
        (RecipientType.CLIENT, "user-1", Channel.PUSH, "Votre commande est en route"),
    }


# Regression: the deliveries service now forwards ``user_id`` in its delivery.* events
# (previously absent -> "livreur en route" / "commande en route" notifications were lost).
# These tests pin the exact production payload shapes emitted by deliveries.
def test_delivery_assigned_production_payload_reaches_client(
    dispatcher: NotificationDispatcher,
) -> None:
    deliveries_payload = {
        "order_id": "order-1",
        "delivery_id": "dlv-1",
        "courier_id": "courier-1",
        "courier_name": "Marco",
        "user_id": "user-1",
    }
    created = dispatcher.handle_event(make_event("delivery.assigned", deliveries_payload))
    client_notifs = [n for n in created if n.recipient_type is RecipientType.CLIENT]
    assert [n.recipient_id for n in client_notifs] == ["user-1"]


def test_delivery_picked_up_production_payload_reaches_client(
    dispatcher: NotificationDispatcher,
) -> None:
    deliveries_payload = {
        "order_id": "order-1",
        "delivery_id": "dlv-1",
        "courier_id": "courier-1",
        "user_id": "user-1",
    }
    created = dispatcher.handle_event(make_event("delivery.picked_up", deliveries_payload))
    assert _routing(created) == {
        (RecipientType.CLIENT, "user-1", Channel.PUSH, "Votre commande est en route"),
    }


def test_delivery_assigned_without_user_id_only_notifies_courier(
    dispatcher: NotificationDispatcher,
) -> None:
    # Legacy / degraded payload (no user_id): the courier is still notified, the client
    # notification is skipped (recipient_missing_in_payload warning) rather than crashing.
    data = {"order_id": "order-1", "delivery_id": "dlv-1", "courier_id": "courier-1"}
    created = dispatcher.handle_event(make_event("delivery.assigned", data))
    assert _routing(created) == {
        (RecipientType.COURIER, "courier-1", Channel.PUSH, "Nouvelle course assignée"),
    }


@pytest.mark.parametrize("event", ["delivery.completed", "order.delivered"])
def test_delivered_events_wish_bon_appetit(dispatcher: NotificationDispatcher, event: str) -> None:
    created = dispatcher.handle_event(make_event(event, {"order_id": "order-1", "user_id": "u1"}))
    assert _routing(created) == {
        (RecipientType.CLIENT, "u1", Channel.EMAIL, "Bon appétit !"),
        (RecipientType.CLIENT, "u1", Channel.PUSH, "Bon appétit !"),
    }
    assert all("Bon appétit" in n.body for n in created)


def test_unknown_event_is_ignored_without_crash(
    dispatcher: NotificationDispatcher,
    repository: InMemoryNotificationRepository,
    recording_logger: RecordingLogger,
) -> None:
    created = dispatcher.handle_event(make_event("order.exploded", FULL_ORDER_DATA))
    assert created == []
    assert repository.list_filtered() == []
    assert recording_logger.events("warning") == ["unknown_event_ignored"]


def test_envelope_without_event_key_is_ignored(
    dispatcher: NotificationDispatcher, recording_logger: RecordingLogger
) -> None:
    assert dispatcher.handle_event({"data": {"user_id": "user-1"}}) == []
    assert recording_logger.events("warning") == ["unknown_event_ignored"]


def test_missing_recipient_id_yields_partial_notifications_and_warning(
    dispatcher: NotificationDispatcher, recording_logger: RecordingLogger
) -> None:
    # delivery.assigned without user_id: only the courier can be notified.
    data = {"order_id": "order-1", "courier_id": "courier-1"}
    created = dispatcher.handle_event(make_event("delivery.assigned", data))
    assert _routing(created) == {
        (RecipientType.COURIER, "courier-1", Channel.PUSH, "Nouvelle course assignée"),
    }
    warnings = [entry for entry in recording_logger.entries if entry[0] == "warning"]
    assert len(warnings) == 1
    _, event_name, kwargs = warnings[0]
    assert event_name == "recipient_missing_in_payload"
    assert kwargs["expected_key"] == "user_id"
    assert kwargs["recipient_type"] is RecipientType.CLIENT


def test_order_cancelled_body_without_refund_does_not_mention_refund(
    dispatcher: NotificationDispatcher,
) -> None:
    data = {"order_id": "order-1", "user_id": "user-1", "reason": "restaurant fermé"}
    created = dispatcher.handle_event(make_event("order.cancelled", data))
    assert created
    for notification in created:
        assert "restaurant fermé" in notification.body
        assert "remboursement" not in notification.body.lower()


def test_non_string_event_field_is_ignored_without_crash(
    dispatcher: NotificationDispatcher,
    repository: InMemoryNotificationRepository,
    recording_logger: RecordingLogger,
) -> None:
    created = dispatcher.handle_event({"event": 123, "data": FULL_ORDER_DATA})
    assert created == []
    assert repository.list_filtered() == []
    assert recording_logger.events("warning") == ["unknown_event_ignored"]


def test_non_dict_data_field_yields_only_missing_recipient_warnings(
    dispatcher: NotificationDispatcher,
    repository: InMemoryNotificationRepository,
    recording_logger: RecordingLogger,
) -> None:
    created = dispatcher.handle_event({"event": "order.confirmed", "data": ["not", "a", "dict"]})
    assert created == []
    assert repository.list_filtered() == []
    # One warning per recipient rule (client + restaurant), no exception raised.
    assert recording_logger.events("warning") == [
        "recipient_missing_in_payload",
        "recipient_missing_in_payload",
    ]


def test_two_successive_events_for_same_order_create_distinct_notifications(
    dispatcher: NotificationDispatcher,
    repository: InMemoryNotificationRepository,
) -> None:
    first = dispatcher.handle_event(make_event("order.confirmed", FULL_ORDER_DATA))
    second = dispatcher.handle_event(make_event("order.confirmed", FULL_ORDER_DATA))
    assert len(first) == 3 and len(second) == 3
    all_ids = [n.id for n in first + second]
    assert len(set(all_ids)) == 6  # every notification has its own identity
    assert len(repository.list_filtered()) == 6


def test_correlation_id_is_propagated_to_notifications(
    dispatcher: NotificationDispatcher,
) -> None:
    created = dispatcher.handle_event(
        make_event("order.confirmed", FULL_ORDER_DATA, correlation_id="corr-42")
    )
    assert created
    assert all(n.correlation_id == "corr-42" for n in created)


def test_missing_correlation_id_is_stored_as_none(dispatcher: NotificationDispatcher) -> None:
    created = dispatcher.handle_event(
        make_event("order.confirmed", FULL_ORDER_DATA, correlation_id=None)
    )
    assert created
    assert all(n.correlation_id is None for n in created)


def test_non_string_recipient_id_is_coerced(dispatcher: NotificationDispatcher) -> None:
    created = dispatcher.handle_event(
        make_event("delivery.picked_up", {"order_id": "order-1", "user_id": 42})
    )
    assert [n.recipient_id for n in created] == ["42"]


def test_simulated_send_logs_channel_recipient_and_subject(
    dispatcher: NotificationDispatcher, recording_logger: RecordingLogger
) -> None:
    dispatcher.handle_event(make_event("delivery.picked_up", {"user_id": "user-1"}))
    sends = [entry for entry in recording_logger.entries if entry[1] == "notification_sent"]
    assert len(sends) == 1
    level, _, kwargs = sends[0]
    assert level == "info"
    assert kwargs == {
        "channel": Channel.PUSH,
        "recipient_type": RecipientType.CLIENT,
        "recipient_id": "user-1",
        "subject": "Votre commande est en route",
    }
