"""Shared fixtures — each test gets a fresh application, hence a clean in-memory state.

The simulated PSP is replaced by a ``FlakyPspGateway`` fed with a *deterministic*
random stub (``StubRng``), so no test ever depends on ``random.random()``.
"""

from collections import deque
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.psp import FlakyPspGateway

PAYMENT_PAYLOAD: dict[str, object] = {
    "order_id": "order-1",
    "amount": 42.5,
    "currency": "EUR",
}


class StubRng:
    """Deterministic random source: yields preset values, then 0.99 forever.

    With the default tail value 0.99, any failure_rate <= 0.99 means success.
    """

    def __init__(self, values: list[float] | None = None) -> None:
        self._values: deque[float] = deque(values or [])

    def __call__(self) -> float:
        return self._values.popleft() if self._values else 0.99


@pytest.fixture
def app() -> FastAPI:
    """A brand new application whose PSP gateway is deterministic (always succeeds)."""
    application = create_app()
    application.state.psp_gateway = FlakyPspGateway(failure_rate=0.0, rng=StubRng())
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """A TestClient bound to the fresh application instance."""
    with TestClient(app) as test_client:
        yield test_client
