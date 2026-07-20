"""Shared fixtures — each test gets a fresh application, hence a clean in-memory state.

Hermeticity: no test requires Redis nor any running downstream service. The three
services called by the saga orchestrator (restaurants, payments, deliveries) are
simulated by :class:`FakeDownstream`, a programmable handler plugged into the app
through ``httpx.MockTransport`` — no real network call is ever made.
"""

import json
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

USER_ID = "user-1"

PIZZA_ITEM: dict[str, Any] = {
    "restaurant_id": "resto-1",
    "menu_item_id": "pizza-margherita",
    "name": "Pizza Margherita",
    "unit_price": 10.0,
    "quantity": 2,
    "options": [
        {"name": "extra cheese", "price_delta": 1.5},
        {"name": "no basil", "price_delta": -0.5},
    ],
}

SODA_ITEM: dict[str, Any] = {
    "restaurant_id": "resto-1",
    "menu_item_id": "soda-cola",
    "name": "Cola",
    "unit_price": 3.5,
    "quantity": 1,
    "options": [],
}

DELIVERY_ADDRESS: dict[str, Any] = {
    "label": "Home",
    "street": "10 rue de la Paix",
    "city": "Paris",
    "lat": 48.8698,
    "lng": 2.3311,
}


class FakeDownstream:
    """Programmable stand-in for restaurants/payments/deliveries (httpx.MockTransport).

    Nominal by default: validation OK, payment captured, kitchen ticket accepted,
    courier assigned on the first attempt. Each failure scenario is a knob; every
    received request is recorded (route label + JSON body) for assertions.
    """

    def __init__(self) -> None:
        # Restaurant validation (saga step 2).
        self.validation_valid = True
        self.validation_reasons: list[str] = ["menu item 'pizza-margherita' not found"]
        self.unknown_restaurant = False
        self.restaurants_down = False  # 503 on every restaurants endpoint
        # Payment (saga step 3): queue of statuses for successive calls; when the
        # queue is empty, `payment_fail_always` decides between 201 and 502.
        self.payment_status_queue: list[int] = []
        self.payment_fail_always = False
        # Kitchen ticket (saga step 4).
        self.accept_ticket = True
        # Refund (compensation).
        self.refund_status = 201
        # Delivery assignment (continuation T12): attempt number that succeeds
        # (1 = first call); None = no courier, ever.
        self.courier_available_on_attempt: int | None = 1
        self.delivery_attempts_seen = 0
        # Recorded traffic.
        self.calls: list[str] = []
        self.bodies: list[tuple[str, dict[str, Any]]] = []
        self.requests: list[httpx.Request] = []

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        body: dict[str, Any] = json.loads(request.content) if request.content else {}
        path = request.url.path
        if path.endswith("/order-validations"):
            return self._validate(body)
        if path.endswith("/kitchen-tickets"):
            return self._ticket(body)
        if path == "/api/v1/payments":
            return self._payment(body)
        if path.endswith("/refunds"):
            return self._refund(body)
        if path == "/api/v1/deliveries":
            return self._delivery(body)
        return httpx.Response(500, json={"detail": f"unexpected path {path}"})

    def _record(self, label: str, body: dict[str, Any]) -> None:
        self.calls.append(label)
        self.bodies.append((label, body))

    def _validate(self, body: dict[str, Any]) -> httpx.Response:
        self._record("validate", body)
        if self.restaurants_down:
            return httpx.Response(503, json={"detail": "restaurants down"})
        if self.unknown_restaurant:
            return httpx.Response(404, json={"detail": "Restaurant not found"})
        if not self.validation_valid:
            return httpx.Response(
                200, json={"valid": False, "subtotal": None, "reasons": self.validation_reasons}
            )
        return httpx.Response(200, json={"valid": True, "subtotal": 25.5, "reasons": []})

    def _payment(self, body: dict[str, Any]) -> httpx.Response:
        self._record("payment", body)
        if self.payment_status_queue:
            status = self.payment_status_queue.pop(0)
        else:
            status = 502 if self.payment_fail_always else 201
        if status >= 400:
            return httpx.Response(status, json={"detail": "PSP indisponible"})
        return httpx.Response(
            status,
            json={
                "id": "pay-1",
                "order_id": body["order_id"],
                "amount": body["amount"],
                "currency": "EUR",
                "status": "CAPTURED",
                "refunds": [],
                "refunded_amount": 0.0,
                "created_at": "2026-01-01T00:00:00Z",
            },
        )

    def _ticket(self, body: dict[str, Any]) -> httpx.Response:
        self._record("ticket", body)
        if not self.accept_ticket:
            return httpx.Response(409, json={"detail": "Kitchen ticket refused"})
        return httpx.Response(
            201,
            json={
                "id": "ticket-1",
                "order_id": body["order_id"],
                "restaurant_id": "resto-1",
                "status": "ACCEPTED",
                "items": body["items"],
                "created_at": "2026-01-01T00:00:00Z",
            },
        )

    def _refund(self, body: dict[str, Any]) -> httpx.Response:
        self._record("refund", body)
        if self.refund_status >= 400:
            return httpx.Response(self.refund_status, json={"detail": "PSP indisponible"})
        return httpx.Response(
            201,
            json={
                "id": "pay-1",
                "order_id": "order-1",
                "amount": body.get("amount", 0.0),
                "currency": "EUR",
                "status": "REFUNDED",
                "refunds": [
                    {
                        "id": "ref-1",
                        "amount": body.get("amount", 0.0),
                        "reason": body.get("reason", ""),
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ],
                "refunded_amount": body.get("amount", 0.0),
                "created_at": "2026-01-01T00:00:00Z",
            },
        )

    def _delivery(self, body: dict[str, Any]) -> httpx.Response:
        self._record("delivery", body)
        self.delivery_attempts_seen += 1
        if (
            self.courier_available_on_attempt is None
            or self.delivery_attempts_seen < self.courier_available_on_attempt
        ):
            return httpx.Response(409, json={"detail": "No courier available"})
        return httpx.Response(
            201,
            json={
                "id": "dlv-1",
                "order_id": body["order_id"],
                "courier_id": "courier-1",
                "status": "ACCEPTED",
                "pickup_address": body["pickup_address"],
                "dropoff_address": body["dropoff_address"],
                "events": [],
                "created_at": "2026-01-01T00:00:00Z",
            },
        )


def make_settings(**overrides: Any) -> Settings:
    """Test settings: zero backoff delays so retries never slow the suite down."""
    defaults: dict[str, Any] = {"retry_base_delay": 0.0, "delivery_assign_retry_delay": 0.0}
    defaults.update(overrides)
    return Settings(**defaults)


def build_client(downstream: FakeDownstream, **overrides: Any) -> TestClient:
    """A TestClient whose saga only ever talks to the fake downstream services."""
    return TestClient(create_app(make_settings(**overrides), http_transport=downstream.transport))


@pytest.fixture
def downstream() -> FakeDownstream:
    return FakeDownstream()


@pytest.fixture
def client(downstream: FakeDownstream) -> Iterator[TestClient]:
    """A TestClient bound to a brand new application instance (in-memory backends)."""
    with build_client(downstream) as test_client:
        yield test_client


def add_item(client: TestClient, user_id: str, item: dict[str, Any]) -> Any:
    """Helper: add an item to a user's cart."""
    return client.post(f"/api/v1/carts/{user_id}/items", json=item)


def place_order(
    client: TestClient,
    user_id: str = USER_ID,
    delivery_address: dict[str, Any] | None = None,
    **extra: Any,
) -> Any:
    """Helper: place an order for a user."""
    payload: dict[str, Any] = {
        "user_id": user_id,
        "delivery_address": delivery_address or DELIVERY_ADDRESS,
        **extra,
    }
    return client.post("/api/v1/orders", json=payload)
