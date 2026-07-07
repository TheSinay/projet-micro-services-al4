"""Application factory for the orders service."""

import redis
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.events import EventBus, InMemoryEventBus, RedisEventBus
from app.logging import CorrelationIdMiddleware, configure_logging
from app.repositories.interfaces import CartStore
from app.repositories.memory import InMemoryCartStore, InMemoryOrderRepository
from app.repositories.redis_store import RedisCartStore
from app.routes import api_router
from app.routes.health import router as health_router
from app.services.exceptions import DomainError


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


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a fully wired FastAPI application with fresh state.

    Stores live on ``app.state`` (no module-level globals), so tests can
    instantiate an isolated application per test case with in-memory backends.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="service-commandes",
        description=(
            "Orders for the food delivery platform: cart, checkout with pricing "
            "(subtotal + distance-based delivery fee), strict order state machine "
            "and history. The saga orchestrator arrives with T09."
        ),
        version="0.1.0",
    )
    app.state.settings = settings
    app.state.cart_store = _build_cart_store(settings)
    app.state.order_repository = InMemoryOrderRepository()
    app.state.event_bus = _build_event_bus(settings)

    app.add_middleware(CorrelationIdMiddleware)
    app.add_exception_handler(DomainError, _handle_domain_error)
    app.include_router(health_router)
    app.include_router(api_router)
    return app


app = create_app()
