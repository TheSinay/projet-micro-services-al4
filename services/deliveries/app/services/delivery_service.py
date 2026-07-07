"""Delivery assignment and tracking logic.

Assignment picks the closest *available* courier to the pickup point (haversine).
For the prototype the chosen courier immediately auto-accepts the proposal
(``PROPOSED`` -> ``ACCEPTED``), which is why ``delivery.proposed`` and
``delivery.assigned`` are published back-to-back (documented in the README).
"""

import uuid
from datetime import UTC, datetime

from app.events import EventBus, build_payload
from app.logging import logger
from app.repositories.entities import (
    Courier,
    Delivery,
    DeliveryEvent,
    DeliveryStatus,
    GeoAddress,
    Location,
)
from app.repositories.interfaces import CourierRepository, DeliveryRepository
from app.schemas.deliveries import DeliveryAddress, DeliveryCreate
from app.services.exceptions import (
    DeliveryNotFoundError,
    InvalidDeliveryTransitionError,
    NoCourierAvailableError,
)
from app.services.geo import haversine_km

# Strict forward-only transitions accepted through PATCH /deliveries/{id}.
_ALLOWED_TRANSITIONS: dict[DeliveryStatus, DeliveryStatus] = {
    DeliveryStatus.ACCEPTED: DeliveryStatus.PICKED_UP,
    DeliveryStatus.PICKED_UP: DeliveryStatus.DELIVERED,
}


class DeliveryService:
    """Use cases around delivery assignment and status tracking."""

    def __init__(
        self,
        couriers: CourierRepository,
        deliveries: DeliveryRepository,
        events: EventBus,
    ) -> None:
        self._couriers = couriers
        self._deliveries = deliveries
        self._events = events

    async def request_delivery(self, data: DeliveryCreate) -> tuple[Delivery, bool]:
        """Assign the closest available courier to the order.

        Returns ``(delivery, created)``; ``created`` is False when an active delivery
        already exists for this ``order_id`` (idempotent re-POST -> 200).
        Raises ``NoCourierAvailableError`` (409) when the whole fleet is busy.
        """
        existing = self._find_active(data.order_id)
        if existing is not None:
            return existing, False

        courier = self._pick_closest_courier(data.pickup_address)
        now = datetime.now(UTC)
        delivery = Delivery(
            id=uuid.uuid4().hex,
            order_id=data.order_id,
            courier_id=courier.id,
            status=DeliveryStatus.PROPOSED,
            pickup_address=self._to_address(data.pickup_address),
            dropoff_address=self._to_address(data.dropoff_address),
            created_at=now,
            events=[DeliveryEvent(status=DeliveryStatus.PROPOSED, at=now)],
        )
        self._deliveries.add(delivery)
        courier.available = False
        self._couriers.update(courier)
        await self._publish(
            "delivery.proposed",
            {"order_id": delivery.order_id, "delivery_id": delivery.id, "courier_id": courier.id},
        )

        # Prototype simulation: the courier auto-accepts the proposal immediately.
        self._record_transition(delivery, DeliveryStatus.ACCEPTED)
        await self._publish(
            "delivery.assigned",
            {
                "order_id": delivery.order_id,
                "delivery_id": delivery.id,
                "courier_id": courier.id,
                "courier_name": courier.name,
            },
        )
        logger.info(
            "delivery_assigned",
            delivery_id=delivery.id,
            order_id=delivery.order_id,
            courier_id=courier.id,
        )
        return delivery, True

    async def update_status(self, delivery_id: str, new_status: DeliveryStatus) -> Delivery:
        """Apply a strict ACCEPTED -> PICKED_UP -> DELIVERED transition (else 409)."""
        delivery = self.get(delivery_id)
        if _ALLOWED_TRANSITIONS.get(delivery.status) is not new_status:
            raise InvalidDeliveryTransitionError()

        self._record_transition(delivery, new_status)
        if new_status is DeliveryStatus.PICKED_UP:
            await self._publish(
                "delivery.picked_up",
                {
                    "order_id": delivery.order_id,
                    "delivery_id": delivery.id,
                    "courier_id": delivery.courier_id,
                },
            )
        else:  # DeliveryStatus.DELIVERED
            self._release_courier(delivery)
            await self._publish(
                "delivery.completed",
                {"order_id": delivery.order_id, "delivery_id": delivery.id},
            )
        logger.info("delivery_status_updated", delivery_id=delivery.id, status=new_status)
        return delivery

    def get(self, delivery_id: str) -> Delivery:
        delivery = self._deliveries.get_by_id(delivery_id)
        if delivery is None:
            raise DeliveryNotFoundError()
        return delivery

    def list(self, order_id: str | None = None) -> list[Delivery]:
        if order_id is not None:
            return self._deliveries.list_by_order(order_id)
        return self._deliveries.list_all()

    def _find_active(self, order_id: str) -> Delivery | None:
        """Return the non-DELIVERED delivery for this order, if any (idempotence key)."""
        return next(
            (
                delivery
                for delivery in self._deliveries.list_by_order(order_id)
                if delivery.status is not DeliveryStatus.DELIVERED
            ),
            None,
        )

    def _pick_closest_courier(self, pickup: DeliveryAddress) -> Courier:
        available = [courier for courier in self._couriers.list_all() if courier.available]
        if not available:
            raise NoCourierAvailableError()
        return min(
            available,
            key=lambda courier: haversine_km(
                courier.location.lat, courier.location.lng, pickup.lat, pickup.lng
            ),
        )

    def _record_transition(self, delivery: Delivery, status: DeliveryStatus) -> None:
        delivery.status = status
        delivery.events.append(DeliveryEvent(status=status, at=datetime.now(UTC)))
        self._deliveries.update(delivery)

    def _release_courier(self, delivery: Delivery) -> None:
        """Make the courier available again, positioned at the dropoff point."""
        courier = self._couriers.get_by_id(delivery.courier_id)
        if courier is None:  # pragma: no cover - defensive, couriers are never deleted
            return
        courier.available = True
        courier.location = Location(
            lat=delivery.dropoff_address.lat, lng=delivery.dropoff_address.lng
        )
        self._couriers.update(courier)

    async def _publish(self, channel: str, data: dict[str, object]) -> None:
        await self._events.publish(channel, build_payload(channel, dict(data)))

    @staticmethod
    def _to_address(address: DeliveryAddress) -> GeoAddress:
        return GeoAddress(lat=address.lat, lng=address.lng, label=address.label)
