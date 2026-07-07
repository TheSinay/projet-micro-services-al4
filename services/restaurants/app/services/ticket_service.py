"""Kitchen ticket logic: acceptance/refusal (SAGA step 4) and preparation lifecycle."""

import uuid
from datetime import UTC, datetime

import structlog

from app.events import EventBus
from app.repositories.entities import KitchenTicket, TicketItem, TicketStatus
from app.repositories.interfaces import KitchenTicketRepository, RestaurantRepository
from app.schemas.tickets import KitchenTicketCreate
from app.services.exceptions import (
    InvalidTicketTransitionError,
    KitchenTicketNotFoundError,
    RestaurantNotFoundError,
    TicketRefusedError,
)

ORDER_READY_CHANNEL = "order.ready"

# Strict lifecycle: ACCEPTED -> PREPARING -> READY (anything else is a 409).
_ALLOWED_TRANSITIONS: dict[TicketStatus, TicketStatus] = {
    TicketStatus.ACCEPTED: TicketStatus.PREPARING,
    TicketStatus.PREPARING: TicketStatus.READY,
}


class KitchenTicketService:
    """Ticket creation (accept/refuse via ``auto_accept``) and status transitions."""

    def __init__(
        self,
        restaurants: RestaurantRepository,
        tickets: KitchenTicketRepository,
        event_bus: EventBus,
    ) -> None:
        self._restaurants = restaurants
        self._tickets = tickets
        self._event_bus = event_bus

    def create(self, restaurant_id: str, data: KitchenTicketCreate) -> KitchenTicket:
        """Create a ticket; a restaurant with ``auto_accept=False`` refuses it (409).

        The refused ticket is still recorded (status REFUSED) for auditability.
        """
        restaurant = self._restaurants.get_by_id(restaurant_id)
        if restaurant is None:
            raise RestaurantNotFoundError()
        ticket = KitchenTicket(
            id=uuid.uuid4().hex,
            order_id=data.order_id,
            restaurant_id=restaurant_id,
            status=TicketStatus.ACCEPTED if restaurant.auto_accept else TicketStatus.REFUSED,
            items=[
                TicketItem(menu_item_id=i.menu_item_id, quantity=i.quantity) for i in data.items
            ],
            created_at=datetime.now(UTC),
        )
        self._tickets.add(ticket)
        if not restaurant.auto_accept:
            raise TicketRefusedError()
        return ticket

    async def update_status(self, ticket_id: str, new_status: TicketStatus) -> KitchenTicket:
        """Apply a strict transition; publishes ``order.ready`` when the ticket is READY."""
        ticket = self._tickets.get_by_id(ticket_id)
        if ticket is None:
            raise KitchenTicketNotFoundError()
        if _ALLOWED_TRANSITIONS.get(ticket.status) != new_status:
            raise InvalidTicketTransitionError()
        ticket.status = new_status
        self._tickets.update(ticket)
        if new_status is TicketStatus.READY:
            await self._publish_order_ready(ticket)
        return ticket

    async def _publish_order_ready(self, ticket: KitchenTicket) -> None:
        """Notify downstream (orders service) that the order awaits pickup."""
        restaurant = self._restaurants.get_by_id(ticket.restaurant_id)
        correlation_id = structlog.contextvars.get_contextvars().get("correlation_id")
        payload: dict[str, object] = {
            "event": ORDER_READY_CHANNEL,
            "correlation_id": correlation_id,
            "data": {
                "order_id": ticket.order_id,
                "restaurant_id": ticket.restaurant_id,
                "pickup_address": restaurant.address if restaurant is not None else None,
            },
        }
        await self._event_bus.publish(ORDER_READY_CHANNEL, payload)
