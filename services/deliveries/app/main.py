"""Application factory for the deliveries service."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.events import EventBus, InMemoryEventBus, RedisEventBus
from app.logging import CorrelationIdMiddleware, configure_logging
from app.repositories.memory import InMemoryCourierRepository, InMemoryDeliveryRepository
from app.routes import api_router
from app.routes.health import router as health_router
from app.seed import seed_couriers
from app.services.exceptions import DomainError


async def _handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    """Translate business errors into normalized ``{"detail": ...}`` responses."""
    assert isinstance(exc, DomainError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a fully wired FastAPI application with fresh in-memory state.

    Repositories and the event bus live on ``app.state`` (no module-level globals),
    so tests can instantiate an isolated application per test case.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="service-livraisons",
        description="Couriers, assignment and delivery tracking for the food delivery platform.",
        version="0.1.0",
    )
    app.state.settings = settings
    app.state.courier_repository = InMemoryCourierRepository()
    app.state.delivery_repository = InMemoryDeliveryRepository()
    event_bus: EventBus = (
        RedisEventBus(settings.redis_url)
        if settings.event_backend == "redis"
        else InMemoryEventBus()
    )
    app.state.event_bus = event_bus

    if settings.seed_data:
        seed_couriers(app.state.courier_repository)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)
    app.add_exception_handler(DomainError, _handle_domain_error)
    app.include_router(health_router)
    app.include_router(api_router)
    return app


app = create_app()
