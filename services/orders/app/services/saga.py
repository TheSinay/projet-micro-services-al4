"""PLACE_ORDER saga orchestrator (T09) and its event-driven continuation (T12).

Critical phase, orchestrated synchronously (ADR 0003):

1. the order already exists in ``RECEIVED`` (created by ``OrderService.place_order``);
2. restaurant validation — invalid/unknown -> CANCELLED + ``order.cancelled``;
3. payment, protected by circuit breaker + retry + timeout (ADR 0007) — failure ->
   CANCELLED (nothing to refund);
4. kitchen ticket — refusal -> compensation: TOTAL REFUND then CANCELLED;
5. success -> PREPARING + ``order.confirmed``.

Event-driven continuation (choreography):

- ``order.ready`` -> request a courier (deferred retries; final failure -> late
  compensation: total refund + CANCELLED) -> DELIVERING;
- ``delivery.completed`` -> DELIVERED + ``order.delivered``.

Every step is persisted in ``Order.saga_state`` so a saga is observable at any time.
The saga never raises to the HTTP layer: a failed checkout still answers 201 with the
CANCELLED order and a human-readable ``cancellation_reason`` (documented in README).
"""

import asyncio
import random
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from app.clients import (
    DeliveriesClient,
    DownstreamClientError,
    PaymentsClient,
    RestaurantsClient,
)
from app.events import EventBus
from app.logging import logger
from app.repositories.entities import Order, OrderStatus
from app.repositories.interfaces import OrderRepository
from app.services.resilience import (
    RETRYABLE_EXCEPTIONS,
    CircuitBreaker,
    CircuitOpenError,
    retry_async,
)

# Saga states persisted on the order (observable progress, ADR 0003).
SAGA_VALIDATING = "VALIDATING"
SAGA_PAYING = "PAYING"
SAGA_REQUESTING_ACCEPT = "REQUESTING_ACCEPT"
SAGA_CONFIRMED = "CONFIRMED"
SAGA_COMPENSATING = "COMPENSATING"
SAGA_REFUND_FAILED = "REFUND_FAILED"
SAGA_CANCELLED_VALIDATION = "CANCELLED_VALIDATION"
SAGA_CANCELLED_PAYMENT = "CANCELLED_PAYMENT"
SAGA_CANCELLED_REFUSED = "CANCELLED_REFUSED"
SAGA_ASSIGNING_DELIVERY = "ASSIGNING_DELIVERY"
SAGA_DELIVERING = "DELIVERING"
SAGA_DELIVERED = "DELIVERED"
SAGA_CANCELLED_NO_COURIER = "CANCELLED_NO_COURIER"

ORDER_CONFIRMED_CHANNEL = "order.confirmed"
ORDER_CANCELLED_CHANNEL = "order.cancelled"
ORDER_DELIVERED_CHANNEL = "order.delivered"

# Any downstream failure the orchestrator must translate into a cancellation
# instead of a 500: transient failures (after retries) and unexpected 4xx.
_DOWNSTREAM_FAILURES: tuple[type[BaseException], ...] = (
    *RETRYABLE_EXCEPTIONS,
    httpx.HTTPError,
    DownstreamClientError,
)


class SagaOrchestrator:
    """Drives the PLACE_ORDER saga and its event-driven continuation."""

    def __init__(
        self,
        *,
        orders: OrderRepository,
        event_bus: EventBus,
        restaurants: RestaurantsClient,
        payments: PaymentsClient,
        deliveries: DeliveriesClient,
        payment_breaker: CircuitBreaker,
        retry_attempts: int = 3,
        retry_base_delay: float = 0.1,
        delivery_attempts: int = 3,
        delivery_retry_delay: float = 2.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        rng: Callable[[], float] = random.random,
    ) -> None:
        self._orders = orders
        self._event_bus = event_bus
        self._restaurants = restaurants
        self._payments = payments
        self._deliveries = deliveries
        self._payment_breaker = payment_breaker
        self._retry_attempts = retry_attempts
        self._retry_base_delay = retry_base_delay
        self._delivery_attempts = delivery_attempts
        self._delivery_retry_delay = delivery_retry_delay
        self._sleep = sleep
        self._rng = rng

    # ------------------------------------------------------------------ checkout

    async def run_checkout(self, order: Order) -> None:
        """Run saga steps 2 to 5 on a freshly created RECEIVED order.

        Never raises on a downstream failure: the order ends CANCELLED with a
        readable ``cancellation_reason`` and an ``order.cancelled`` event.
        """
        self._set_saga_state(order, SAGA_VALIDATING)
        if not await self._validate_with_restaurant(order):
            return

        self._set_saga_state(order, SAGA_PAYING)
        if not await self._charge_payment(order):
            return

        self._set_saga_state(order, SAGA_REQUESTING_ACCEPT)
        accepted, failure_reason = await self._request_kitchen_ticket(order)
        if not accepted:
            await self._refund_and_cancel(order, failure_reason, SAGA_CANCELLED_REFUSED)
            return

        self._transition(order, OrderStatus.PREPARING, SAGA_CONFIRMED)
        self._publish(
            ORDER_CONFIRMED_CHANNEL,
            {
                "order_id": order.id,
                "user_id": order.user_id,
                "restaurant_id": order.restaurant_id,
                "total": order.total,
            },
        )
        logger.info("saga_confirmed", order_id=order.id, payment_id=order.payment_id)

    async def _validate_with_restaurant(self, order: Order) -> bool:
        """Step 2 — cancel (nothing to refund) on invalid verdict or unreachable service."""
        try:
            verdict = await self._retry(
                lambda: self._restaurants.validate_order(order.restaurant_id, order.items)
            )
        except _DOWNSTREAM_FAILURES as exc:
            logger.warning("saga_validation_unreachable", order_id=order.id, error=str(exc))
            self._cancel(
                order,
                SAGA_CANCELLED_VALIDATION,
                "validation impossible : service restaurants indisponible",
            )
            return False
        if not verdict.valid:
            reasons = "; ".join(verdict.reasons) or "commande invalide"
            self._cancel(order, SAGA_CANCELLED_VALIDATION, f"commande refusée : {reasons}")
            return False
        return True

    async def _charge_payment(self, order: Order) -> bool:
        """Step 3 — breaker + retry + timeout; failure -> CANCELLED, nothing to refund."""
        try:
            payment_id = await self._retry(
                lambda: self._payment_breaker.call(
                    lambda: self._payments.create_payment(order.id, order.total)
                )
            )
        except CircuitOpenError:
            logger.warning("saga_payment_circuit_open", order_id=order.id)
            self._cancel(
                order,
                SAGA_CANCELLED_PAYMENT,
                "paiement indisponible (circuit ouvert), commande annulée sans débit",
            )
            return False
        except _DOWNSTREAM_FAILURES as exc:
            logger.warning("saga_payment_failed", order_id=order.id, error=str(exc))
            self._cancel(
                order,
                SAGA_CANCELLED_PAYMENT,
                "paiement refusé (PSP indisponible), commande annulée sans débit",
            )
            return False
        order.payment_id = payment_id
        self._persist(order)
        return True

    async def _request_kitchen_ticket(self, order: Order) -> tuple[bool, str]:
        """Step 4 — returns (accepted, reason-for-compensation-when-refused)."""
        try:
            accepted = await self._retry(
                lambda: self._restaurants.create_kitchen_ticket(
                    order.restaurant_id, order.id, order.items
                )
            )
        except _DOWNSTREAM_FAILURES as exc:
            logger.warning("saga_kitchen_ticket_unreachable", order_id=order.id, error=str(exc))
            return False, "restaurant injoignable après paiement"
        if not accepted:
            return False, "refusée par le restaurant"
        return True, ""

    # -------------------------------------------------------------- continuation

    async def handle_order_ready(self, data: dict[str, Any]) -> None:
        """``order.ready`` -> request a courier; success -> DELIVERING.

        409 "no courier" is retried with a deferred, configurable delay; a final
        failure triggers the late compensation (total refund + CANCELLED).
        """
        order = self._orders.get_by_id(str(data.get("order_id", "")))
        if order is None:
            logger.warning("order_ready_unknown_order", order_id=data.get("order_id"))
            return
        if order.status is not OrderStatus.PREPARING:
            logger.info("order_ready_ignored", order_id=order.id, status=order.status.value)
            return

        self._set_saga_state(order, SAGA_ASSIGNING_DELIVERY)
        pickup = self._pickup_address(order, data.get("pickup_address"))
        dropoff = {
            "label": order.delivery_address.label,
            "lat": order.delivery_address.lat,
            "lng": order.delivery_address.lng,
        }
        for attempt in range(1, self._delivery_attempts + 1):
            try:
                delivery_id = await self._deliveries.request_delivery(order.id, pickup, dropoff)
            except _DOWNSTREAM_FAILURES as exc:
                logger.warning(
                    "delivery_request_failed", order_id=order.id, attempt=attempt, error=str(exc)
                )
                delivery_id = None
            if delivery_id is not None:
                order.delivery_id = delivery_id
                self._transition(order, OrderStatus.DELIVERING, SAGA_DELIVERING)
                logger.info("delivery_assigned", order_id=order.id, delivery_id=delivery_id)
                return
            if attempt < self._delivery_attempts:
                await self._sleep(self._delivery_retry_delay)

        logger.warning("delivery_assignment_exhausted", order_id=order.id)
        await self._refund_and_cancel(order, "aucun livreur disponible", SAGA_CANCELLED_NO_COURIER)

    async def handle_delivery_completed(self, data: dict[str, Any]) -> None:
        """``delivery.completed`` -> DELIVERED + ``order.delivered``."""
        order = self._orders.get_by_id(str(data.get("order_id", "")))
        if order is None:
            logger.warning("delivery_completed_unknown_order", order_id=data.get("order_id"))
            return
        if order.status is not OrderStatus.DELIVERING:
            logger.info("delivery_completed_ignored", order_id=order.id, status=order.status.value)
            return
        self._transition(order, OrderStatus.DELIVERED, SAGA_DELIVERED)
        self._publish(ORDER_DELIVERED_CHANNEL, {"order_id": order.id, "user_id": order.user_id})
        logger.info("saga_delivered", order_id=order.id)

    def _pickup_address(self, order: Order, label: object) -> dict[str, Any]:
        """Pickup point for the courier: restaurant coordinates recorded at checkout.

        When the restaurant coordinates are unknown (optional at checkout), fall back
        to the dropoff coordinates so the assignment can still proceed (documented
        prototype limitation — the courier search radius is then centred on the client).
        """
        lat = (
            order.restaurant_lat if order.restaurant_lat is not None else order.delivery_address.lat
        )
        lng = (
            order.restaurant_lng if order.restaurant_lng is not None else order.delivery_address.lng
        )
        return {"label": str(label) if label is not None else None, "lat": lat, "lng": lng}

    # -------------------------------------------------------------- compensation

    async def _refund_and_cancel(self, order: Order, reason: str, final_state: str) -> None:
        """Compensation: total refund of the captured payment, then CANCELLED.

        A refund failure is a documented debt: CRITICAL structured log +
        ``saga_state = REFUND_FAILED`` (manual intervention required); the order is
        still cancelled so the client is never left waiting.
        """
        self._set_saga_state(order, SAGA_COMPENSATING)
        payment_id = order.payment_id
        assert payment_id is not None  # compensation only runs after a captured payment
        try:
            await self._retry(
                lambda: self._payments.refund(
                    payment_id, amount=order.total, reason=f"commande {order.id} : {reason}"
                )
            )
        except _DOWNSTREAM_FAILURES as exc:
            logger.critical(
                "refund_failed",
                order_id=order.id,
                payment_id=payment_id,
                amount=order.total,
                error=str(exc),
            )
            self._cancel(
                order,
                SAGA_REFUND_FAILED,
                f"{reason} — remboursement en échec, intervention manuelle requise",
            )
            return
        self._cancel(order, final_state, f"{reason}, remboursement effectué")

    # ------------------------------------------------------------------ plumbing

    async def _retry[T](self, func: Callable[[], Awaitable[T]]) -> T:
        return await retry_async(
            func,
            attempts=self._retry_attempts,
            base_delay=self._retry_base_delay,
            sleep=self._sleep,
            rng=self._rng,
        )

    def _cancel(self, order: Order, saga_state: str, reason: str) -> None:
        order.cancellation_reason = reason
        self._transition(order, OrderStatus.CANCELLED, saga_state)
        self._publish(
            ORDER_CANCELLED_CHANNEL,
            {"order_id": order.id, "user_id": order.user_id, "reason": reason},
        )
        logger.info("saga_cancelled", order_id=order.id, saga_state=saga_state, reason=reason)

    def _transition(self, order: Order, status: OrderStatus, saga_state: str) -> None:
        """Move the order in the state machine and persist saga progress."""
        # Local import to avoid a circular import (order_service builds the saga deps).
        from app.services.order_service import ALLOWED_TRANSITIONS

        if status not in ALLOWED_TRANSITIONS[order.status]:  # pragma: no cover - safety net
            raise RuntimeError(f"saga illegal transition {order.status} -> {status}")
        order.status = status
        order.saga_state = saga_state
        self._persist(order)

    def _set_saga_state(self, order: Order, saga_state: str) -> None:
        order.saga_state = saga_state
        self._persist(order)

    def _persist(self, order: Order) -> None:
        order.updated_at = datetime.now(UTC)
        self._orders.update(order)

    def _publish(self, channel: str, data: dict[str, Any]) -> None:
        correlation_id = structlog.contextvars.get_contextvars().get("correlation_id")
        self._event_bus.publish(
            channel,
            {"event": channel, "correlation_id": correlation_id, "data": data},
        )
