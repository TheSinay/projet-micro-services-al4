"""Application factory for the restaurants service."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.events import InMemoryEventBus, RedisEventBus
from app.logging import CorrelationIdMiddleware, configure_logging
from app.repositories.memory import (
    InMemoryKitchenTicketRepository,
    InMemoryMenuItemRepository,
    InMemoryRestaurantRepository,
)
from app.routes import api_router
from app.routes.health import router as health_router
from app.seed import seed_catalogue
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
        title="service-restaurants",
        description="Restaurant catalogue: profiles, menus, search, order validation, kitchen.",
        version="0.1.0",
    )
    app.state.settings = settings
    app.state.restaurant_repository = InMemoryRestaurantRepository()
    app.state.menu_item_repository = InMemoryMenuItemRepository()
    app.state.ticket_repository = InMemoryKitchenTicketRepository()
    # Redis is only used outside the test suite (Settings.event_bus defaults to "memory").
    if settings.event_bus == "redis":
        app.state.event_bus = RedisEventBus.from_url(settings.redis_url)
    else:
        app.state.event_bus = InMemoryEventBus()

    if settings.seed_data:
        seed_catalogue(app.state.restaurant_repository, app.state.menu_item_repository)

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
