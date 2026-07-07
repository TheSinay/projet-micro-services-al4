"""Application factory for the notifications service."""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.logging import CorrelationIdMiddleware, configure_logging
from app.repositories.memory import InMemoryNotificationRepository
from app.routes import api_router
from app.routes.health import router as health_router
from app.services.dispatch import NotificationDispatcher
from app.services.exceptions import DomainError
from app.subscriber import run_subscriber


async def _handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    """Translate business errors into normalized ``{"detail": ...}`` responses."""
    assert isinstance(exc, DomainError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start/stop the Redis pub/sub consumer only when the backend is ``redis``.

    With the default in-memory backend (tests) no task is started; the loop
    logic itself is covered by ``tests/test_subscriber.py`` with a fake client,
    so only this live-Redis wiring is excluded from coverage.
    """
    settings: Settings = app.state.settings
    dispatcher: NotificationDispatcher = app.state.dispatcher
    task: asyncio.Task[None] | None = None
    client: aioredis.Redis | None = None
    if settings.event_backend == "redis":  # pragma: no cover - requires a live Redis
        client = aioredis.Redis.from_url(settings.redis_url)
        task = asyncio.create_task(run_subscriber(client.pubsub(), dispatcher))
    try:
        yield
    finally:
        if task is not None:  # pragma: no cover - requires a live Redis
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        if client is not None:  # pragma: no cover - requires a live Redis
            await client.aclose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a fully wired FastAPI application with fresh in-memory state.

    The repository and the dispatcher live on ``app.state`` (no module-level
    globals), so tests can instantiate an isolated application per test case.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="service-notifications",
        description="Event-driven simulated notifications for the food delivery platform.",
        version="0.1.0",
        lifespan=_lifespan,
    )
    app.state.settings = settings
    repository = InMemoryNotificationRepository()
    app.state.notification_repository = repository
    app.state.dispatcher = NotificationDispatcher(repository)

    app.add_middleware(CorrelationIdMiddleware)
    app.add_exception_handler(DomainError, _handle_domain_error)
    app.include_router(health_router)
    app.include_router(api_router)
    return app


app = create_app()
