"""Application factory for the payments service."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.logging import CorrelationIdMiddleware, configure_logging
from app.repositories.memory import InMemoryPaymentRepository
from app.routes import api_router
from app.routes.health import router as health_router
from app.services.exceptions import DomainError
from app.services.psp import FlakyPspGateway


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

    Repositories and the simulated PSP gateway live on ``app.state`` (no
    module-level globals), so tests can instantiate an isolated application
    per test case and swap the gateway for a deterministic stub.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="service-paiements",
        description=(
            "Payments for the food delivery platform: simulated flaky PSP, "
            "idempotent charge per order, partial/total refunds."
        ),
        version="0.1.0",
    )
    app.state.settings = settings
    app.state.payment_repository = InMemoryPaymentRepository()
    app.state.psp_gateway = FlakyPspGateway(failure_rate=settings.failure_rate)

    app.add_middleware(CorrelationIdMiddleware)
    app.add_exception_handler(DomainError, _handle_domain_error)
    app.include_router(health_router)
    app.include_router(api_router)
    return app


app = create_app()
