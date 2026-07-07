"""Declarative event -> notification routing rules.

``NotificationDispatcher.handle_event`` takes a plain event envelope
(``{"event", "correlation_id", "data"}``) as a dict: it is fully decoupled from
Redis, so tests call it directly with dict payloads — the pub/sub loop in
``app.subscriber`` is only a thin transport in front of it.

"Sending" a notification is simulated: the structured log line *is* the
delivery, and the notification is persisted for the demo / frontend.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from app.logging import logger
from app.repositories.entities import Channel, Notification, RecipientType
from app.repositories.interfaces import NotificationRepository

BodyBuilder = Callable[[dict[str, Any]], str]


@dataclass(frozen=True)
class RoutingRule:
    """One recipient of an event: who to notify, on which channels, with what."""

    recipient_type: RecipientType
    id_key: str  # key of the recipient id in the event ``data`` payload
    channels: tuple[Channel, ...]
    subject: str
    body: BodyBuilder


def _order_label(data: dict[str, Any]) -> str:
    order_id = data.get("order_id")
    return f"commande {order_id}" if order_id else "commande"


def _confirmed_client_body(data: dict[str, Any]) -> str:
    return f"Votre {_order_label(data)} est confirmée et va être préparée."


def _confirmed_restaurant_body(data: dict[str, Any]) -> str:
    return f"Nouvelle {_order_label(data)} à préparer."


def _cancelled_body(data: dict[str, Any]) -> str:
    reason = data.get("reason") or "raison non précisée"
    body = f"Votre {_order_label(data)} a été annulée : {reason}."
    refund_amount = data.get("refund_amount")
    if refund_amount is not None:
        body += f" Un remboursement de {refund_amount} € a été effectué."
    elif data.get("refunded"):
        body += " Un remboursement a été effectué."
    return body


def _assigned_client_body(data: dict[str, Any]) -> str:
    courier_name = data.get("courier_name")
    who = f"Votre livreur {courier_name}" if courier_name else "Votre livreur"
    return f"{who} est en route vers le restaurant."


def _assigned_courier_body(data: dict[str, Any]) -> str:
    return f"Nouvelle course assignée pour la {_order_label(data)}."


def _picked_up_body(data: dict[str, Any]) -> str:
    return f"Votre {_order_label(data)} est en route."


def _delivered_body(data: dict[str, Any]) -> str:
    return f"Votre {_order_label(data)} a été livrée. Bon appétit !"


_EMAIL_AND_PUSH = (Channel.EMAIL, Channel.PUSH)
_PUSH_ONLY = (Channel.PUSH,)

# ``delivery.completed`` (deliveries) and ``order.delivered`` (orders) both mean
# "the meal has arrived": same notification either way.
_DELIVERED_RULES: tuple[RoutingRule, ...] = (
    RoutingRule(RecipientType.CLIENT, "user_id", _EMAIL_AND_PUSH, "Bon appétit !", _delivered_body),
)

# Declarative routing table: event -> recipients. An empty tuple means the
# event is technical and deliberately produces no notification.
ROUTING_TABLE: dict[str, tuple[RoutingRule, ...]] = {
    "order.confirmed": (
        RoutingRule(
            RecipientType.CLIENT,
            "user_id",
            _EMAIL_AND_PUSH,
            "Votre commande est confirmée",
            _confirmed_client_body,
        ),
        RoutingRule(
            RecipientType.RESTAURANT,
            "restaurant_id",
            _PUSH_ONLY,
            "Nouvelle commande à préparer",
            _confirmed_restaurant_body,
        ),
    ),
    "order.cancelled": (
        RoutingRule(
            RecipientType.CLIENT,
            "user_id",
            _EMAIL_AND_PUSH,
            "Votre commande est annulée",
            _cancelled_body,
        ),
    ),
    # Technical event (triggers courier assignment in orders): no client notification.
    "order.ready": (),
    "delivery.assigned": (
        RoutingRule(
            RecipientType.CLIENT,
            "user_id",
            _PUSH_ONLY,
            "Votre livreur est en route vers le restaurant",
            _assigned_client_body,
        ),
        RoutingRule(
            RecipientType.COURIER,
            "courier_id",
            _PUSH_ONLY,
            "Nouvelle course assignée",
            _assigned_courier_body,
        ),
    ),
    "delivery.picked_up": (
        RoutingRule(
            RecipientType.CLIENT,
            "user_id",
            _PUSH_ONLY,
            "Votre commande est en route",
            _picked_up_body,
        ),
    ),
    "delivery.completed": _DELIVERED_RULES,
    "order.delivered": _DELIVERED_RULES,
}


class NotificationDispatcher:
    """Turn incoming event envelopes into persisted, "sent" notifications."""

    def __init__(self, notifications: NotificationRepository) -> None:
        self._notifications = notifications

    def handle_event(self, payload: dict[str, Any]) -> list[Notification]:
        """Route one event envelope; unknown events are ignored without crashing."""
        event = payload.get("event")
        raw_data = payload.get("data")
        data: dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}
        raw_correlation_id = payload.get("correlation_id")
        correlation_id = raw_correlation_id if isinstance(raw_correlation_id, str) else None

        if not isinstance(event, str) or event not in ROUTING_TABLE:
            logger.warning("unknown_event_ignored", event_name=event)
            return []
        rules = ROUTING_TABLE[event]
        if not rules:
            logger.debug("technical_event_ignored", event_name=event)
            return []

        bound = {"correlation_id": correlation_id} if correlation_id else {}
        with structlog.contextvars.bound_contextvars(**bound):
            return self._apply_rules(event, rules, data, correlation_id)

    def _apply_rules(
        self,
        event: str,
        rules: tuple[RoutingRule, ...],
        data: dict[str, Any],
        correlation_id: str | None,
    ) -> list[Notification]:
        """Notify every recipient whose id is present in the payload (warn otherwise)."""
        created: list[Notification] = []
        for rule in rules:
            raw_recipient_id = data.get(rule.id_key)
            if raw_recipient_id is None or raw_recipient_id == "":
                logger.warning(
                    "recipient_missing_in_payload",
                    event_name=event,
                    recipient_type=rule.recipient_type,
                    expected_key=rule.id_key,
                )
                continue
            recipient_id = str(raw_recipient_id)
            body = rule.body(data)
            for channel in rule.channels:
                notification = Notification(
                    id=uuid.uuid4().hex,
                    recipient_type=rule.recipient_type,
                    recipient_id=recipient_id,
                    channel=channel,
                    subject=rule.subject,
                    body=body,
                    event=event,
                    correlation_id=correlation_id,
                    created_at=datetime.now(UTC),
                )
                self._notifications.add(notification)
                # Simulated send: the log line stands in for the email/push/SMS provider.
                logger.info(
                    "notification_sent",
                    channel=channel,
                    recipient_type=rule.recipient_type,
                    recipient_id=recipient_id,
                    subject=rule.subject,
                )
                created.append(notification)
        return created
