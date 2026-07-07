"""Order use cases: checkout from the cart, pricing, strict state machine, history."""

import uuid
from dataclasses import replace
from datetime import UTC, datetime

from app.events import EventBus
from app.repositories.entities import (
    CartItem,
    DeliveryAddress,
    Order,
    OrderStatus,
)
from app.repositories.interfaces import CartStore, OrderRepository
from app.schemas.orders import OrderCreate
from app.services.exceptions import (
    EmptyCartError,
    IllegalStatusTransitionError,
    OrderNotFoundError,
)
from app.services.pricing import compute_delivery_fee, compute_subtotal

# Strict state machine: RECEIVED -> PREPARING -> DELIVERING -> DELIVERED,
# CANCELLED reachable from RECEIVED and PREPARING only.
ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.RECEIVED: frozenset({OrderStatus.PREPARING, OrderStatus.CANCELLED}),
    OrderStatus.PREPARING: frozenset({OrderStatus.DELIVERING, OrderStatus.CANCELLED}),
    OrderStatus.DELIVERING: frozenset({OrderStatus.DELIVERED}),
    OrderStatus.DELIVERED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}

# Initial saga state; the orchestrator (T09) will advance it step by step.
SAGA_STATE_PENDING = "PENDING"


def _snapshot_items(items: list[CartItem]) -> list[CartItem]:
    """Deep-copy the cart lines so later cart mutations never touch the order."""
    return [replace(item, options=[replace(option) for option in item.options]) for item in items]


class OrderService:
    """Checkout and lifecycle of orders."""

    def __init__(
        self,
        carts: CartStore,
        orders: OrderRepository,
        event_bus: EventBus,
        base_delivery_fee: float,
        delivery_fee_per_km: float,
    ) -> None:
        self._carts = carts
        self._orders = orders
        self._event_bus = event_bus
        self._base_delivery_fee = base_delivery_fee
        self._delivery_fee_per_km = delivery_fee_per_km

    def place_order(self, data: OrderCreate) -> Order:
        """Build an order from the user's cart (frozen prices), then empty the cart.

        The order starts in ``RECEIVED`` with ``saga_state="PENDING"``; the saga
        orchestrator (T09) takes over from there.
        """
        cart = self._carts.get(data.user_id)
        if cart is None or not cart.items or cart.restaurant_id is None:
            raise EmptyCartError()

        items = _snapshot_items(cart.items)
        subtotal = compute_subtotal(items)
        restaurant_lat = (
            data.restaurant_lat if data.restaurant_lat is not None else cart.restaurant_lat
        )
        restaurant_lng = (
            data.restaurant_lng if data.restaurant_lng is not None else cart.restaurant_lng
        )
        delivery_fee = compute_delivery_fee(
            self._base_delivery_fee,
            self._delivery_fee_per_km,
            restaurant_lat,
            restaurant_lng,
            data.delivery_address.lat,
            data.delivery_address.lng,
        )
        now = datetime.now(UTC)
        order = Order(
            id=uuid.uuid4().hex,
            user_id=data.user_id,
            restaurant_id=cart.restaurant_id,
            items=items,
            delivery_address=DeliveryAddress(
                lat=data.delivery_address.lat,
                lng=data.delivery_address.lng,
                label=data.delivery_address.label,
                street=data.delivery_address.street,
                city=data.delivery_address.city,
            ),
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=round(subtotal + delivery_fee, 2),
            status=OrderStatus.RECEIVED,
            saga_state=SAGA_STATE_PENDING,
            created_at=now,
            updated_at=now,
        )
        self._orders.add(order)
        self._carts.clear(data.user_id)
        # TODO(T09): hand the order over to the saga orchestrator here —
        # restaurant validation -> payment -> kitchen ticket, with compensations,
        # publishing order.confirmed / order.cancelled on self._event_bus.
        return order

    def get(self, order_id: str) -> Order:
        """Return the order or raise a 404 domain error."""
        order = self._orders.get_by_id(order_id)
        if order is None:
            raise OrderNotFoundError()
        return order

    def list_for_user(self, user_id: str) -> list[Order]:
        """Order history for a user, most recent first."""
        orders = sorted(self._orders.list_by_user(user_id), key=lambda order: order.created_at)
        return list(reversed(orders))

    def transition(self, order_id: str, new_status: OrderStatus) -> Order:
        """Apply a state machine transition; illegal transitions raise a 409.

        Used by the demo/tracking endpoint ``PATCH /orders/{id}/status`` and, later,
        by the saga orchestrator (T09) to drive the order lifecycle.
        """
        order = self.get(order_id)
        if new_status not in ALLOWED_TRANSITIONS[order.status]:
            raise IllegalStatusTransitionError(order.status.value, new_status.value)
        order.status = new_status
        order.updated_at = datetime.now(UTC)
        self._orders.update(order)
        return order
