"""Application factory for the orders service."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import redis
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.clients import DeliveriesClient, PaymentsClient, RestaurantsClient
from app.config import Settings, get_settings
from app.events import EventBus, InMemoryEventBus, RedisEventBus
from app.logging import CorrelationIdMiddleware, configure_logging
from app.repositories.interfaces import CartStore
from app.repositories.memory import InMemoryCartStore, InMemoryOrderRepository
from app.repositories.redis_store import RedisCartStore
from app.routes import api_router
from app.routes.health import router as health_router
from app.services.exceptions import DomainError
from app.services.resilience import CircuitBreaker
from app.services.saga import SagaOrchestrator
from app.subscriber import (
    DELIVERY_COMPLETED_CHANNEL,
    ORDER_READY_CHANNEL,
    RedisSubscriber,
)


async def _handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    """Translate business errors into normalized ``{"detail": ...}`` responses."""
    assert isinstance(exc, DomainError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


def _build_cart_store(settings: Settings) -> CartStore:
    """Select the cart backend: Redis in production, in-memory by default (tests, demo)."""
    if settings.cart_store_backend == "redis":
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        return RedisCartStore(client)
    return InMemoryCartStore()


def _build_event_bus(settings: Settings) -> EventBus:
    """Select the event bus backend: Redis pub/sub in production, in-memory by default."""
    if settings.event_bus_backend == "redis":
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        return RedisEventBus(client)
    return InMemoryEventBus()


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start/stop the saga continuation subscriber and release the HTTP client.

    The Redis subscription only exists with ``event_bus_backend=redis``: the
    default in-memory backend keeps tests and standalone runs hermetic.
    """
    subscriber: RedisSubscriber | None = app.state.subscriber
    if subscriber is not None:
        await subscriber.start()
    try:
        yield
    finally:
        if subscriber is not None:
            await subscriber.stop()
        await app.state.http_client.aclose()


def create_app(
    settings: Settings | None = None,
    http_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """Create a fully wired FastAPI application with fresh state.

    Stores live on ``app.state`` (no module-level globals), so tests can
    instantiate an isolated application per test case with in-memory backends.
    ``http_transport`` lets the test suite plug an ``httpx.MockTransport`` so the
    saga orchestrator is exercised without any real network call.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="service-commandes",
        description=(
            "Orders for the food delivery platform: cart, checkout with pricing "
            "(subtotal + distance-based delivery fee), strict order state machine, "
            "history, and the PLACE_ORDER saga orchestrator (validation -> payment "
            "-> kitchen ticket, with compensations and resilience patterns)."
        ),
        version="0.2.0",
        lifespan=_lifespan,
    )
    app.state.settings = settings
    app.state.cart_store = _build_cart_store(settings)
    app.state.order_repository = InMemoryOrderRepository()
    app.state.event_bus = _build_event_bus(settings)

    # Saga orchestrator wiring: one shared async HTTP client (timeout everywhere),
    # one circuit breaker instance dedicated to the payments call (ADR 0007).
    http_client = httpx.AsyncClient(transport=http_transport, timeout=settings.http_timeout)
    app.state.http_client = http_client
    app.state.payment_breaker = CircuitBreaker(
        failure_threshold=settings.breaker_failure_threshold,
        window_seconds=settings.breaker_window_seconds,
        recovery_timeout=settings.breaker_recovery_timeout,
        name="payments",
    )
    saga = SagaOrchestrator(
        orders=app.state.order_repository,
        event_bus=app.state.event_bus,
        restaurants=RestaurantsClient(http_client, settings.restaurants_url),
        payments=PaymentsClient(http_client, settings.payments_url),
        deliveries=DeliveriesClient(http_client, settings.deliveries_url),
        payment_breaker=app.state.payment_breaker,
        retry_attempts=settings.retry_attempts,
        retry_base_delay=settings.retry_base_delay,
        delivery_attempts=settings.delivery_assign_attempts,
        delivery_retry_delay=settings.delivery_assign_retry_delay,
    )
    app.state.saga = saga
    app.state.subscriber = (
        RedisSubscriber.from_url(
            settings.redis_url,
            {
                ORDER_READY_CHANNEL: saga.handle_order_ready,
                DELIVERY_COMPLETED_CHANNEL: saga.handle_delivery_completed,
            },
        )
        if settings.event_bus_backend == "redis"
        else None
    )

    app.add_middleware(CorrelationIdMiddleware)
    app.add_exception_handler(DomainError, _handle_domain_error)
    app.include_router(health_router)
    app.include_router(api_router)
    return app


app = create_app()
