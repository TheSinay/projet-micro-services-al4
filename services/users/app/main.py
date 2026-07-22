"""Application factory for the users service."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.logging import CorrelationIdMiddleware, configure_logging
from app.repositories.memory import (
    InMemoryAddressRepository,
    InMemoryTokenStore,
    InMemoryUserRepository,
)
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


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a fully wired FastAPI application with fresh in-memory state.

    Repositories live on ``app.state`` (no module-level globals), so tests can
    instantiate an isolated application per test case.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="service-utilisateurs",
        description="Identity, authentication and address book for the food delivery platform.",
        version="0.1.0",
    )
    app.state.settings = settings
    app.state.user_repository = InMemoryUserRepository()
    app.state.address_repository = InMemoryAddressRepository()
    app.state.token_store = InMemoryTokenStore()

    if settings.seed_data:
        from app.seed import seed_users

        seed_users(app.state.user_repository, app.state.address_repository)

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
